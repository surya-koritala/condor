#!/usr/bin/env python3
"""An MCP server (stdio) so AI tools (Claude Code, Cursor, ...) can start, stop, check and ask Qwen3.8-Flash-Next running on Glyd. Standard library only.
    claude mcp add glyd -- python3 /path/to/glyd-qwen-3.8-flash/tools/mcp_server.py
Tools: glyd_status, glyd_start (fast or precise), glyd_stop, glyd_ask (one chat message)."""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
HB = Path(os.environ.get("GLYD_QWEN", Path.home() / ".glyd-qwen-3.8-flash"))
URL = os.environ.get("GLYD_URL", "http://127.0.0.1:8080")
PIDFILE = HB / "server.pid"

TOOLS = [
    {"name": "glyd_status", "description": "Whether Qwen3.8-Flash-Next (on this computer's GPU, with Glyd) is running, and its address.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "glyd_start", "description": "Start the Glyd server (chat page and OpenAI/Anthropic API). Loading takes about a minute.",
     "inputSchema": {"type": "object", "properties": {"mode": {"type": "string", "enum": ["fast", "precise"], "description": "fast (default) or precise"}}}},
    {"name": "glyd_stop", "description": "Stop the Glyd server and free the GPU.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "glyd_ask", "description": "Ask the local model one question and get its answer.",
     "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}, "max_tokens": {"type": "integer"}}, "required": ["prompt"]}},
]


def healthy():
    try:
        with urllib.request.urlopen(URL + "/health", timeout=2) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def call(name, args):
    if name == "glyd_status":
        return f"running at {URL} (chat page {URL}/, API {URL}/v1)" if healthy() else "not running"
    if name == "glyd_start":
        if healthy():
            return f"already running at {URL}"
        cmd = ["bash", str(HERE / "serve.sh")] + (["--precise"] if args.get("mode") == "precise" else [])
        log = open(HB / "server.log", "a")
        p = subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
        PIDFILE.write_text(str(p.pid))
        for _ in range(600):
            if healthy():
                break
            if p.poll() is not None:
                return f"the server exited; see {HB / 'server.log'}"
            time.sleep(1)
        return f"started at {URL}" if healthy() else f"still loading; see {HB / 'server.log'}"
    if name == "glyd_stop":
        if not PIDFILE.exists():
            return "not started by this tool"
        try:
            os.killpg(int(PIDFILE.read_text()), signal.SIGTERM)
        except (ProcessLookupError, ValueError):
            pass
        PIDFILE.unlink(missing_ok=True)
        return "stopped"
    if name == "glyd_ask":
        body = json.dumps({"messages": [{"role": "user", "content": args["prompt"]}], "max_tokens": int(args.get("max_tokens", 1024))}).encode()
        req = urllib.request.Request(URL + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3600) as r:
            return json.load(r)["choices"][0]["message"]["content"]
    raise ValueError(f"no tool {name}")


def main():
    HB.mkdir(parents=True, exist_ok=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        if mid is None:   # (a notification: nothing to answer)
            continue
        if method == "initialize":
            res = {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                   "serverInfo": {"name": "glyd-qwen-3.8-flash", "version": "0.1.0"}}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            p = msg.get("params", {})
            try:
                res = {"content": [{"type": "text", "text": call(p.get("name"), p.get("arguments") or {})}]}
            except Exception as e:  # noqa: BLE001
                res = {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
        elif method == "ping":
            res = {}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"no method {method}"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": res}), flush=True)


if __name__ == "__main__":
    main()
