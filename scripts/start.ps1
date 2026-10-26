# ==============================================================================
# VANTA TERMINAL — SAFE LOCAL LAUNCH SCRIPT
# Starts Backend (FastAPI) and Frontend (Next.js) on local loopback via Win32 API.
# Strictly preserves Port 8000 and all existing system processes.
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "`n[VANTA] Initializing VANTA Research Terminal..." -ForegroundColor Cyan

# 1. Project Root Verification
$ProjectRoot = "D:\vanta-terminal"
if (-not (Test-Path $ProjectRoot)) {
    $ProjectRoot = "D:\VANTA Terminal"
}
Set-Location $ProjectRoot

# 2. Runtime Directory
$RuntimeDir = Join-Path $ProjectRoot ".runtime"
if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
}

$BackendPidFile = Join-Path $RuntimeDir "backend.pid"
$FrontendPidFile = Join-Path $RuntimeDir "frontend.pid"

# Check if already running
if (Test-Path $BackendPidFile) {
    $existingPid = (Get-Content $BackendPidFile -Raw).Trim()
    $existingProc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($existingProc) {
        Write-Host "[VANTA] Backend is already running (PID $existingPid)." -ForegroundColor Yellow
        Write-Host "[VANTA] Use 'scripts/stop.ps1' to stop it first if you want to restart." -ForegroundColor Yellow
        exit 0
    }
}

# 3. Port Allocation Check
$BackendPort = 8101
$FrontendPort = 3000

# Verify Port 8000 is untouched
$Port8000Occupied = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($Port8000Occupied) {
    Write-Host "[VANTA] Verified Port 8000 is occupied by PID $($Port8000Occupied.OwningProcess). Strictly locked out." -ForegroundColor Yellow
}

# Check Backend Port 8101
$Port8101Occupied = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue
if ($Port8101Occupied) {
    Write-Host "[VANTA] Port $BackendPort is already active (PID $($Port8101Occupied.OwningProcess))." -ForegroundColor Green
} else {
    Write-Host "[VANTA] Starting Backend on 127.0.0.1:$BackendPort..." -ForegroundColor Cyan
    $pythonPath = (Get-Command python).Source
    $bRes = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = "`"$pythonPath`" -m uvicorn backend.main:app --host 127.0.0.1 --port $BackendPort"
        CurrentDirectory = $ProjectRoot
    }
    if ($bRes.ReturnValue -eq 0) {
        $bRes.ProcessId | Out-File -FilePath $BackendPidFile -Encoding ascii
        Write-Host "  -> Backend spawned with PID $($bRes.ProcessId)" -ForegroundColor Green
    } else {
        Write-Host "  -> Failed to spawn Backend (Code $($bRes.ReturnValue))" -ForegroundColor Red
    }
}

# Check Frontend Port 3000
$Port3000Occupied = Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue
if ($Port3000Occupied) {
    Write-Host "[VANTA] Port $FrontendPort is already active (PID $($Port3000Occupied.OwningProcess))." -ForegroundColor Green
} else {
    Write-Host "[VANTA] Starting Frontend on 127.0.0.1:$FrontendPort..." -ForegroundColor Cyan
    $cmdPath = "C:\Windows\System32\cmd.exe"
    $frontendDir = Join-Path $ProjectRoot "frontend"
    $fRes = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = "`"$cmdPath`" /c npm run dev -- -p $FrontendPort -H 127.0.0.1"
        CurrentDirectory = $frontendDir
    }
    if ($fRes.ReturnValue -eq 0) {
        $fRes.ProcessId | Out-File -FilePath $FrontendPidFile -Encoding ascii
        Write-Host "  -> Frontend spawned with PID $($fRes.ProcessId)" -ForegroundColor Green
    } else {
        Write-Host "  -> Failed to spawn Frontend (Code $($fRes.ReturnValue))" -ForegroundColor Red
    }
}

# 4. Display Operational Summary
Start-Sleep -Seconds 2

Write-Host "`n========================================================" -ForegroundColor Green
Write-Host "  VANTA TERMINAL READY // LOCAL RESEARCH WORKSTATION" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Dashboard:     http://127.0.0.1:$FrontendPort" -ForegroundColor White
Write-Host "  API Docs:      http://127.0.0.1:$BackendPort/docs" -ForegroundColor White
Write-Host "  API Health:    http://127.0.0.1:$BackendPort/api/health" -ForegroundColor White
Write-Host "  Shutdown:      powershell -File scripts/stop.ps1" -ForegroundColor Yellow
Write-Host "  Status Notice: LOCAL RESEARCH - NO LIVE ORDERS" -ForegroundColor Yellow
Write-Host "========================================================`n" -ForegroundColor Green
