# build.ps1 — ExpVault Windows installer build
# Usage: .\build.ps1
# Requirements: Python 3.8+, Node.js 18+, npm

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host ""
Write-Host "=== ExpVault Build Script ===" -ForegroundColor Cyan

# -- 1. Python dependencies --------------------------------------------------
Write-Host ""
Write-Host "[1/5] Installing Python dependencies..." -ForegroundColor Yellow

pip install --quiet -r "$root\requirements.txt"
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }

# -- 2. PyInstaller: build bridge.exe ----------------------------------------
Write-Host ""
Write-Host "[2/5] Building bridge.exe with PyInstaller..." -ForegroundColor Yellow

Set-Location "$root\backend"

if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist")  { Remove-Item -Recurse -Force "dist" }

python -m PyInstaller bridge.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller failed"; exit 1 }

Set-Location $root

# -- 3. Smoke-test bridge.exe -------------------------------------------------
# Πιάνει packaging-only σφάλματα (λάθος PyInstaller excludes, NameError σε
# export path) που δεν φαίνονται σε dev mode ούτε σε static analysis — βλ.
# scripts/smoke-test-bridge.mjs.
Write-Host ""
Write-Host "[3/5] Smoke-testing bridge.exe..." -ForegroundColor Yellow
node scripts\smoke-test-bridge.mjs "$root\backend\dist\bridge\bridge.exe"
if ($LASTEXITCODE -ne 0) { Write-Error "smoke-test-bridge failed — bridge.exe δεν είναι έτοιμο για installer"; exit 1 }

# Copy output to dist/bridge at project root (expected by package.json extraResources)
$bridgeDest = "$root\dist\bridge"
if (Test-Path $bridgeDest) { Remove-Item -Recurse -Force $bridgeDest }
New-Item -ItemType Directory -Force $bridgeDest | Out-Null
Copy-Item -Recurse -Force "$root\backend\dist\bridge\*" $bridgeDest
Write-Host "  bridge.exe -> dist/bridge/" -ForegroundColor Green

# -- 4. npm install ----------------------------------------------------------
Write-Host ""
Write-Host "[4/5] Installing npm dependencies..." -ForegroundColor Yellow
npm install --silent
if ($LASTEXITCODE -ne 0) { Write-Error "npm install failed"; exit 1 }

# -- 5. Electron Builder: NSIS installer -------------------------------------
Write-Host ""
Write-Host "[5/5] Building Windows installer..." -ForegroundColor Yellow
if (-not (Test-Path "$root\github-token.json")) {
    Write-Warning "github-token.json δεν βρέθηκε — η αναφορά προβλήματος έκδοσης (report-version-issue) θα είναι απενεργοποιημένη σε αυτό το build."
}
npm run dist:win
if ($LASTEXITCODE -ne 0) { Write-Error "electron-builder failed"; exit 1 }

# -- Result ------------------------------------------------------------------
Write-Host ""
Write-Host "=== Build complete! ===" -ForegroundColor Green
$installer = Get-ChildItem "$root\dist" -Filter "*.exe" |
    Where-Object { $_.Name -notlike "bridge*" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($installer) {
    $sizeMB = [math]::Round($installer.Length / 1MB, 1)
    Write-Host "Installer: $($installer.FullName)" -ForegroundColor Cyan
    Write-Host "Size:      $sizeMB MB" -ForegroundColor Cyan
} else {
    $distPath = "$root\dist"
    Write-Host "Check folder: $distPath" -ForegroundColor Cyan
}
