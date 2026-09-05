[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$PythonExecutable = Join-Path $VirtualEnvironment "Scripts\python.exe"

function Require-Command {
    param([Parameter(Mandatory)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

Require-Command python
Require-Command ffmpeg

if (-not (Test-Path -LiteralPath $PythonExecutable)) {
    python -m venv $VirtualEnvironment
}

if (-not $SkipInstall) {
    & $PythonExecutable -m pip install --upgrade pip
    & $PythonExecutable -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
}

New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "workspace") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot "output") | Out-Null
& $PythonExecutable (Join-Path $ProjectRoot "scripts\verify_environment.py")

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Warning "GitHub CLI (gh) is not installed; install and authenticate it before repository creation."
}
Write-Host "Google Drive delivery requires the connected Codex Google Drive plugin; credentials are not stored locally."
