#!/usr/bin/env bash
# Install the Glyd engine (compiled, from this repository's GitHub release) and a small Python venv for the server shim, under
# $GLYD_QWEN (default ~/.glyd-qwen-3.8-flash). Linux x86-64, an NVIDIA GPU (Ampere or newer) with driver 580+. No sudo.
#   tools/install.sh [VERSION]        (default: the latest release)
set -euo pipefail
H=${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}; mkdir -p "$H/bin" "$H/lib"
REPO=surya-koritala/glyd-qwen-3.8-flash; VER=${1:-latest}
if [ "$VER" = latest ]; then BASE=https://github.com/$REPO/releases/latest/download; else BASE=https://github.com/$REPO/releases/download/$VER; fi
BASE=${GLYD_RELEASE_URL:-$BASE}   # (a mirror, or file:///dir for a test before a release)
command -v nvidia-smi > /dev/null || { echo "no nvidia-smi: an NVIDIA driver is needed" >&2; exit 1; }
cd "$H"
for f in glyd-engine libglyd_gpu_cuda13.so SHA256SUMS; do curl -fsSL --retry 3 -o "$f.new" "$BASE/$f" && mv "$f.new" "$f"; done
sha256sum -c SHA256SUMS
mv glyd-engine bin/ && chmod +x bin/glyd-engine && mv libglyd_gpu_cuda13.so lib/
[ -x "$H/venv/bin/python" ] || python3 -m venv "$H/venv" || { rm -rf "$H/venv"; echo "Python could not make a venv: on Ubuntu or Debian run  sudo apt install python3-venv  and then this again." >&2; exit 1; }
"$H/venv/bin/pip" install -q "transformers==5.19.0" "huggingface_hub>=1.5,<2" hf_xet jinja2
cat > "$H/env.sh" <<EOF
export GLYD_QWEN=$H GLYD_ENGINE=$H/bin/glyd-engine GLYD_GPU_LIB=$H/lib/libglyd_gpu_cuda13.so PATH=$H/venv/bin:\$PATH
EOF
"$H/bin/glyd-engine" --version
echo "installed. Next: . $H/env.sh; tools/download.sh; tools/serve.sh"
