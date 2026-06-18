# Build Cryptoriale Windows bundle (onedir) via PyInstaller.
# Prereq: Python on PATH, from repo root or via: powershell -File scripts\build_release.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Installing runtime + dev dependencies..."
python -m pip install -r requirements.txt -r requirements-dev.txt

Write-Host "Running PyInstaller..."
python -m PyInstaller cryptoriale.spec --noconfirm

$outDir = Join-Path $root "dist\Cryptoriale"
$exe = Join-Path $outDir "Cryptoriale.exe"
if (-not (Test-Path $exe)) {
    Write-Error "Expected output missing: $exe"
}

$playText = @"
Cryptoriale - playable build

1. Install Ollama once: https://ollama.com
2. Double-click Cryptoriale.exe in this folder

On first launch the game will:
- Start Ollama automatically if it is not already running
- Download the AI model (llama3) with progress in the console window

Keep this entire folder together (do not move only the .exe).
A console window shows startup messages; the game window opens when ready.
"@
Set-Content -Path (Join-Path $outDir "PLAY.txt") -Value $playText -Encoding UTF8

$desktop = Join-Path $env:USERPROFILE "OneDrive\Desktop\Cryptoriale"
if (-not (Test-Path (Split-Path $desktop -Parent))) {
    $desktop = Join-Path $env:USERPROFILE "Desktop\Cryptoriale"
}
if (Test-Path $desktop) {
    Remove-Item -Recurse -Force $desktop
}
Copy-Item -Path $outDir -Destination $desktop -Recurse -Force

Write-Host "OK: $exe"
Write-Host "Copied to: $desktop"
