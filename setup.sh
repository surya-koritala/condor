#!/usr/bin/env bash
# Qwen3.8-Flash-Next on Glyd in one command: checks this computer, installs the engine, downloads the model, asks two questions, then starts the
# chat page and the API. Run it again to start it next time (nothing is downloaded twice).   ./setup.sh   (or ./setup.sh --yes for the defaults)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
H=${GLYD_QWEN:-$HOME/.glyd-qwen-3.8-flash}; YES=0; [ "${1:-}" = --yes ] && YES=1
say() { printf '\033[1m%s\033[0m\n' "$*"; }
ask() { local q=$1 d=$2 a; if [ "$YES" = 1 ]; then echo "$d"; return; fi; read -r -p "$q [$d]: " a < /dev/tty; echo "${a:-$d}"; }

say "Qwen3.8-Flash-Next (Glyd Hummingbird level) on your GPU"
command -v nvidia-smi > /dev/null || { echo "No NVIDIA driver found (nvidia-smi). Install the NVIDIA driver 580 or newer, then run this again."; exit 1; }
read -r GPU VRAM DRV < <(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits | head -1 | awk -F', ' '{gsub(/ /,"_",$1); print $1, $2, $3}')
RAM=$(free -g | awk '/^Mem:/ {print $2}'); DISK=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9)
echo "  GPU ${GPU//_/ }, $(((VRAM + 512) / 1024)) GB, driver $DRV;  RAM $RAM GiB;  free disk $DISK GB"
[ "$VRAM" -ge 15000 ] || echo "  Note: the GPU has less than 16 GB; this is tested on 16 GB and up."
[ "$RAM" -ge 60 ] || echo "  Note: less than 64 GB of RAM; expect slower answers while the model's files come from the disk."
[ "${DRV%%.*}" -ge 580 ] || { echo "  The driver is older than 580: update it, then run this again."; exit 1; }

[ -x "$H/bin/glyd-engine" ] || { say "Installing the engine (about 50 MB)"; bash "$HERE/tools/install.sh"; }
. "$H/env.sh"
MODE=$(ask "Mode: fast (quickest) or precise (adds the precision pack: closer to the original model, about 41 GB more to download)" fast)
if [ ! -f "$H/hf/model/config.json" ] || { [ "$MODE" = precise ] && [ ! -f "$H/hf/precise/meta.json" ]; }; then
  [ "$DISK" -ge 75 ] || { echo "About 75 GB of free disk is needed (110 GB for precise mode)."; exit 1; }
  say "Downloading the model (about 68 GB$([ "$MODE" = precise ] && echo ' + 41 GB'); it resumes if it stops)"
  bash "$HERE/tools/download.sh" $([ "$MODE" = precise ] && echo --precise)
fi
CTX=$(ask "Context (tokens the model keeps in mind): 32768 is fastest; 65536, 131072 or 262144 hold more, with less room for the model on the GPU" 32768)
say "Starting: chat at http://127.0.0.1:8080/  ·  API at http://127.0.0.1:8080/v1 (OpenAI and Anthropic)  ·  Ctrl+C to stop"
DIR=$H/hf; PACK=$DIR/pack; [ "$MODE" = precise ] && PACK=$DIR/precise
( sleep 60; command -v xdg-open > /dev/null && xdg-open http://127.0.0.1:8080/ > /dev/null 2>&1 || true ) &
exec python "$HERE/tools/server.py" --model "$DIR/model" --pack "$PACK" $([ "$MODE" = precise ] && echo --precise) \
  --engine "$GLYD_ENGINE" --engine-args "--ctx $CTX" --port 8080
