# Build Cryptoriale Windows bundle (onedir) via PyInstaller.
# Prereq: Python on PATH, from repo root or via: powershell -File scripts\build_release.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Installing runtime + dev dependencies..."
python -m pip install -r requirements.txt -r requirements-dev.txt

Write-Host "Running PyInstaller..."
python -m PyInstaller cryptoriale.spec --noconfirm

$exe = Join-Path $root "dist\Cryptoriale\Cryptoriale.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Expected output missing: $exe"
}
Write-Host "OK: $exe"
