#!/usr/bin/env python3
"""Acceptance suite for a GLM-5.3-Flash engine behind glm_shim.py (Linear GLY-133): correctness before speed. A mix and an engine build count only if these pass; no speed number is quoted from one that does not.

  needle   a secret number hidden in the novel's text (the Strata record's long prompt), at 1K, 2K, 4K, 8K, 16K and 32K tokens, three needle positions each (10%, 50%, 90% of the text); the question comes last. Pass: the reply
           contains the number. `needle_exact.py` checks the same prompts teacher-forced on the exact model (this file writes them with --write-prompts): a case the exact model fails does not count.
  chat     twelve chat and code prompts with known answers (facts, arithmetic, a word problem, instruction following, JSON, code that is run against tests). Pass: the check holds and the reply is neither cut off
           at the token cap nor a loop.
  follow   the instruction-following cases of ifcases.py (all caps, a given language, JSON only, exactly N items, one word...): the damage class that needles and GSM8K miss. Only the cases the exact model answers with high
           confidence count (if_report.py writes the list, bench/if_gate.json, from the teacher-forced simulation).
  gsm8k    the first 25 questions of the Strata record's GSM8K set (10-shot, Inspect AI, as eval_slice.py runs them): no reply may loop, hit the 3,072-token cap or be garbage; the score is reported too.
  dump     the 128-position check of an engine dump against the exact model and a simulated mix (engine_check.py).

    python accept.py --base http://127.0.0.1:8011 --snap SNAPSHOT_DIR --out DIR [--tests needle,chat,follow,gsm8k] [--if-gate bench/if_gate.json] [--lengths 1024,2048,4096,8192,16384,32000] [--exact-pass FILE]
    python accept.py --write-prompts bench/needle_prompts.json --snap SNAPSHOT_DIR
    python accept.py --analyse-gsm8k bench/slices/gsm8k_000_025          the loop / garbage check of an eval_slice.py run
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zlib

LENGTHS = [1024, 2048, 4096, 8192, 16384, 32000]
POSITIONS = [0.10, 0.50, 0.90]


# ---------------------------------------------------------------------------------------------------------------------------------- loops and garbage
def looks_degenerate(text, tokens=None, cap=3072):
    """Why a reply is a loop or garbage, or None: it hit the token cap, a 6-word sequence repeats 4 times or more, it compresses below 0.2 of its size (above 400 characters), a character class is out of place."""
    if tokens is not None and tokens >= cap:
        return "hit the token cap"
    words = text.split()
    seen = {}
    for i in range(len(words) - 5):
        g = tuple(words[i:i + 6])
        seen[g] = seen.get(g, 0) + 1
        if seen[g] >= 4:
            return "a 6-word sequence repeats 4 times: " + " ".join(g)[:60]
    if len(text) > 400 and len(zlib.compress(text.encode())) / len(text.encode()) < 0.2:
        return "compresses below 0.2 of its size"
    if len(text) > 80 and sum(1 for ch in text if not (ch.isprintable() or ch in "\n\t")) / len(text) > 0.05:
        return "non-printable characters"
    if re.search(r"(\b\w{1,3}\b[ ,.]?)\1{12,}", text):
        return "a short token repeated 12 times in a row"
    return None


# ---------------------------------------------------------------------------------------------------------------------------------- the server
class Server:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def chat(self, messages, max_tokens, timeout=3600):
        body = json.dumps({"model": "m", "messages": messages, "max_tokens": max_tokens, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False}}).encode()
        req = urllib.request.Request(self.base + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        ch = d["choices"][0]
        return {"text": ch["message"]["content"], "finish": ch["finish_reason"], "prompt_tokens": d["usage"]["prompt_tokens"], "completion_tokens": d["usage"]["completion_tokens"],
                "secs": time.time() - t0, "timings": d.get("timings")}


# ---------------------------------------------------------------------------------------------------------------------------------- needle
def needle_prompts(snap, lengths=LENGTHS, positions=POSITIONS, text_path=None):
    """[{id, length, position, code, messages}]: the novel's text cut to about `length` tokens in total, the sentence with the code inserted at `position` of the text (at a sentence end), the question last."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(snap)
    path = text_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench", "long_prompt.txt")
    novel = open(path, encoding="utf-8").read()
    q = "\n\n---\nWhat is the secret passcode of the vault mentioned in the text above? Reply with just the number."
    rng = random.Random(20261011)
    out = []
    for L in lengths:
        for pos in positions:
            code = str(rng.randint(10000, 99999))
            needle = f" The secret passcode of the vault is {code}. "
            budget = L - len(tok(needle + q, add_special_tokens=False)["input_ids"]) - 40   # (the chat template's own tokens)
            ids = tok(novel, add_special_tokens=False)["input_ids"][:budget]
            cut = int(len(ids) * pos)
            before = tok.decode(ids[:cut])
            k = max(before.rfind(". "), before.rfind(".\n"))
            before = before[:k + 2] if k > 0 else before
            body = before + needle + tok.decode(ids[cut:])
            out.append({"id": f"needle_{L}_{int(pos * 100)}", "length": L, "position": pos, "code": code, "messages": [{"role": "user", "content": body + q}]})
    return out


def run_needle(srv, prompts, exact_pass=None):
    rows = []
    for p in prompts:
        r = srv.chat(p["messages"], 24)
        ok = p["code"] in r["text"].replace(",", "").replace(" ", "")
        exact_ok = None if exact_pass is None else bool(exact_pass.get(p["id"]))
        rows.append({"id": p["id"], "length": p["length"], "position": p["position"], "code": p["code"], "reply": r["text"][:80], "pass": ok, "exact_passes": exact_ok, "prompt_tokens": r["prompt_tokens"], "secs": round(r["secs"], 1)})
        print(f"  {p['id']:16s} {r['prompt_tokens']:6d} tokens  {'PASS' if ok else 'FAIL'}  {r['text'].strip()[:50]!r}  ({r['secs']:.0f} s)" + ("" if exact_ok is None else f"  exact model: {'passes' if exact_ok else 'FAILS (not counted)'}"), flush=True)
    return rows


# ---------------------------------------------------------------------------------------------------------------------------------- chat and code
def run_python(code, tests, timeout=10):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code + "\n\n" + tests + "\nprint('TESTS PASSED')\n")
        path = f.name
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
        return "TESTS PASSED" in r.stdout
    except Exception:  # noqa: BLE001
        return False
    finally:
        os.unlink(path)


def extract_code(text):
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    return m.group(1) if m else text


def has(*subs, any_of=False):
    return lambda t: (any if any_of else all)(s.lower() in t.lower() for s in subs)


CHAT = [
    ("capital", [{"role": "user", "content": "What is the capital of France? Answer in one word."}], has("paris")),
    ("arithmetic", [{"role": "user", "content": "What is 17 * 23? Reply with just the number."}], has("391")),
    ("symbol", [{"role": "user", "content": "What is the chemical symbol for gold? Reply with just the symbol."}], lambda t: t.strip().strip(".*`") == "Au"),
    ("ducks", [{"role": "user", "content": "Janet's ducks lay 16 eggs per day. She eats three for breakfast and bakes muffins with four. She sells the rest at $2 per egg. How much does she make every day? End with 'ANSWER: <number>'."}],
     lambda t: re.search(r"ANSWER:\s*\$?18\b", t) is not None),
    ("train", [{"role": "user", "content": "A train travels at 60 miles per hour for 2.5 hours. How many miles does it travel? Reply with just the number."}], has("150")),
    ("spanish", [{"role": "user", "content": "Translate 'good morning' into Spanish. Reply with just the translation."}], has("buenos d")),
    ("capitals", [{"role": "system", "content": "Reply in ALL CAPITAL LETTERS."}, {"role": "user", "content": "Name the largest planet of the solar system."}], lambda t: "JUPITER" in t and t == t.upper()),
    ("fruits", [{"role": "user", "content": "List exactly three fruits, one per line, in lowercase, with no other text."}],
     lambda t: len([l for l in t.strip().splitlines() if l.strip()]) == 3 and all(re.fullmatch(r"[a-z ]+", l.strip()) for l in t.strip().splitlines() if l.strip())),
    ("json", [{"role": "user", "content": "Return only a JSON object with the keys name and age for Alice, who is 30."}],
     lambda t: (lambda d: d.get("name") == "Alice" and d.get("age") == 30)(json.loads(re.search(r"\{.*\}", t, re.S).group(0))) if re.search(r"\{.*\}", t, re.S) else False),
    ("is_prime", [{"role": "user", "content": "Write a Python function is_prime(n) that returns True if n is prime. Reply with only the code in a ```python block."}],
     lambda t: run_python(extract_code(t), "assert is_prime(2) and is_prime(97) and not is_prime(1) and not is_prime(15) and not is_prime(0) and is_prime(7919)")),
    ("reverse_words", [{"role": "user", "content": "Write a Python function reverse_words(s) that returns the words of the string s in reverse order, joined by single spaces. Reply with only the code in a ```python block."}],
     lambda t: run_python(extract_code(t), "assert reverse_words('hello big world') == 'world big hello' and reverse_words('a') == 'a'")),
    ("fizzbuzz", [{"role": "user", "content": "Write a Python function fizzbuzz(n) that returns a list of strings for 1..n: 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for both, else the number as a string. Reply with only the code in a ```python block."}],
     lambda t: run_python(extract_code(t), "r = fizzbuzz(15); assert r[2] == 'Fizz' and r[4] == 'Buzz' and r[14] == 'FizzBuzz' and r[0] == '1' and len(r) == 15")),
]


def run_follow(srv, gate=None):
    """The instruction-following cases of ifcases.py (format constraints: case, count, JSON only, one word, a given language) through the engine; `gate`: the names the exact model answers with high confidence
    (if_report.py writes bench/if_gate.json), the only ones that count."""
    import ifcases
    rows = []
    for name, msgs, canon, check in ifcases.FORMAT:
        r = srv.chat(msgs, 200)
        bad = looks_degenerate(r["text"], r["completion_tokens"], cap=200)
        try:
            ok = bool(check(r["text"]))
        except Exception:  # noqa: BLE001
            ok = False
        ok = ok and bad is None and r["finish"] == "stop"
        counted = gate is None or name in gate
        rows.append({"id": name, "pass": ok, "counted": counted, "degenerate": bad, "finish": r["finish"], "tokens": r["completion_tokens"], "reply": r["text"][:300]})
        print(f"  {name:14s} {'PASS' if ok else 'FAIL'}{'' if counted else ' (not counted: the exact model is not sure of it)'}  {r['finish']:6s} {r['completion_tokens']:4d} tokens" + (f"  [{bad}]" if bad else "") + f"  {r['text'].strip()[:60]!r}", flush=True)
    return rows


def run_chat(srv):
    rows = []
    for name, msgs, check in CHAT:
        r = srv.chat(msgs, 400)
        bad = looks_degenerate(r["text"], r["completion_tokens"], cap=400)
        try:
            ok = bool(check(r["text"]))
        except Exception:  # noqa: BLE001
            ok = False
        ok = ok and bad is None and r["finish"] == "stop"
        rows.append({"id": name, "pass": ok, "degenerate": bad, "finish": r["finish"], "tokens": r["completion_tokens"], "reply": r["text"][:300]})
        print(f"  {name:14s} {'PASS' if ok else 'FAIL'}  {r['finish']:6s} {r['completion_tokens']:4d} tokens" + (f"  [{bad}]" if bad else "") + f"  {r['text'].strip()[:60]!r}", flush=True)
    return rows


# ---------------------------------------------------------------------------------------------------------------------------------- GSM8K
def analyse_gsm8k(slice_dir):
    import zipfile
    from glob import glob
    rows = []
    for p in sorted(glob(f"{slice_dir}/logs/*.eval")):
        z = zipfile.ZipFile(p)
        for n in z.namelist():
            if n.startswith("samples/") and n.endswith(".json"):
                s = json.loads(z.read(n))
                out = s.get("output") or {}
                ch = (out.get("choices") or [{}])[0]
                text = ((ch.get("message") or {}).get("content")) or ""
                if isinstance(text, list):
                    text = "".join(c.get("text", "") for c in text if isinstance(c, dict))
                sc = next(iter((s.get("scores") or {"": {"value": None}}).values()))
                toks = (out.get("usage") or {}).get("output_tokens")
                bad = looks_degenerate(text, toks)
                if bad is None and ch.get("stop_reason") == "max_tokens":
                    bad = "hit the token cap"
                if bad is None and "ANSWER" not in text:
                    bad = "no ANSWER line"
                rows.append({"id": s["id"], "correct": sc.get("value") == "C", "tokens": toks, "degenerate": bad, "tail": text[-120:]})
    n = len(rows)
    res = {"questions": n, "correct": sum(r["correct"] for r in rows), "degenerate": sum(1 for r in rows if r["degenerate"]), "rows": rows}
    print(f"  GSM8K slice: {res['correct']} / {n} correct, {res['degenerate']} degenerate (loop, cap, garbage or no ANSWER line)")
    for r in rows:
        if r["degenerate"]:
            print(f"    {r['id']}: {r['degenerate']}  tail {r['tail'][-60:]!r}")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://127.0.0.1:8011")
    ap.add_argument("--snap", default=None)
    ap.add_argument("--out", default="bench/accept")
    ap.add_argument("--tests", default="needle,chat")
    ap.add_argument("--lengths", default=",".join(map(str, LENGTHS)))
    ap.add_argument("--exact-pass", default=None, help="JSON {needle id: true/false} from needle_exact.py")
    ap.add_argument("--if-gate", default=None, help="JSON list of the instruction-following case names the exact model answers with high confidence (if_report.py: bench/if_gate.json)")
    ap.add_argument("--write-prompts", default=None)
    ap.add_argument("--analyse-gsm8k", default=None)
    a = ap.parse_args()
    if a.analyse_gsm8k:
        json.dump(analyse_gsm8k(a.analyse_gsm8k), open(a.out + "_gsm8k.json", "w"), indent=1)
        return
    lengths = [int(x) for x in a.lengths.split(",")]
    if a.write_prompts:
        P = needle_prompts(a.snap, lengths)
        json.dump(P, open(a.write_prompts, "w"))
        print(f"{len(P)} needle prompts written to {a.write_prompts}")
        return
    os.makedirs(a.out, exist_ok=True)
    srv = Server(a.base)
    res, ok = {}, True
    exact = json.load(open(a.exact_pass)) if a.exact_pass else None
    for t in a.tests.split(","):
        print(f"== {t}", flush=True)
        if t == "needle":
            rows = run_needle(srv, needle_prompts(a.snap, lengths), exact)
            counted = [r for r in rows if r["exact_passes"] in (None, True)]
            res["needle"] = {"rows": rows, "passed": sum(r["pass"] for r in counted), "counted": len(counted)}
            ok &= all(r["pass"] for r in counted)
            print(f"  needle: {res['needle']['passed']} / {res['needle']['counted']} counted cases passed")
        elif t == "chat":
            rows = run_chat(srv)
            res["chat"] = {"rows": rows, "passed": sum(r["pass"] for r in rows), "counted": len(rows)}
            ok &= all(r["pass"] for r in rows)
            print(f"  chat/code: {res['chat']['passed']} / {len(rows)} passed")
        elif t == "follow":
            rows = run_follow(srv, set(json.load(open(a.if_gate))) if a.if_gate else None)
            cnt = [r for r in rows if r["counted"]]
            res["follow"] = {"rows": rows, "passed": sum(r["pass"] for r in cnt), "counted": len(cnt)}
            ok &= all(r["pass"] for r in cnt)
            print(f"  instruction following: {res['follow']['passed']} / {len(cnt)} counted cases passed")
    json.dump(res, open(f"{a.out}/accept.json", "w"), indent=1)
    print("ACCEPTANCE", "PASSED" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
