$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$uiPython = Join-Path $PSScriptRoot '.venv-research\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $uiPython)) {
    $uiPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $uiPython)) {
    throw 'Chưa có môi trường Python. Xem submission/stem_ui/README.md.'
}
& $uiPython -X utf8 -m submission.stem_ui.app
if ($LASTEXITCODE -ne 0) { throw 'UI dừng do lỗi. Kiểm tra thông báo phía trên.' }
