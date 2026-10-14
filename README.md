<h1 align="center">Qwen3.8-Flash-Next on Glyd</h1>

<p align="center"><b>Run a 180-billion-parameter AI model on one 16 GB NVIDIA graphics card</b><br>
Linux · 64 GB of RAM · free for personal use</p>

<p align="center"><a href="examples/star-drift"><img src="docs/media/star-drift.gif" width="720" alt="Star Drift, a space shooter the model wrote in one prompt, playing itself"></a><br>
<sub>A space shooter written in one prompt by the model on an RTX 4080 SUPER, unedited ·
<a href="examples/star-drift">the prompt, the file and how often it works</a></sub></p>

This runs **[Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)** on a normal PC with [Glyd](https://getglyd.com)'s own
engine. It's a large, smart AI model that usually needs a server. It chats, writes code and works with your apps and coding agents.
Nothing leaves your PC.

## How fast is it?

Measured on one PC: an RTX 4080 SUPER (16 GB), a Ryzen 9 7950X3D and 64 GB of RAM. A token is about ¾ of a word.

| | Precise | Fast |
| --- | ---: | ---: |
| **Writes answers** in a chat (the default settings) | 117 tokens/s | 135 tokens/s |
| **Writes answers**, top speed (a short prompt, greedy) | 145 tokens/s | 169–173 tokens/s |
| **Reads your prompt** (32,000 tokens) | about 7 s | about 7 s |

Run `tools/bench.sh` to measure your PC.

## How smart is it?

Inspect AI, 150 GSM8K and 150 MMLU-Pro questions, thinking off:

| | Precise | Fast |
| --- | ---: | ---: |
| **GSM8K** (school math) | 148 of 150 | 148 of 150 |
| **MMLU-Pro** (hard knowledge questions) | 124 of 150 | 118 of 150 |
| **A full game in one prompt** ([Star Drift](examples/star-drift)) | 3 of 6 playable | 1 of 6 |

The logs: [results/v0.1.0](results/v0.1.0).

## What you need

| | |
| --- | --- |
| **Graphics card** | NVIDIA GeForce RTX 30, 40 or 50 series, or a workstation card from the same generations (Ampere or newer), with **16 GB of VRAM or more** and driver 580 or newer. |
| **RAM** | 64 GB. |
| **Disk** | About 90 GB free (75 GB for fast mode). An SSD makes the first start much faster. |
| **System** | Linux on x86-64: Ubuntu 22.04 or newer, or another distribution from 2022 on (tested on Ubuntu 22.04 and 24.04). Windows is not supported yet. |

## Install

### Let your AI set it up

Using an AI coding assistant (Claude Code, Cursor, Codex, ...)? Paste this into it:

```text
Set up Qwen3.8-Flash-Next on Glyd on this PC for me: https://github.com/surya-koritala/glyd-qwen-3.8-flash - follow docs/AI_SETUP.md in that repository.
```

### Or do it yourself

```sh
git clone https://github.com/surya-koritala/glyd-qwen-3.8-flash && cd glyd-qwen-3.8-flash
./setup.sh
```

It checks your graphics card, RAM and disk, installs the engine (no sudo, nothing else to install) and downloads the model (about 82 GB;
if the download stops, run it again and it continues). It asks two questions, precise or fast and how much context, then opens the
app in your browser at `http://127.0.0.1:8080`. Press Enter for the recommended answers.

**Next time**, run `./setup.sh` again: it starts right away and downloads nothing twice. Press Ctrl+C to stop it.

## Precise or fast?

- **Precise** (recommended, an 82 GB download) keeps more detail in the model, so its answers are closer to the original model's. It is
  the better choice for code: long programs come out right much more often.
- **Fast** (a 68 GB download) writes about 15-20% faster, with less accuracy: fine for chat, weaker for long code.

`./setup.sh` asks; to switch later, `tools/download.sh --fast` and `tools/serve.sh --fast` (or the same without `--fast` for precise).

## Using it

- **In the browser:** `http://127.0.0.1:8080` has **Chat**, a live **Monitor** of the model and your GPU, CPU and RAM, and **About**.
  The chat shows tables and code, draws flowcharts, and runs the web pages, games and animations the model writes in a live preview.
- **Your apps and coding agents:** add an "OpenAI-compatible" provider with the base URL **`http://127.0.0.1:8080/v1`**. Any API key and
  any model name work.
  - Apps that use Anthropic's API: `http://127.0.0.1:8080/v1/messages` (Claude Code: `ANTHROPIC_BASE_URL=http://127.0.0.1:8080 claude`).
  - AI tools can also start, stop and ask it through its MCP server:
    `claude mcp add glyd -- ~/.glyd-qwen-3.8-flash/bin/glyd-engine qwenmcp --repo /path/to/glyd-qwen-3.8-flash`.
- **Thinking:** off by default, which is the fastest. Turn it on in the chat's settings, or with `reasoning_effort` in your app.
- **Long prompts:** up to 262,144 tokens of context (`./setup.sh` asks). A 32,000-token prompt is read in about 7 seconds; follow-up
  messages reuse the conversation and start in under a second.
- **One request at a time:** others wait their turn.
- **Is it fast on your PC?** With it running, `tools/bench.sh` measures a chat and 4K, 16K and 32K prompts in about 5 minutes and
  writes `bench-report.md` to share.

## Something went wrong?

- **It stopped while downloading.** Run `./setup.sh` again. It continues where it stopped.
- **"No NVIDIA driver found" or "580 or newer is needed".** Install or update the NVIDIA driver (on Ubuntu: `sudo apt install nvidia-driver-595`), reboot, then run it again.
- **It's very slow and the disk is busy.** Your PC doesn't have enough free RAM. Close other programs (browsers use a lot).
- **Port 8080 is already in use.** It's probably already running. Or start it on another port: `tools/serve.sh 8090`.

Still stuck? Open an [issue](https://github.com/surya-koritala/glyd-qwen-3.8-flash/issues) with what it printed. Found a security
problem? Report it privately: [SECURITY.md](SECURITY.md).

## How does it work?

The model is a team of 512 small specialists ("experts") in each of its 48 layers, and each word needs only 10 of them. A 16 GB card
can't hold them all, so Glyd shares the work across your PC:

- **Your graphics card** keeps the experts that are used most. **Your RAM** holds the rest, and **your processor** works on those at the
  same time.
- **Compressed by use:** Glyd stores the experts in 2 to 4 bits each, with more detail where the model needs it most.
- **Guess, then check:** the model's own small helper guesses the next few words, and the big model checks them all at once.
- **Long prompts layer by layer:** a 32,000-token prompt goes through the model one layer at a time.

## License and credits

The model is [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) by the Qwen team, under its own license; Glyd's
compressed copy on [Hugging Face](https://huggingface.co/glyd/Qwen3.8-Flash-Next-hummingbird) carries the same license.

- This repository (the setup scripts, the chat app, the benchmarks and the documentation) is open source under the
  [Apache License 2.0](LICENSE).
- The Glyd engine ships compiled in the [releases](https://github.com/surya-koritala/glyd-qwen-3.8-flash/releases), under the
  [Business Source License 1.1](ENGINE-LICENSE): free for personal, research and other non-commercial use. Commercial use needs a license
  (suryakoritala@getglyd.com). Each version becomes Apache-2.0 four years after its release.

Contributions are welcome: [CONTRIBUTING.md](CONTRIBUTING.md).
