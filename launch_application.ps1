# Run from any working directory. Installation/model setup remains explicit.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ApplicationArguments)
$ErrorActionPreference = 'Stop'
$ApplicationPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $ApplicationPython)) {
    $ApplicationPython = (Get-Command python -ErrorAction Stop).Source
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $ApplicationPython -m extensions.stem3d.app @ApplicationArguments
    $ApplicationExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $ApplicationExitCode
