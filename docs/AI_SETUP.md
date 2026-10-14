# Setting up Qwen3.8-Flash-Next on Glyd: steps for an AI assistant

You are setting up Glyd's Qwen3.8-Flash-Next (Hummingbird level) for a user: Qwen3.8-Flash-Next running on their own NVIDIA GPU, with a chat page and an OpenAI- and
Anthropic-compatible API. Follow these steps in order, and tell the user what you find at each one.

## 1. Check the computer

Run these and compare with the requirements:

```sh
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
free -g | awk '/^Mem:/ {print $2 " GiB RAM"}'
df -h ~ | tail -1
uname -sm
```

| Requirement | Needed |
|---|---|
| System | Linux on x86-64. On Windows, use WSL2 with the NVIDIA driver for WSL. |
| GPU | NVIDIA, Ampere or newer (RTX 30, 40 or 50 series, A-series, H100), 16 GB or more |
| Driver | 580 or newer |
| RAM | 64 GB |
| Disk | about 75 GB free (110 GB for precise mode too) |

If something is short, stop and tell the user which requirement, and by how much.

## 2. Install

```sh
git clone https://github.com/surya-koritala/glyd-qwen-3.8-flash && cd glyd-qwen-3.8-flash
tools/install.sh                  # the compiled engine and a small Python venv under ~/.glyd-qwen-3.8-flash; no sudo
. ~/.glyd-qwen-3.8-flash/env.sh
tools/download.sh                 # about 68 GB; add --precise for precise mode (the precision pack, about 41 GB more)
```

The download resumes if it stops: run it again.

## 3. Start it

```sh
tools/serve.sh                    # fast mode; tools/serve.sh --precise for precise mode
```

Loading takes about a minute. Then:

- the chat page is at http://127.0.0.1:8080/;
- the OpenAI-compatible API is at http://127.0.0.1:8080/v1, model `qwen3.8-flash-next`, any API key;
- the Anthropic-compatible API is at http://127.0.0.1:8080/v1/messages.

Check that it answers:

```sh
curl -s http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-flash-next","messages":[{"role":"user","content":"Say hello in five words."}]}'
```

## 4. Connect the user's tools

- **Any OpenAI-compatible app** (Open WebUI, Continue, Cline, LibreChat): base URL `http://127.0.0.1:8080/v1`, model `qwen3.8-flash-next`.
- **Anthropic-compatible tools:** base URL `http://127.0.0.1:8080`.
- **MCP:** `claude mcp add glyd -- python3 "$PWD/tools/mcp_server.py"` gives an AI tool `glyd_start`, `_stop`, `_status` and `_ask`.

## 5. Measure it

`tools/bench.py` takes about 5 minutes. It measures a chat and 4K, 16K and 32K prompts, and writes `bench-report.md` for the user.
