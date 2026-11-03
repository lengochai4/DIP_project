param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -e '.[dev,product]'
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Write-Host 'Setup complete. Model instructions: models/README.md. Launch: .\launch_v2.ps1'
} finally { Pop-Location }
