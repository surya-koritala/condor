# Condor

Qwen3.8-Flash-Next (180B, MoE) on one 12-16 GB NVIDIA GPU with 32-64 GB of RAM, on Linux or Windows. Our own engine and our own
compressed weights. OpenAI- and Anthropic-compatible APIs, a chat page, MCP. Free for personal use. More Flash-class models will come here.

![Star Drift, a space shooter the model wrote in one prompt](docs/media/star-drift.gif)

The model wrote that game in one prompt on my 4080 SUPER, unedited. 3 of 6 tries were playable in precise mode; all 6 are in
[examples/star-drift](examples/star-drift), broken ones included.

## How it works, in short

- The engine knows which experts the model routes to. The busy ones sit on the GPU, the rest in RAM; the CPU computes the misses while
  the GPU works on the layer.
- Experts are compressed by use: busy ones keep more bits.
- The model's own draft head guesses the next token and the big model checks it in the same pass.
- Long prompts go through the model a layer at a time, so a 32K prompt doesn't blow up memory.

Details: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## Numbers

RTX 4080 SUPER 16 GB, Ryzen 9 7950X3D, 64 GB RAM, Ubuntu 26.04. Greedy, thinking off, `bench/compare.py`.

```
                                     precise         best            fast (v0.2.2)
experts, avg bits/weight             ~3.0            ~3.4            ~2.0
attention + rest                     6 bit           6 bit           4-5 bit
download                             82 GB           89 GB           66 GB
KL divergence vs bf16 (wikitext-2)   0.22            0.165           0.39

writing, short / 4K / 30K prompt     118 / 110 / 96  104 / 92 / 97   124 / 116 / 125 tok/s
greedy, short prompt (best case)     ~130 tok/s      ~105 tok/s      ~169 tok/s
read a 30K-token prompt              7.5 s           7.5 s           7.4 s

GSM8K   (150 q, Inspect AI)          148/150         149/150         149/150
MMLU-Pro (150 q, Inspect AI)         126/150         128/150         121/150
```

Fast was measured on 2026-10-19 on this build; precise and best in October's earlier runs (v0.2.0, v0.2.1). GSM8K is a sanity check that
compression didn't break reasoning; MMLU-Pro says more. Logs in [results/](results), scripts in
[bench/](bench). Also tested on a cloud A10 (24 GB) and, on Windows, an L4 (24 GB).

Your own machine: `tools/bench.sh` (about 5 min) prints a block to paste into a "Bench result" issue. To compare with what you run now,
`bench/compare.py` runs the same prompts and questions against any OpenAI-compatible server ([bench/README.md](bench/README.md)); I
don't publish comparisons myself.

## What you need

- NVIDIA RTX 30/40/50 (or an Ampere+ workstation card), 12 GB+ VRAM (16 GB recommended), driver 580+.
- 32 GB+ RAM. Precise and best want 64 GB; fast is the mode for 32 GB.
- A decent CPU. Experts that miss the GPU cache run on it, so it matters about as much as the GPU: a 16-core 7950X3D does a pass in
  ~16 ms, an 8-core Zen 2 with DDR4 in ~70 ms.
- ~90 GB of free disk (73 GB for fast, 96 GB for best), on an SSD.
- Linux x86-64 (tested on Ubuntu 22.04 and 24.04) or Windows 10/11 x64. WSL untested.

12 GB cards and 32 GB of RAM: measured on my 4080 held back to those sizes, fast mode does about 145 tok/s on a short prompt. A 3060
has half the 4080's bandwidth, so expect roughly half that. Not yet run on a real 12 GB card.

## Install

```sh
git clone https://github.com/surya-koritala/condor && cd condor
./setup.sh
```

It checks GPU, RAM and disk, installs the engine (no sudo), downloads the model (resumable: rerun if it stops), asks the mode and the
context, and opens `http://127.0.0.1:8080`. Enter takes the defaults. Run it again to start next time; nothing downloads twice.

Windows (PowerShell, NVIDIA driver 580+):

```powershell
git clone https://github.com/surya-koritala/condor; cd condor
powershell -ExecutionPolicy Bypass -File setup.ps1
```

`tools\download.ps1` and `tools\serve.ps1` (`-Fast`, `-Best`) are the twins of the `.sh` scripts. Tested on one Windows machine so
far (an AWS L4, 64 GB RAM): clean install, `tests/` passing, 47 tok/s chat in fast mode (the L4 has 40% of a 4080's
bandwidth). Not yet tested on a GeForce card under Windows or in WSL2.

With an AI coding assistant: `Set up https://github.com/surya-koritala/condor on this PC - follow docs/AI_SETUP.md`.

## Modes

- **precise** (default): the one for code; long programs come out right far more often.
- **best**: closest to the original (KL 0.165), about 10% slower, 7 GB more; 64 GB of RAM.
- **fast**: 15-20% quicker than precise, 66 GB, runs with 32 GB of RAM. v0.2.2 packs its experts a new way at the same size: KL
  0.53 -> 0.39, top-1 agreement with the original 79% -> 83%. Two of the 19 tool-call tests in `tests/` fail with it (see the CHANGELOG).

Switch: `tools/download.sh --best` (or `--fast`), then `tools/serve.sh --best`. No flag means precise.

## Using it

- Chat: `http://127.0.0.1:8080`. Renders tables, code and diagrams, runs the HTML the model writes, shows GPU/CPU/RAM live.
- OpenAI-compatible API at `http://127.0.0.1:8080/v1` (any key, any model name); Anthropic-compatible at `/v1/messages`, e.g.
  `ANTHROPIC_BASE_URL=http://127.0.0.1:8080 claude`.
- Agent frameworks and tool calls, what's tested: [docs/CLIENTS.md](docs/CLIENTS.md).
- MCP: `claude mcp add glyd -- ~/.glyd-qwen-3.8-flash/bin/glyd-engine qwenmcp --repo /path/to/condor`
- Thinking is off by default; turn it on in chat settings or with `reasoning_effort`.
- Context up to 262,144 tokens; follow-ups reuse the conversation and start in under a second.

## Known limits

- Text only; the model's vision part isn't wired up yet (#13).
- NVIDIA only, 12 GB minimum; no macOS or AMD (#8, AMD in progress).
- One request at a time; others queue (#9, in progress).
- Fast mode is weaker on long code.
- Short on free RAM, it gets slow and the disk gets busy: close what's eating RAM.

## Troubleshooting

- Download stopped: rerun `./setup.sh`.
- "No NVIDIA driver found" or "580 or newer is needed": update the driver (Ubuntu: `sudo apt install nvidia-driver-595`), reboot.
- Port 8080 in use: it's probably already running; or `tools/serve.sh 8090`.
- Download stuck at 0 MB/s then "Connection reset by peer": IPv6 to the Hub's CDN is broken on some networks. The engine falls back to
  IPv4 by itself; `GLYD_IPV4=1 ./setup.sh` forces it from the start.
- Slower than the numbers above: check the CPU (above) and the context: on a 16 GB card a bigger `GLYD_CTX` takes VRAM from the expert
  cache (one user saw 11-15% slower at 131,072 than at the default 32,768).

Anything else: open an [issue](https://github.com/surya-koritala/condor/issues) with what it printed. Security: [SECURITY.md](SECURITY.md).

## License

- Model: [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) by the Qwen team, under its license; the compressed
  weights on [Hugging Face](https://huggingface.co/glyd/Qwen3.8-Flash-Next-hummingbird) carry the same license.
- This repo (scripts, chat app, benchmarks, docs): [Apache 2.0](LICENSE).
- The engine ships compiled in [releases](https://github.com/surya-koritala/condor/releases) under [BUSL 1.1](ENGINE-LICENSE): free for
  personal, research and non-commercial use; commercial use needs a license (suryakoritala@getglyd.com). Each version turns Apache 2.0
  four years after release.

PRs welcome: [CONTRIBUTING.md](CONTRIBUTING.md). Thanks to the Qwen team for open-weighting this model.
