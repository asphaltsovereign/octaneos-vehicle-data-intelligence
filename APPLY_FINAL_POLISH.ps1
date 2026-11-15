param(
    [string]$Target = "C:\Users\awamo\Downloads\OctaneOS_Sentinel_V3.4_Hackathon_Submission\octaneos-sentinel-v3"
)

$ErrorActionPreference = "Stop"
$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExpectedModelHash = "3ee122b87fa5cadfaaa8bd5d5aff44734cddc96cc81cf32e396b6c1e5f692542"

if (-not (Test-Path (Join-Path $Target "frontend\src\main.tsx"))) {
    throw "Target does not look like the OctaneOS project root: $Target"
}

Write-Host "[OctaneOS] Final hackathon polish" -ForegroundColor Cyan
Write-Host "[OctaneOS] Target: $Target" -ForegroundColor Cyan

# Stop only a VERIFIED OctaneOS process on port 8000. Never kill an unrelated service.
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
    if ($health.service -eq "octaneos-sentinel") {
        $conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) {
            Write-Host "[OctaneOS] Stopping previous OctaneOS server (PID $($conn.OwningProcess))..." -ForegroundColor Yellow
            Stop-Process -Id $conn.OwningProcess -Force
            Start-Sleep -Milliseconds 700
        }
    }
} catch {
    Write-Host "[OctaneOS] No verified OctaneOS listener needs stopping." -ForegroundColor DarkGray
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $Target "hackathon_polish_backup_$stamp"
New-Item -ItemType Directory -Path (Join-Path $backup "frontend\src") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $backup "backend\app\services") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $backup "docs") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $backup "submission") -Force | Out-Null

Copy-Item (Join-Path $Target "frontend\src\main.tsx") (Join-Path $backup "frontend\src\main.tsx")
Copy-Item (Join-Path $Target "frontend\src\styles.css") (Join-Path $backup "frontend\src\styles.css")
Copy-Item (Join-Path $Target "backend\app\services\demo.py") (Join-Path $backup "backend\app\services\demo.py")
Copy-Item (Join-Path $Target "docs\DEMO_SCRIPT.md") (Join-Path $backup "docs\DEMO_SCRIPT.md")
Copy-Item (Join-Path $Target "submission\RECORDING_CHECKLIST.md") (Join-Path $backup "submission\RECORDING_CHECKLIST.md")
Copy-Item (Join-Path $Target "submission\UNSTOP_UPLOAD_CHECKLIST.md") (Join-Path $backup "submission\UNSTOP_UPLOAD_CHECKLIST.md")
Copy-Item (Join-Path $Target "submission\PROJECT_DESCRIPTION.txt") (Join-Path $backup "submission\PROJECT_DESCRIPTION.txt")
Copy-Item (Join-Path $Target "SUBMISSION_MASTER.md") (Join-Path $backup "SUBMISSION_MASTER.md")

Copy-Item (Join-Path $PatchRoot "frontend\src\main.tsx") (Join-Path $Target "frontend\src\main.tsx") -Force
Copy-Item (Join-Path $PatchRoot "frontend\src\styles.css") (Join-Path $Target "frontend\src\styles.css") -Force
Copy-Item (Join-Path $PatchRoot "backend\app\services\demo.py") (Join-Path $Target "backend\app\services\demo.py") -Force
Copy-Item (Join-Path $PatchRoot "backend\tests\test_hackathon_presentation.py") (Join-Path $Target "backend\tests\test_hackathon_presentation.py") -Force
Copy-Item (Join-Path $PatchRoot "docs\DEMO_SCRIPT.md") (Join-Path $Target "docs\DEMO_SCRIPT.md") -Force
Copy-Item (Join-Path $PatchRoot "submission\RECORDING_CHECKLIST.md") (Join-Path $Target "submission\RECORDING_CHECKLIST.md") -Force
Copy-Item (Join-Path $PatchRoot "submission\UNSTOP_UPLOAD_CHECKLIST.md") (Join-Path $Target "submission\UNSTOP_UPLOAD_CHECKLIST.md") -Force
Copy-Item (Join-Path $PatchRoot "submission\PROJECT_DESCRIPTION.txt") (Join-Path $Target "submission\PROJECT_DESCRIPTION.txt") -Force
Copy-Item (Join-Path $PatchRoot "SUBMISSION_MASTER.md") (Join-Path $Target "SUBMISSION_MASTER.md") -Force
Write-Host "[OctaneOS] UI + demo patch copied. Backup: $backup" -ForegroundColor Green

# Recover the user's previously validated V0.5 frozen model only when its SHA-256 is exact.
$frozenTarget = Join-Path $Target "backend\artifacts\sentinel_submission_frozen"
New-Item -ItemType Directory -Path $frozenTarget -Force | Out-Null
$modelCandidates = @(
    (Join-Path $Target "backend\artifacts\sentinel_baseline_v32"),
    "$env:USERPROFILE\Documents\AsphaltSovereign\octaneos-sentinel-v3\backend\artifacts\sentinel_baseline_v32",
    "$env:USERPROFILE\Documents\AsphaltSovereign\octaneos-sentinel-v3\backend\artifacts\sentinel_baseline_v32_backup"
)
$modelRecovered = $false
foreach ($candidate in $modelCandidates) {
    $artifact = Join-Path $candidate "sentinel_baseline.joblib"
    $manifest = Join-Path $candidate "model_manifest.json"
    $report = Join-Path $candidate "final_test_report.json"
    if ((Test-Path $artifact) -and (Test-Path $manifest) -and (Test-Path $report)) {
        $actualHash = (Get-FileHash -Algorithm SHA256 $artifact).Hash.ToLowerInvariant()
        if ($actualHash -eq $ExpectedModelHash) {
            Write-Host "[OctaneOS] Verified frozen V0.5 model found. Restoring exact artifact..." -ForegroundColor Green
            Copy-Item $artifact (Join-Path $frozenTarget "sentinel_baseline.joblib") -Force
            Copy-Item $manifest (Join-Path $frozenTarget "model_manifest.json") -Force
            Copy-Item $report (Join-Path $frozenTarget "final_test_report.json") -Force
            $modelRecovered = $true
            break
        } else {
            Write-Host "[OctaneOS] Ignoring model candidate with wrong SHA-256: $candidate" -ForegroundColor Yellow
        }
    }
}
if (-not $modelRecovered) {
    Write-Host "[OctaneOS] Exact V0.5 frozen artifact was not found in the known prior-work folders." -ForegroundColor Yellow
    Write-Host "[OctaneOS] The polished UI will truthfully show LOCAL FALLBACK. No model is fabricated or substituted." -ForegroundColor Yellow
}

Push-Location (Join-Path $Target "frontend")
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "[OctaneOS] node_modules missing; installing frontend dependencies..." -ForegroundColor Yellow
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
    }
    Write-Host "[OctaneOS] Building polished frontend..." -ForegroundColor Cyan
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally {
    Pop-Location
}

$python = Join-Path $Target "backend\.venv\Scripts\python.exe"
if (Test-Path $python) {
    Push-Location (Join-Path $Target "backend")
    try {
        Write-Host "[OctaneOS] Running presentation regression tests..." -ForegroundColor Cyan
        & $python -m pytest -q tests\test_hackathon_presentation.py
        if ($LASTEXITCODE -ne 0) { throw "presentation regression tests failed" }
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[OctaneOS] Existing backend virtualenv not found; launcher will create it." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Green
Write-Host " FINAL POLISH APPLIED + FRONTEND BUILT" -ForegroundColor Green
if ($modelRecovered) {
    Write-Host " FROZEN MODEL: RESTORED + SHA-256 VERIFIED" -ForegroundColor Green
} else {
    Write-Host " FROZEN MODEL: NOT FOUND - TRUTHFUL LOCAL FALLBACK ACTIVE" -ForegroundColor Yellow
}
Write-Host "==============================================================" -ForegroundColor Green
Write-Host "Now run:" -ForegroundColor Cyan
Write-Host "cd `"$Target`""
Write-Host ".\START_OCTANEOS_WINDOWS.bat"
