# Changelog

## 0.1.1

- The engine runs on Ubuntu 22.04 and other Linux distributions from 2022 on (it needed a newer system library before).
- setup.sh says how to update an NVIDIA driver older than 580.
- Tested on an NVIDIA A10 (Ampere, 24 GB) on a clean Ubuntu 22.04 machine: 101 tokens/s in chat.

## 0.1.0

- Qwen3.8-Flash-Next on one 16 GB NVIDIA GPU with 64 GB of RAM: fast and precise modes, contexts up to 262,144 tokens.
- The chat app (Chat, Monitor, About), the OpenAI- and Anthropic-compatible APIs, an MCP server and a speed test.
