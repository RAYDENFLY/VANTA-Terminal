# ==============================================================================
# VANTA TERMINAL — HEALTH & DIAGNOSTIC VERIFICATION SCRIPT
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "`n=== VANTA TERMINAL HEALTH CHECK ===" -ForegroundColor Cyan

# 1. Verify Project Directory
$ProjectRoot = "D:\vanta-terminal"
if (-not (Test-Path $ProjectRoot)) {
    $ProjectRoot = "D:\VANTA Terminal"
}
Write-Host "[1/4] Project Root: $ProjectRoot" -ForegroundColor Gray

# 2. Check Port Bindings
Write-Host "[2/4] Checking Network Ports..." -ForegroundColor Gray
$Port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($Port8000) {
    Write-Host "  -> Port 8000: OCCUPIED by PID $($Port8000.OwningProcess) [LOCKED OUT / UNTOUCHED]" -ForegroundColor Yellow
} else {
    Write-Host "  -> Port 8000: Free" -ForegroundColor Gray
}

$Port8101 = Get-NetTCPConnection -LocalPort 8101 -State Listen -ErrorAction SilentlyContinue
if ($Port8101) {
    Write-Host "  -> Backend Port 8101: LISTENING (PID $($Port8101.OwningProcess))" -ForegroundColor Green
} else {
    Write-Host "  -> Backend Port 8101: Inactive" -ForegroundColor DarkGray
}

$Port3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($Port3000) {
    Write-Host "  -> Frontend Port 3000: LISTENING (PID $($Port3000.OwningProcess))" -ForegroundColor Green
} else {
    Write-Host "  -> Frontend Port 3000: Inactive" -ForegroundColor DarkGray
}

# 3. Check Backend API Endpoint
Write-Host "[3/4] Querying Backend Health Endpoint..." -ForegroundColor Gray
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8101/api/health" -Method Get -TimeoutSec 3
    Write-Host "  -> Backend Status: $($response.status)" -ForegroundColor Green
    Write-Host "  -> Terminal Mode:  LOCAL RESEARCH - NO LIVE ORDERS" -ForegroundColor Green
    Write-Host "  -> Demo Active:    $($response.is_demo_data)" -ForegroundColor Gray
} catch {
    Write-Host "  -> Backend endpoint not responding (API may be stopped)" -ForegroundColor DarkGray
}

# 4. Check Tracked PIDs
Write-Host "[4/4] Process Ownership & Runtime Locks..." -ForegroundColor Gray
$BackendPidFile = Join-Path $ProjectRoot ".runtime\backend.pid"
$FrontendPidFile = Join-Path $ProjectRoot ".runtime\frontend.pid"

if (Test-Path $BackendPidFile) {
    $bPid = Get-Content $BackendPidFile -Raw
    Write-Host "  -> Tracked Backend PID: $bPid" -ForegroundColor Gray
} else {
    Write-Host "  -> No active backend PID file" -ForegroundColor DarkGray
}

if (Test-Path $FrontendPidFile) {
    $fPid = Get-Content $FrontendPidFile -Raw
    Write-Host "  -> Tracked Frontend PID: $fPid" -ForegroundColor Gray
} else {
    Write-Host "  -> No active frontend PID file" -ForegroundColor DarkGray
}

Write-Host "===================================`n" -ForegroundColor Cyan
