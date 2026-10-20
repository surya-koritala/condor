# Changelog

## 0.2.2

- Fast mode is closer to the original at the same size: its experts are packed a new way, still 2 bits a weight. KL divergence vs the
  original bf16 (wikitext-2, 32 x 512): 0.53 -> 0.39, top-1 79% -> 83%. On a mixed text set (code, docs, five languages, an agent
  transcript), over the original's 64 most likely tokens: 0.397 -> 0.295, top-1 78% -> 81%. GSM8K 149/150, MMLU-Pro 121/150 (the v0.2.1
  experts on the same engine, the same night: 147 and 124). Writing after a short / 4K / 30K prompt: 124 / 116 / 125 tok/s, vs
  120 / 117 / 141 with the v0.2.1 experts on the same night; prompts are read at the same speed.
- The fast experts are a new download, `fast/` (29 GB): `./setup.sh` fetches them, or `tools/download.sh --fast`; the old `pack/` folder
  can be deleted after. Engines before v0.2.2 keep using `pack/`. 66 GB in all for fast mode (was 68).
- Known: with the new fast experts two of the 19 tool-call tests in `tests/test_agents.py` fail (a forced tool choice gets a second call;
  the 12-round tool loop overruns), 19 of 19 with precise and best. On the list for v0.2.3.
- The project is Condor and the repository is surya-koritala/condor (old links redirect). More Flash-class models will come here.
- Precise and best are unchanged.

## 0.2.1

- Best mode (`--best`, `-Best` on Windows; setup asks): about 30% of the experts at 4 bits, the rest at 3, calibrated like precise.
  KL divergence vs bf16 (wikitext-2, 32 x 512) 0.165 vs precise's 0.22, top-1 89% vs 87%; GSM8K 149/150, MMLU-Pro 128/150. About 10%
  slower than precise on short prompts, about the same at 30K. 52 GB of experts (89 GB in all), 64 GB of RAM. Precise stays the default.
- The MCP server's glyd_start: `mode` fast and best now work on Linux (it passed a flag serve.sh didn't take), and precise is the
  default it describes.
- The MCP server's glyd_stop on Ubuntu 22.04: it left the server running and could stop the program that started the MCP server
  (22.04's `kill` read the server's process group as its own). Fixed; tested on 22.04 and 26.04.
- The Monitor tab and the bench block name best mode (they said fast).
- setup.sh installs the engine again when the latest release is newer than the installed one (on Windows, run tools\install.ps1
  after `git pull` for now).
- README: the IPv4 workaround is gone (the engine falls back to IPv4 by itself).

## 0.2.0

- Precise mode is closer to the original model: its experts are packed again with calibration, and the always-on matrices are kept at
  six bits. KL divergence vs the original bf16 (wikitext-2 test, 32 x 512): mean 0.40 -> 0.22, median 0.06 -> 0.02, top-1 82% -> 88%.
  The download stays about 82 GB; writing is about 10% slower; VRAM in use about 15.4 of 16 GB.
- Tool calls work the way agent frameworks send them (streamed, several in one answer, tool_choice), and JSON mode (response_format).
- A second request waits for the first instead of failing; a client that leaves while waiting is dropped cleanly.
- bench/compare.py: the same speed test and questions against any OpenAI-compatible server, to compare on your own machine.
- tools/bench.sh prints a block to paste into a "Bench result" issue. docs/HOW_IT_WORKS.md and docs/CLIENTS.md.
- Windows 10/11 x64, native: setup.ps1 and tools\\*.ps1 (the .sh scripts' twins). Tested on one machine so far (an L4, 64 GB).
- 12 GB cards and 32 GB of RAM: setup picks fast mode below 64 GB of RAM; measured on a 4080 SUPER held back to those sizes.
- The repository is now surya-koritala/glyd-condor (Glyd Condor); the old links redirect.

## 0.1.1

- The engine runs on Ubuntu 22.04 and other Linux distributions from 2022 on (it needed a newer system library before).
- setup.sh says how to update an NVIDIA driver older than 580.
- Tested on an NVIDIA A10 (Ampere, 24 GB) on a clean Ubuntu 22.04 machine: 101 tokens/s in chat.

## 0.1.0

- Qwen3.8-Flash-Next on one 16 GB NVIDIA GPU with 64 GB of RAM: fast and precise modes, contexts up to 262,144 tokens.
- The chat app (Chat, Monitor, About), the OpenAI- and Anthropic-compatible APIs, an MCP server and a speed test.
