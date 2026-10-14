#!/usr/bin/env bash
# Install the Glyd engine (compiled, from this repository's GitHub release) under $GLYD_QWEN (default ~/.glyd-qwen-3.8-flash).
# Linux x86-64, an NVIDIA GPU (Ampere or newer) with driver 580+. No sudo, nothing else to install.
#   tools/install.sh [VERSION]        (default: the latest release)
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
H=${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}; mkdir -p "$H/bin" "$H/lib"
REPO=surya-koritala/glyd-qwen-3.8-flash; VER=${1:-latest}
if [ "$VER" = latest ]; then BASE=https://github.com/$REPO/releases/latest/download; else BASE=https://github.com/$REPO/releases/download/$VER; fi
BASE=${GLYD_RELEASE_URL:-$BASE}   # (a mirror, or file:///dir for a test before a release)
command -v nvidia-smi > /dev/null || { echo "no nvidia-smi: an NVIDIA driver is needed" >&2; exit 1; }
cd "$H"
for f in glyd-engine libglyd_gpu_cuda13.so SHA256SUMS; do curl -fsSL --retry 3 -o "$f.new" "$BASE/$f" && mv "$f.new" "$f"; done
sha256sum -c --quiet SHA256SUMS
mv glyd-engine bin/ && chmod +x bin/glyd-engine && mv libglyd_gpu_cuda13.so lib/
cat > "$H/env.sh" <<ENV
export GLYD_QWEN=$H GLYD_REPO=$HERE GLYD_ENGINE=$H/bin/glyd-engine GLYD_GPU_LIB=$H/lib/libglyd_gpu_cuda13.so
ENV
"$H/bin/glyd-engine" --version
echo "installed. Next: tools/download.sh, then tools/serve.sh"
