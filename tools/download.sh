#!/usr/bin/env bash
# The model from Hugging Face (no account needed), glyd/Qwen3.8-Flash-Next-hummingbird: model/ (Qwen's tokenizer and configs, and the weights
# outside the experts, 37 GB) and the experts for one mode: precise/ (45 GB, the default) or, with --fast, pack/ (31 GB). The files go to the
# Hugging Face cache (~/.cache/huggingface, or $HF_HUB_CACHE), which other tools share; DIR gets links to them. It resumes if it stops.
#   tools/download.sh [--fast] [DIR]        (default DIR $GLYD_QWEN/hf)
set -euo pipefail
. "${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}/env.sh"
MODE=--precise; [ "${1:-}" = --fast ] && { MODE=; shift; }
exec "$GLYD_ENGINE" qwenget glyd/Qwen3.8-Flash-Next-hummingbird "${1:-$GLYD_QWEN/hf}" $MODE
