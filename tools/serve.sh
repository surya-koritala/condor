#!/usr/bin/env bash
# The chat page and the API (OpenAI and Anthropic) on http://127.0.0.1:PORT (default 8080).
#   tools/serve.sh [--precise] [PORT]        fast mode by default; --precise uses the precision pack (tools/download.sh --precise)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
. "${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}/env.sh"
DIR=${GLYD_HF:-$GLYD_QWEN/hf}
if [ "${1:-}" = --precise ]; then shift; PACK=$DIR/precise; MODE=--precise; else PACK=$DIR/pack; MODE=; fi
exec python "$HERE/server.py" --model "$DIR/model" --pack "$PACK" $MODE --engine "$GLYD_ENGINE" --port "${1:-8080}"
