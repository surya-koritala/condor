#!/usr/bin/env python3
"""Glyd's server for Qwen3.8-Flash-Next (Hummingbird level): the Glyd engine (`glyd-engine qwenserve`) behind an OpenAI- and Anthropic-compatible HTTP API, with a chat page.

    server.py --model DIR --pack DIR [--precise] [--port 8080] [--host 127.0.0.1]

  GET  /                        the chat page
  GET  /health, /v1/models
  POST /v1/chat/completions     OpenAI: streaming, tools (tool_calls), reasoning_content, chat_template_kwargs
  POST /v1/messages             Anthropic: streaming, tools (tool_use / tool_result), system, thinking
  POST /v1/messages/count_tokens

The engine answers one request at a time (requests queue); decoding is greedy. Thinking is off unless a request turns it on
(chat_template_kwargs.enable_thinking, reasoning_effort, or Anthropic's thinking). `server.py --selftest` checks the parsers."""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")   # (its "PyTorch was not found" warning: the server only uses the tokenizer)

HERE = Path(__file__).resolve().parent


ENGINE_LINE = re.compile(r"(\d+) prompt tokens, (\d+) made in (\d+) ms(?: with drafts of \d+)? \(the prompt (\d+) ms, then ([0-9.]+) ms a token\)"
                         r"(?:: \d+ passes, (\d+) of (\d+) guesses right \(\d+%\), ([0-9.]+) tokens a pass)?(?:; the cache: ([0-9.]+)% in places)?")


class Engine:
    """glyd-engine qwenserve as a child process: a JSON request a line in; {"part": [ids]} lines while it streams, then the reply's line.
    Its log (stderr) goes on to this server's, and its per-request line feeds `stats` for the dashboard."""

    def __init__(self, cmd):
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.lock = threading.Lock()
        self.state = {"state": "loading", "since": time.time()}
        self.stats = {}          # the last request's engine numbers
        self.places = None       # "N a layer of X MB" from the load
        threading.Thread(target=self._log, daemon=True).start()

    def _log(self):
        for line in self.p.stderr:
            sys.stderr.write(line)
            m = ENGINE_LINE.search(line)
            if m:
                g = m.groups()
                self.stats = {"prompt_tokens": int(g[0]), "made": int(g[1]), "ms": int(g[2]), "prompt_ms": int(g[3]), "ms_a_token": float(g[4]),
                              "guesses_right": int(g[5]) if g[5] else None, "guesses": int(g[6]) if g[6] else None,
                              "tokens_a_pass": float(g[7]) if g[7] else None, "cache_hits": float(g[8]) if g[8] else None}
            m = re.search(r"places: ([0-9.]+) GB, (\d+) a layer", line)
            if m:
                self.places = {"gb": float(m.group(1)), "per_layer": int(m.group(2))}
            if "free memory after the load" in line:
                self.state = {"state": "idle", "since": time.time()}

    def generate(self, ids, max_new, stop, on_part=None, sampling=None):
        req = {"ids": ids, "max_new": max_new, "stop": stop, **(sampling or {})}
        if on_part:
            req["stream"] = True
        self.waiting = getattr(self, "waiting", 0) + 1
        with self.lock:
            self.waiting -= 1
            self.state = {"state": "reading", "since": time.time(), "prompt_tokens": len(ids), "made": 0}
            first = [True]
            user_part, failed = on_part, []

            def on_part(part):
                if first[0]:
                    first[0] = False
                    self.state = {**self.state, "state": "writing", "writing_since": time.time()}
                self.state["made"] = self.state.get("made", 0) + len(part)
                if user_part and not failed:
                    try:
                        user_part(part)
                    except Exception as e:  # noqa: BLE001 (the client went away: read the rest, or the next request gets it)
                        failed.append(e)
                # ponytail: an abandoned answer runs to max_new; an engine "cancel" message is the upgrade
            req["stream"] = True
            self.p.stdin.write(json.dumps(req) + "\n")
            self.p.stdin.flush()
            while True:
                line = self.p.stdout.readline()
                if not line:
                    raise RuntimeError("the engine exited (see its log above)")
                if not line.lstrip().startswith("{"):
                    continue
                msg = json.loads(line)
                if "part" in msg:
                    if on_part:
                        on_part(msg["part"])
                    continue
                self.state = {"state": "idle", "since": time.time()}
                if "error" in msg:
                    raise RuntimeError(f"the engine: {msg['error']}")
                if failed:
                    raise failed[0]
                return msg


SAMPLING = ("temperature", "top_p", "top_k", "min_p", "presence_penalty", "frequency_penalty", "repetition_penalty", "seed")
TOOL_RE = re.compile(r"<tool_call>\s*<function=([^>\s]+)>(.*?)</function>\s*</tool_call>", re.S)
PARAM_RE = re.compile(r"<parameter=([^>\s]+)>\n?(.*?)\n?</parameter>", re.S)


class TooLong(ValueError):
    """A prompt longer than the context."""


def parse_tool_calls(text):
    """The model's tool calls (<tool_call><function=NAME><parameter=P>value</parameter>...</function></tool_call>) as
    [(name, {param: value})], and the text before the first one. A value that is JSON (a number, list, object, true) is decoded."""
    calls = []
    for m in TOOL_RE.finditer(text):
        args = {}
        for p in PARAM_RE.finditer(m.group(2)):
            v = p.group(2)
            try:
                v = json.loads(v) if v.strip()[:1] in "[{0123456789-tfn\"" else v
            except ValueError:
                pass
            args[p.group(1)] = v
        calls.append((m.group(1), args))
    i = text.find("<tool_call>")
    return calls, (text if i < 0 else text[:i])


class Splitter:
    """Streamed text cut into reasoning (before </think>, when thinking) and content; content stops at <tool_call>. A tail that
    could be the start of a tag is held back until it can't."""

    def __init__(self, thinking):
        self.state = "think" if thinking else "content"
        self.buf = ""

    def feed(self, text, final=False):
        out = []   # ("reasoning" | "content", text)
        self.buf += text
        while self.buf:
            if self.state == "think":
                tag = "</think>"
            elif self.state == "content":
                tag = "<tool_call>"
            else:
                self.buf = ""
                break
            i = self.buf.find(tag)
            if i >= 0:
                if i:
                    out.append(("reasoning" if self.state == "think" else "content", self.buf[:i]))
                self.buf = self.buf[i + len(tag):]
                self.state = "content" if self.state == "think" else "tools"
                if self.state == "content":
                    self.buf = self.buf.lstrip("\n")
                continue
            keep = 0 if final else next((k for k in range(min(len(tag) - 1, len(self.buf)), 0, -1) if tag.startswith(self.buf[-k:])), 0)
            emit = self.buf[: len(self.buf) - keep]
            if emit:
                out.append(("reasoning" if self.state == "think" else "content", emit))
            self.buf = self.buf[len(emit):]
            break
        return out


class Machine:
    """The computer's numbers once a second for the dashboard (the GPU's through nvidia-smi, the CPU's, RAM's and disk's through /proc), with
    the last two minutes of each."""

    KEYS = ("gpu_load", "vram_used", "gpu_temp", "power", "cpu", "ram_used", "disk_read", "tok_s")

    def __init__(self):
        self.now, self.hist, self.static = {}, {k: [] for k in self.KEYS}, {}
        self._cpu = self._disk = None
        threading.Thread(target=self._run, daemon=True).start()

    def _gpu(self):
        q = "name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit,pcie.link.gen.current,pcie.link.width.current"
        out = subprocess.run(["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5).stdout
        f = [x.strip() for x in out.splitlines()[0].split(",")]
        num = lambda x: float(x) if x.replace(".", "", 1).isdigit() else None
        self.static.update(gpu=f[0], vram_total=num(f[3]), power_limit=num(f[6]), pcie=f"Gen{f[7]} x{f[8]}")
        return {"gpu_load": num(f[1]), "vram_used": num(f[2]), "gpu_temp": num(f[4]), "power": num(f[5])}

    def _proc(self):
        r = {}
        with open("/proc/stat") as fh:
            v = [int(x) for x in fh.readline().split()[1:]]
        idle, total = v[3] + v[4], sum(v)
        if self._cpu:
            r["cpu"] = round(100 * (1 - (idle - self._cpu[0]) / max(total - self._cpu[1], 1)), 1)
        self._cpu = (idle, total)
        mem = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}
        r["ram_used"] = round((mem["MemTotal"] - mem["MemAvailable"]) / 2**20, 1)
        self.static["ram_total"] = round(mem["MemTotal"] / 2**20, 1)
        sectors = sum(int(l.split()[5]) for l in open("/proc/diskstats") if re.match(r"(nvme\d+n\d+|sd[a-z]|vd[a-z])$", l.split()[2]))
        t = time.time()
        if self._disk:
            r["disk_read"] = round((sectors - self._disk[0]) * 512 / 1e6 / max(t - self._disk[1], 1e-3), 1)
        self._disk = (sectors, t)
        self.static["cores"] = os.cpu_count()
        return r

    def _run(self):
        while True:
            now = {}
            for f in (self._gpu, self._proc):
                try:
                    now.update(f())
                except Exception:  # noqa: BLE001 (a missing tool leaves its numbers out)
                    pass
            now["tok_s"] = LIVE.get("tok_s", 0.0)
            self.now = now
            for k in self.KEYS:
                self.hist[k] = (self.hist[k] + [now.get(k)])[-120:]
            time.sleep(1)


MODE = {}          # fast or precise, the context
MACHINE = None
LIVE = {}          # the reply being written: tokens a second, for the dashboard
REQUESTS = []      # the last 30 requests


class Model:
    def __init__(self, model_dir, engine):
        from transformers import AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(model_dir)
        self.engine = engine
        self.last_reused = 0
        gc = json.load(open(Path(model_dir) / "generation_config.json"))
        # (the model's own sampling defaults, as vLLM takes them, for what a request leaves out; temperature 0 asks for greedy)
        self.defaults = {k: gc[k] for k in ("temperature", "top_k", "top_p") if k in gc} if gc.get("do_sample") else {}
        if self.defaults:
            # The model's own settings (temperature 1.0) on the compressed experts end about one answer in four early: the compression leaves a
            # few percent on the end token in places, before a code block most of all. 0.7 and min-p 0.05 ended none of 20 (two-turn chats, a table
            # then a flowchart); a request's own values still win.
            self.defaults.update(temperature=min(self.defaults.get("temperature", 0.7), 0.7), min_p=0.05)
        e = gc.get("eos_token_id", [])
        self.eos = e if isinstance(e, list) else [e]

    def prompt(self, messages, tools, thinking, effort):
        kw = {"enable_thinking": thinking}
        if thinking and effort:
            kw["reasoning_effort"] = effort
        text = self.tok.apply_chat_template(messages, tools=tools or None, tokenize=False, add_generation_prompt=True, **kw)
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def sampling(self, body, keys=SAMPLING):
        """The request's sampling settings over the model's defaults (top_k -1 or 0: none)."""
        s = {**self.defaults, **{k: body[k] for k in keys if body.get(k) is not None}}
        if s.get("top_k", 0) < 0:
            s["top_k"] = 0
        return s

    def run(self, messages, tools, thinking, effort, max_new, on_delta=None, sampling=None):
        """Generate; on_delta(kind, text) as text arrives (kind reasoning / content). Returns (reasoning, content, tool_calls, finish, n_prompt, n_out);
        self.last_reused: how many of the prompt's tokens the engine kept from the conversation's earlier turns."""
        ids = self.prompt(messages, tools, thinking, effort)
        room = MODE.get("ctx", 33536) - len(ids)
        if room < 1:
            raise TooLong(f"the prompt is {len(ids)} tokens; the context holds {MODE.get('ctx')} (start the server with a larger --ctx)")
        max_new = min(max_new, room)   # (like other servers: a max_tokens past the context means "as much as fits")
        t0 = time.time()
        made, sent = [], [""]
        split = Splitter(thinking)

        def on_part(part):
            made.extend(part)
            st = self.engine.state
            if st.get("writing_since"):
                LIVE["tok_s"] = round(len(made) / max(time.time() - st["writing_since"], 1e-3), 1)
            if not on_delta:
                return
            text = self.tok.decode([i for i in made if i not in self.eos], skip_special_tokens=False)
            if text.endswith("�"):   # (a character cut between tokens: wait for the rest)
                return
            new, sent[0] = text[len(sent[0]):], text
            for kind, t in split.feed(new):
                on_delta(kind, t)
        try:
            out = self.engine.generate(ids, max_new, self.eos, on_part, sampling)
        except Exception as e:
            REQUESTS.insert(0, {"time": time.strftime("%H:%M:%S"), "status": "error", "prompt": len(ids), "error": str(e)[:200]}); del REQUESTS[30:]
            raise
        finally:
            LIVE["tok_s"] = 0.0
        self.last_reused = int(out.get("reused", 0))
        es = self.engine.stats
        REQUESTS.insert(0, {"time": time.strftime("%H:%M:%S"), "status": "done", "prompt": len(ids), "reused": self.last_reused, "output": len(out.get("ids", [])),
                            "tok_s": round(1000 / es["ms_a_token"], 1) if es.get("ms_a_token") else None, "prompt_s": round(es.get("prompt_ms", 0) / 1000, 2),
                            "seconds": round(time.time() - t0, 2), "guesses": round(100 * es["guesses_right"] / es["guesses"]) if es.get("guesses") else None,
                            "cache": es.get("cache_hits"), "thinking": thinking, "tools": bool(tools)})
        del REQUESTS[30:]
        toks = [int(i) for i in out["ids"]]
        text = self.tok.decode([i for i in toks if i not in self.eos], skip_special_tokens=False)
        if on_delta:
            for kind, t in split.feed(text[len(sent[0]):], final=True):
                on_delta(kind, t)
        reasoning, content = "", text
        if thinking and "</think>" in text:
            reasoning, content = text.split("</think>", 1)
            reasoning, content = reasoning.replace("<think>", "").strip(), content.lstrip("\n")
        for special in ("<|im_end|>", "<|endoftext|>"):
            content = content.replace(special, "")
        calls, content = parse_tool_calls(content) if tools else ([], content)
        finish = "tool_calls" if calls else ("stop" if toks and toks[-1] in self.eos else "length")
        return reasoning, content.strip() if calls else content, calls, finish, len(ids), len(toks)


def openai_messages(msgs):
    """OpenAI messages as the chat template takes them: tool calls' arguments as objects, content parts joined."""
    out = []
    for m in msgs:
        m = dict(m)
        if isinstance(m.get("content"), list):
            m["content"] = "".join(p.get("text", "") for p in m["content"] if p.get("type") in ("text", "input_text"))
        if m.get("tool_calls"):
            calls = []
            for c in m["tool_calls"]:
                f = dict(c.get("function", {}))
                if isinstance(f.get("arguments"), str):
                    try:
                        f["arguments"] = json.loads(f["arguments"] or "{}")
                    except ValueError:
                        f["arguments"] = {}
                calls.append({**c, "function": f})
            m["tool_calls"] = calls
        out.append(m)
    return out


def anthropic_messages(body):
    """An Anthropic request's system, messages and tools in OpenAI's form for the template."""
    out = []
    sys_ = body.get("system")
    if sys_:
        out.append({"role": "system", "content": sys_ if isinstance(sys_, str) else "".join(b.get("text", "") for b in sys_)})
    for m in body.get("messages", []):
        c = m.get("content")
        if isinstance(c, str):
            out.append({"role": m["role"], "content": c})
            continue
        text, calls = "", []
        for b in c or []:
            t = b.get("type")
            if t == "text":
                text += b.get("text", "")
            elif t == "tool_use":
                calls.append({"id": b.get("id"), "type": "function", "function": {"name": b.get("name"), "arguments": b.get("input") or {}}})
            elif t == "tool_result":
                rc = b.get("content")
                rc = rc if isinstance(rc, str) else "".join(x.get("text", "") for x in (rc or []) if x.get("type") == "text")
                out.append({"role": "tool", "tool_call_id": b.get("tool_use_id"), "content": rc})
        if text or calls:
            msg = {"role": m["role"], "content": text}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
    tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("input_schema", {})}}
             for t in body.get("tools") or [] if t.get("name")]
    return out, tools


def make_handler(model, name):

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *a):
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % a))

        def _send(self, code, body, ctype="application/json"):
            b = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def _stream_start(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

        def _chunk(self, data):
            b = data.encode()
            self.wfile.write(b"%x\r\n" % len(b) + b + b"\r\n")
            self.wfile.flush()

        def do_GET(self):
            p = self.path.split("?")[0].rstrip("/")
            if p in ("", "/index.html"):
                page = HERE / "chat.html"
                self._send(200, page.read_bytes() if page.exists() else b"<p>chat.html is missing</p>", "text/html; charset=utf-8")
            elif p.startswith("/web/") and re.fullmatch(r"[A-Za-z0-9._-]+", p[5:]) and (HERE / "web" / p[5:]).is_file():
                kind = {".woff2": "font/woff2", ".svg": "image/svg+xml", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8"}.get(Path(p).suffix, "application/octet-stream")
                self._send(200, (HERE / "web" / p[5:]).read_bytes(), kind)
            elif p in ("/health", "/v1/health"):
                self._send(200, {"status": "ok"})
            elif p == "/v1/glyd/status":
                e, now = model.engine, time.time()
                st = dict(e.state)
                st["seconds"] = round(now - st.get("since", now), 1)
                if st["state"] == "reading":
                    st["progress"] = min(0.99, st["seconds"] * 4200 / max(st.get("prompt_tokens", 1) - model.last_reused, 1))
                self._send(200, {"model": name, "mode": MODE.get("mode"), "ctx": MODE.get("ctx"), "engine": st, "waiting": getattr(e, "waiting", 0),
                                 "stats": e.stats, "places": e.places, "machine": {**MACHINE.static, **MACHINE.now}, "history": MACHINE.hist,
                                 "requests": REQUESTS, "live_tok_s": LIVE.get("tok_s", 0.0)})
            elif p == "/v1/models":
                self._send(200, {"object": "list", "data": [{"id": name, "object": "model", "owned_by": "glyd"}]})
            else:
                self._send(404, {"error": {"message": "not found"}})

        def do_POST(self):
            p = self.path.split("?")[0].rstrip("/")
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            except ValueError:
                return self._send(400, {"error": {"message": "the body is not JSON"}})
            try:
                if p == "/v1/chat/completions":
                    return self.openai(body)
                if p == "/v1/messages":
                    return self.anthropic(body)
                if p == "/v1/messages/count_tokens":
                    msgs, tools = anthropic_messages(body)
                    return self._send(200, {"input_tokens": len(model.prompt(msgs, tools, False, None))})
                return self._send(404, {"error": {"message": "not found"}})
            except TooLong as e:
                return self._send(400, {"error": {"type": "invalid_request_error", "code": "context_length_exceeded", "message": str(e)}})
            except Exception as e:  # noqa: BLE001 (the client gets the reason)
                try:
                    return self._send(500, {"error": {"type": "server_error", "message": f"{type(e).__name__}: {e}"}})
                except OSError:
                    return None

        def openai(self, body):
            kw = body.get("chat_template_kwargs") or {}
            effort = body.get("reasoning_effort") or kw.get("reasoning_effort")
            thinking = bool(kw.get("enable_thinking", bool(effort)))
            max_new = int(body.get("max_completion_tokens") or body.get("max_tokens") or 4096)
            msgs, tools = openai_messages(body["messages"]), body.get("tools")
            if body.get("tool_choice") == "none":
                tools = None
            cid, created = "chatcmpl-" + uuid.uuid4().hex[:24], int(time.time())
            base = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": name}
            if not body.get("stream"):
                r, c, calls, finish, n_in, n_out = model.run(msgs, tools, thinking, effort, max_new, sampling=model.sampling(body))
                msg = {"role": "assistant", "content": c or (None if calls else "")}
                if r:
                    msg["reasoning_content"] = r
                if calls:
                    msg["tool_calls"] = [{"id": "call_" + uuid.uuid4().hex[:24], "type": "function", "function": {"name": n, "arguments": json.dumps(a)}} for n, a in calls]
                return self._send(200, {"id": cid, "object": "chat.completion", "created": created, "model": name,
                                        "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                                        "usage": {"prompt_tokens": n_in, "completion_tokens": n_out, "total_tokens": n_in + n_out,
                                                  "prompt_tokens_details": {"cached_tokens": model.last_reused}}})
            self._stream_start()

            def sse(obj):
                self._chunk("data: " + json.dumps(obj) + "\n\n")
            sse({**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})

            def delta(kind, text):
                sse({**base, "choices": [{"index": 0, "delta": {"reasoning_content" if kind == "reasoning" else "content": text}, "finish_reason": None}]})
            r, c, calls, finish, n_in, n_out = model.run(msgs, tools, thinking, effort, max_new, delta, model.sampling(body))
            for i, (n, a) in enumerate(calls):
                sse({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": i, "id": "call_" + uuid.uuid4().hex[:24], "type": "function",
                                                                                 "function": {"name": n, "arguments": json.dumps(a)}}]}, "finish_reason": None}]})
            sse({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
            if (body.get("stream_options") or {}).get("include_usage"):
                sse({**base, "choices": [], "usage": {"prompt_tokens": n_in, "completion_tokens": n_out, "total_tokens": n_in + n_out,
                                                      "prompt_tokens_details": {"cached_tokens": model.last_reused}}})
            self._chunk("data: [DONE]\n\n")
            self.wfile.write(b"0\r\n\r\n")

        def anthropic(self, body):
            msgs, tools = anthropic_messages(body)
            th = body.get("thinking") or {}
            thinking = th.get("type") == "enabled"
            max_new = int(body.get("max_tokens") or 4096)
            mid = "msg_" + uuid.uuid4().hex[:24]
            stop_of = {"tool_calls": "tool_use", "stop": "end_turn", "length": "max_tokens"}
            if not body.get("stream"):
                r, c, calls, finish, n_in, n_out = model.run(msgs, tools, thinking, None, max_new, sampling=model.sampling(body, ("temperature", "top_p", "top_k")))
                content = ([{"type": "text", "text": c}] if c else []) + [
                    {"type": "tool_use", "id": "toolu_" + uuid.uuid4().hex[:24], "name": n, "input": a} for n, a in calls]
                return self._send(200, {"id": mid, "type": "message", "role": "assistant", "model": name, "content": content,
                                        "stop_reason": stop_of[finish], "stop_sequence": None,
                                        "usage": {"input_tokens": n_in - model.last_reused, "cache_read_input_tokens": model.last_reused, "output_tokens": n_out}})
            self._stream_start()

            def ev(kind, obj):
                self._chunk(f"event: {kind}\ndata: {json.dumps({'type': kind, **obj})}\n\n")
            ev("message_start", {"message": {"id": mid, "type": "message", "role": "assistant", "model": name, "content": [], "stop_reason": None,
                                             "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": 0}}})
            open_text = [False]

            def delta(kind, text):
                if kind != "content":   # (reasoning is not sent: Anthropic's thinking blocks carry a signature this server can't make)
                    return
                if not open_text[0]:
                    ev("content_block_start", {"index": 0, "content_block": {"type": "text", "text": ""}})
                    open_text[0] = True
                ev("content_block_delta", {"index": 0, "delta": {"type": "text_delta", "text": text}})
            r, c, calls, finish, n_in, n_out = model.run(msgs, tools, thinking, None, max_new, delta, model.sampling(body, ("temperature", "top_p", "top_k")))
            idx = 0
            if open_text[0]:
                ev("content_block_stop", {"index": 0})
                idx = 1
            for n, a in calls:
                ev("content_block_start", {"index": idx, "content_block": {"type": "tool_use", "id": "toolu_" + uuid.uuid4().hex[:24], "name": n, "input": {}}})
                ev("content_block_delta", {"index": idx, "delta": {"type": "input_json_delta", "partial_json": json.dumps(a)}})
                ev("content_block_stop", {"index": idx})
                idx += 1
            ev("message_delta", {"delta": {"stop_reason": stop_of[finish], "stop_sequence": None}, "usage": {"output_tokens": n_out}})
            ev("message_stop", {})
            self.wfile.write(b"0\r\n\r\n")
    return H


def selftest():
    calls, before = parse_tool_calls("Let me look.\n<tool_call>\n<function=read_file>\n<parameter=path>\nsrc/main.rs\n</parameter>\n<parameter=limit>\n40\n</parameter>\n</function>\n</tool_call>")
    assert before == "Let me look.\n" and calls == [("read_file", {"path": "src/main.rs", "limit": 40})], (before, calls)
    s, got = Splitter(True), []
    for piece in ["I should ", "add.</th", "ink>\n\nThe answer", " is 4.<tool", "_call>\n<function=x>"]:
        got += s.feed(piece)
    got += s.feed("", final=True)
    text = {"reasoning": "".join(t for k, t in got if k == "reasoning"), "content": "".join(t for k, t in got if k == "content")}
    assert text == {"reasoning": "I should add.", "content": "The answer is 4."}, text
    msgs, tools = anthropic_messages({"system": "Be brief.", "tools": [{"name": "ls", "input_schema": {"type": "object"}}], "messages": [
        {"role": "user", "content": "list"}, {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "ls", "input": {"dir": "."}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "a.txt"}]}]})
    assert [m["role"] for m in msgs] == ["system", "user", "assistant", "tool"] and tools[0]["function"]["name"] == "ls", msgs
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model"); ap.add_argument("--pack"); ap.add_argument("--precise", action="store_true")
    ap.add_argument("--engine", default="glyd-engine"); ap.add_argument("--engine-args", default="")
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--name", default="qwen3.8-flash-next"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.model and a.pack):
        ap.error("--model and --pack are required")
    cmd = [a.engine, "qwenserve", a.model, a.pack] + (["--precise"] if a.precise else []) + shlex.split(a.engine_args)
    global MACHINE
    MODE.update(mode="precise" if a.precise else "fast", ctx=next((int(x) for x in re.findall(r"--ctx\s+(\d+)", a.engine_args)), 33536))
    MACHINE = Machine()
    model = Model(a.model, Engine(cmd))
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(model, a.name))
    srv.daemon_threads = True
    print(f"Qwen3.8-Flash-Next on Glyd: chat at http://{a.host}:{a.port}/, API at http://{a.host}:{a.port}/v1 (OpenAI and Anthropic)", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
