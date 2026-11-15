$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Artifact = Join-Path $Backend "artifacts\sentinel_submission_frozen\sentinel_baseline.joblib"
$Expected = "3ee122b87fa5cadfaaa8bd5d5aff44734cddc96cc81cf32e396b6c1e5f692542"

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $Backend ".venv")
}

& $Python -m pip install -r (Join-Path $Backend "requirements.txt")
Push-Location $Backend
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
} finally {
    Pop-Location
}

Push-Location $Frontend
try {
    if (-not (Test-Path "node_modules")) { npm ci }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
} finally {
    Pop-Location
}

if (-not (Test-Path $Artifact)) {
    throw "Frozen submission artifact is missing: $Artifact"
}
$Actual = (Get-FileHash -Algorithm SHA256 $Artifact).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
    throw "Frozen model SHA-256 mismatch. Expected $Expected but found $Actual"
}

Write-Host "SUBMISSION GATE PASSED" -ForegroundColor Green
Write-Host "Backend tests: passed"
Write-Host "Frontend build: passed"
Write-Host "Frozen model checksum: $Actual"
