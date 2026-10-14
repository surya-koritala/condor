#!/usr/bin/env bash
# Glyd's build of Qwen3.8-Flash-Next from Hugging Face (no token needed): the model (Qwen's tokenizer, configs and the weights the engine keeps
# outside its experts) and the experts' pack. One Hugging Face repo, glyd/Qwen3.8-Flash-Next-hummingbird: model/ and pack/ (about 68 GB, fast mode);
# --precise adds its precise/ folder, the precision pack (about 45 GB).
#   tools/download.sh [--precise] [DIR]        (default DIR $GLYD_QWEN/hf)
set -euo pipefail
. "${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}/env.sh"
PRECISE=0; [ "${1:-}" = --precise ] && { PRECISE=1; shift; }
DIR=${1:-$GLYD_QWEN/hf}
export HF_XET_HIGH_PERFORMANCE=1
hf download glyd/Qwen3.8-Flash-Next-hummingbird --include "model/*" "pack/*" --local-dir "$DIR"
[ "$PRECISE" = 0 ] || hf download glyd/Qwen3.8-Flash-Next-hummingbird --include "precise/*" --local-dir "$DIR"
echo "downloaded into $DIR"
