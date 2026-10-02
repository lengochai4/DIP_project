param([switch]$Software, [int]$Camera = 0)
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $v2Python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $v2Python)) { throw 'Run setup_v2.ps1 first.' }
    $v2Args = @('-m', 'app.main', '--camera', "$Camera")
    if ($Software) { $v2Args += '--software' }
    & $v2Python @v2Args
    if ($LASTEXITCODE -ne 0) { throw "V2 exited with code $LASTEXITCODE" }
} finally { Pop-Location }
