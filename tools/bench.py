#!/usr/bin/env python3
"""How fast Qwen3.8-Flash-Next on Glyd is on this computer: a short chat, then prompts of about 4K, 16K and 32K tokens, against a running server
(tools/serve.sh). Writes a Markdown report to share, with the GPU, CPU and RAM. Standard library only.
    tools/bench.py [--url http://127.0.0.1:8080] [--out bench-report.md] [--lengths 4000,16000,32000]"""
import argparse
import json
import os
import platform
import subprocess
import time
import urllib.request

FILLER = ("The history of the printing press is a story of many hands. Workshops in several cities tried movable type, inks and presses, "
          "and each change spread along trade routes, carried by apprentices who set up shops of their own. ")


def chat(url, messages, max_tokens):
    """One streamed chat request: (seconds to the first word, words a second after it, tokens out)."""
    body = json.dumps({"messages": messages, "max_tokens": max_tokens, "stream": True, "stream_options": {"include_usage": True},
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(url + "/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    t0, first, usage = time.time(), None, {}
    with urllib.request.urlopen(req, timeout=3600) as r:
        for line in r:
            line = line.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            d = json.loads(line[5:])
            usage = d.get("usage") or usage
            for c in d.get("choices", []):
                if (c.get("delta") or {}).get("content") and first is None:
                    first = time.time()
    t1 = time.time()
    n = usage.get("completion_tokens", 0)
    first = first or t1
    return first - t0, (n - 1) / (t1 - first) if n > 1 and t1 > first else 0.0, n, usage.get("prompt_tokens", 0)


def machine():
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:  # noqa: BLE001
            return "?"
    gpu = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), platform.processor()) if os.path.exists("/proc/cpuinfo") else platform.processor()
    ram = run(["free", "-g"]).splitlines()[1].split()[1] + " GiB" if platform.system() == "Linux" else "?"
    return gpu, cpu, ram


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8080"); ap.add_argument("--out", default="bench-report.md")
    ap.add_argument("--lengths", default="4000,16000,32000")
    a = ap.parse_args()
    gpu, cpu, ram = machine()
    rows = []
    chat(a.url, [{"role": "user", "content": "Say hello."}], 16)   # (warm-up)
    q = "Explain, step by step, how a hash table handles collisions, then compare open addressing with chaining."
    ttft, tps, n, pin = chat(a.url, [{"role": "user", "content": q}], 512)
    rows.append(("Chat (short prompt)", pin, ttft, tps, n))
    print(f"chat: {tps:.1f} tokens/s", flush=True)
    for want in [int(x) for x in a.lengths.split(",") if x]:
        text = FILLER * (want // 45 + 1)
        ttft, tps, n, pin = chat(a.url, [{"role": "user", "content": text[: want * 4] + "\n\nSummarise the text above in three sentences."}], 256)
        rows.append((f"{want // 1000}K prompt", pin, ttft, tps, n))
        print(f"{want // 1000}K: read in {ttft:.1f} s, then {tps:.1f} tokens/s", flush=True)
    with open(a.out, "w") as f:
        f.write(f"# Qwen3.8-Flash-Next on Glyd: speed\n\n- GPU: {gpu}\n- CPU: {cpu}\n- RAM: {ram}\n- When: {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("| Test | Prompt tokens | Reading the prompt (s) | Writing (tokens/s) | Tokens written |\n|---|--:|--:|--:|--:|\n")
        for name, pin, ttft, tps, n in rows:
            f.write(f"| {name} | {pin} | {ttft:.1f} | {tps:.1f} | {n} |\n")
    print(f"report: {a.out}")


if __name__ == "__main__":
    main()
