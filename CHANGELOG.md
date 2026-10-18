# Changelog

## 0.2.0

- Precise mode is closer to the original model: its experts are packed again with calibration, and the always-on matrices are kept at
  six bits. KL divergence vs the original bf16 (wikitext-2 test, 32 x 512): mean 0.40 -> 0.22, median 0.06 -> 0.02, top-1 82% -> 88%.
  The download stays about 82 GB; writing is about 10% slower; VRAM in use about 15.4 of 16 GB.
- Tool calls work the way agent frameworks send them (streamed, several in one answer, tool_choice), and JSON mode (response_format).
- A second request waits for the first instead of failing; a client that leaves while waiting is dropped cleanly.
- bench/compare.py: the same speed test and questions against any OpenAI-compatible server, to compare on your own machine.
- tools/bench.sh prints a block to paste into a "Bench result" issue. docs/HOW_IT_WORKS.md and docs/CLIENTS.md.

## 0.1.1

- The engine runs on Ubuntu 22.04 and other Linux distributions from 2022 on (it needed a newer system library before).
- setup.sh says how to update an NVIDIA driver older than 580.
- Tested on an NVIDIA A10 (Ampere, 24 GB) on a clean Ubuntu 22.04 machine: 101 tokens/s in chat.

## 0.1.0

- Qwen3.8-Flash-Next on one 16 GB NVIDIA GPU with 64 GB of RAM: fast and precise modes, contexts up to 262,144 tokens.
- The chat app (Chat, Monitor, About), the OpenAI- and Anthropic-compatible APIs, an MCP server and a speed test.
