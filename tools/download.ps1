# The model from Hugging Face (no account needed), glyd/Qwen3.8-Flash-Next-hummingbird: model\ (Qwen's tokenizer and configs, and the weights
# outside the experts, 37 GB) and the experts for one mode: precise\ (45 GB, the default) or, with -Fast, pack\ (31 GB). The files go to the
# Hugging Face cache (~\.cache\huggingface, or $env:HF_HUB_CACHE), which other tools share; DIR gets folder links to them. It resumes if it stops.
#   powershell -ExecutionPolicy Bypass -File tools\download.ps1 [-Fast] [DIR]        (default DIR $env:GLYD_QWEN\hf)
param([switch]$Fast, [string]$Dir = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $(if ($env:GLYD_QWEN) { $env:GLYD_QWEN } else { Join-Path $HOME '.glyd-qwen-3.8-flash' }) 'env.ps1')
if (-not $Dir) { $Dir = Join-Path $env:GLYD_QWEN 'hf' }
# Hugging Face counts downloads by requests for the top-level config.json, so ask for it once (a HEAD request, nothing else).
curl.exe -sfI -o NUL https://huggingface.co/glyd/Qwen3.8-Flash-Next-hummingbird/resolve/main/config.json
$mode = if ($Fast) { @() } else { @('--precise') }
& $env:GLYD_ENGINE qwenget glyd/Qwen3.8-Flash-Next-hummingbird $Dir @mode
exit $LASTEXITCODE
