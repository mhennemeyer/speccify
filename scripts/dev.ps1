# dev.ps1 - Speccify-Desktop-App auf Windows bauen und starten.
#
# Windows-Gegenstueck zu scripts/dev.sh (Plan projektfenster.md, P2/P6):
# prueft die Toolchain, baut die MCP-Sidecars mit Triple-Suffix, fuellt
# resources/ und startet `tauri dev`. Idempotent - einfach erneut ausfuehren.
#
# Voraussetzungen (einmalig, jeweils mit winget):
#   winget install Rustlang.Rustup            # dann: rustup default stable
#   winget install OpenJS.NodeJS.LTS          # Node 22+
#   winget install LLVM.LLVM                  # clang - Pflicht fuer `ring`
#   winget install astral-sh.uv               # uv (Sidecar + Python-Teil)
#   corepack enable && corepack prepare pnpm@10 --activate
#   VS Build Tools MIT der C++-Workload (die nackte Installation reicht
#   nicht - ohne Workload fehlt link.exe):
#   winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Step($name) { Write-Host "==> $name" -ForegroundColor Cyan }
function Need($cmd, $hint) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "FEHLT: $cmd - $hint" -ForegroundColor Red
        exit 1
    }
}

Step "Toolchain pruefen"
Need cargo  "rustup installieren: winget install Rustlang.Rustup"
Need node   "Node installieren: winget install OpenJS.NodeJS.LTS"
Need pnpm   "corepack enable && corepack prepare pnpm@10 --activate"
Need uv     "uv installieren: winget install astral-sh.uv"

# clang: `ring` baut auf ARM64/MSVC nur mit LLVM. Vorne in den PATH,
# damit auch eine frische Installation ohne Neustart gefunden wird.
$llvm = "C:\Program Files\LLVM\bin"
if (Test-Path "$llvm\clang.exe") { $env:PATH = "$llvm;$env:PATH" }
Need clang  "LLVM installieren: winget install LLVM.LLVM"

# MSVC-Linker: rustc findet link.exe ueber vswhere - aber nur, wenn die
# C++-Workload wirklich installiert ist (die nackten Build Tools ohne
# Workload sind die haeufigste Falle: `error: linker link.exe not found`).
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vcInstall = $null
if (Test-Path $vswhere) {
    $vcInstall = & $vswhere -products * -requiresAny `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 `
        -latest -property installationPath
}
if (-not $vcInstall) {
    Write-Host "FEHLT: MSVC-Linker (link.exe) - VS Build Tools ohne C++-Workload." -ForegroundColor Red
    Write-Host 'Fix:  winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"' -ForegroundColor Yellow
    Write-Host "Danach ein NEUES Terminal oeffnen und dev.ps1 erneut ausfuehren." -ForegroundColor Yellow
    exit 1
}

Step "pnpm install (Workspace)"
pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Step "MCP-Sidecars bauen"
cargo build -p speccify-exec-mcp -p speccify-discovery-mcp -p speccify-parallels-mcp
if ($LASTEXITCODE -ne 0) { exit 1 }

$triple = (rustc -vV | Select-String '^host: (.+)$').Matches.Groups[1].Value
$bin = Join-Path $repo "apps\desktop\src-tauri\binaries"
New-Item -ItemType Directory -Force $bin | Out-Null
foreach ($name in "speccify-exec-mcp", "speccify-discovery-mcp", "speccify-parallels-mcp") {
    Copy-Item (Join-Path $repo "target\debug\$name.exe") (Join-Path $bin "$name-$triple.exe") -Force
    Write-Host "  $name-$triple.exe"
}
Copy-Item (Get-Command uv).Source (Join-Path $bin "speccify-uv-$triple.exe") -Force
Write-Host "  speccify-uv-$triple.exe"

Step "resources fuellen (Referenz-Skills; Engine-Payload ist Release-Sache)"
$res = Join-Path $repo "apps\desktop\src-tauri\resources"
New-Item -ItemType Directory -Force $res | Out-Null
if (Test-Path (Join-Path $res "skills")) { Remove-Item -Recurse -Force (Join-Path $res "skills") }
Copy-Item -Recurse (Join-Path $repo "skills") (Join-Path $res "skills")

Step "tauri dev starten (erster Rust-Build dauert einige Minuten)"
Set-Location (Join-Path $repo "apps\desktop")
pnpm tauri dev
