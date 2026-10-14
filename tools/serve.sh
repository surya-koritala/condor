#!/usr/bin/env bash
# The chat page and the API (OpenAI and Anthropic) on http://127.0.0.1:PORT (default 8080).
#   tools/serve.sh [--fast] [PORT]        precise mode by default; --fast uses the fast experts (tools/download.sh --fast)
#   GLYD_CTX=65536 tools/serve.sh         the context in tokens (default 32768, up to 262144)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}/env.sh"
DIR=${GLYD_HF:-$GLYD_QWEN/hf}
if [ "${1:-}" = --fast ]; then shift; PACK=$DIR/pack; MODE=; else PACK=$DIR/precise; MODE=--precise; fi
[ -e "$PACK" ] || { echo "$PACK is missing: run tools/download.sh$([ -z "$MODE" ] && echo ' --fast') first." >&2; exit 1; }
exec "$GLYD_ENGINE" qwenserve "$DIR/model" "$PACK" $MODE --ctx "${GLYD_CTX:-32768}" --port "${1:-8080}" --page "$HERE"
