# The chat page and the API (OpenAI and Anthropic) on http://127.0.0.1:PORT (default 8080).
#   powershell -ExecutionPolicy Bypass -File tools\serve.ps1 [-Fast | -Best] [PORT]   precise mode by default; -Fast or -Best uses those experts (tools\download.ps1 -Fast or -Best)
#   $env:GLYD_CTX = 65536; tools\serve.ps1                                        the context in tokens (default 32768, up to 262144)
param([switch]$Fast, [switch]$Best, [int]$Port = 8080)
$ErrorActionPreference = 'Stop'
. (Join-Path $(if ($env:GLYD_QWEN) { $env:GLYD_QWEN } else { Join-Path $HOME '.glyd-qwen-3.8-flash' }) 'env.ps1')
$dir = if ($env:GLYD_HF) { $env:GLYD_HF } else { Join-Path $env:GLYD_QWEN 'hf' }
# (precise and best keep the always-on matrices at six bits: their calibrated experts were packed for that)
if ($Fast) { $pack = Join-Path $dir 'fast'; $mode = @(); $f = ' -Fast' }
elseif ($Best) { $pack = Join-Path $dir 'best'; $mode = @('--no-side', '--layout', 'i6', '--hi', 'i6'); $f = ' -Best' }
else { $pack = Join-Path $dir 'precise'; $mode = @('--precise', '--layout', 'i6', '--hi', 'i6'); $f = '' }
if (-not (Test-Path $pack)) { throw "$pack is missing: run tools\download.ps1$f first." }
$ctx = if ($env:GLYD_CTX) { $env:GLYD_CTX } else { '32768' }
& $env:GLYD_ENGINE qwenserve (Join-Path $dir 'model') $pack @mode --ctx $ctx --port $Port --page $PSScriptRoot
exit $LASTEXITCODE
