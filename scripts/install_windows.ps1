# AGILANG CLI installer for Windows.
# Run from PowerShell inside the docs folder:
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   .\scripts\install_windows.ps1
#
# Or from this app's project root:
#   .\installer.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageRoot = Resolve-Path (Join-Path $ScriptDir "..")
$InstallPy = Join-Path $PackageRoot "install.py"

Write-Host "Installing AGILANG CLI from $PackageRoot" -ForegroundColor Cyan

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $Python) {
    throw "Python 3.10+ was not found. Install Python and make sure python or py is on PATH."
}

if ($Python.Name -eq "py.exe" -or $Python.Name -eq "py") {
    & $Python.Source -3 $InstallPy
} else {
    & $Python.Source $InstallPy
}

Write-Host "AGILANG CLI installer finished." -ForegroundColor Green
