#!/usr/bin/env bash
# How fast it is on this computer: a short chat, then prompts of about 4K, 16K and 32K tokens, against the running server (tools/serve.sh).
# About 5 minutes; writes bench-report.md to share.   tools/bench.sh [URL]   (default http://127.0.0.1:8080)
set -euo pipefail
. "${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}/env.sh"
exec "$GLYD_ENGINE" qwenbench --url "${1:-http://127.0.0.1:8080}" --out bench-report.md
