# ==============================================================================
# VANTA TERMINAL — TARGETED LOCAL SHUTDOWN SCRIPT
# Terminates ONLY VANTA-spawned processes verified via recorded PIDs.
# Never terminates external python/node processes or touches port 8000.
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host "`n[VANTA] Initiating safe shutdown sequence..." -ForegroundColor Cyan

$ProjectRoot = "D:\vanta-terminal"
if (-not (Test-Path $ProjectRoot)) {
    $ProjectRoot = "D:\VANTA Terminal"
}

$RuntimeDir = Join-Path $ProjectRoot ".runtime"
$BackendPidFile = Join-Path $RuntimeDir "backend.pid"
$FrontendPidFile = Join-Path $RuntimeDir "frontend.pid"

function Stop-TrackedProcess([string]$pidFilePath, [string]$serviceName) {
    if (-not (Test-Path $pidFilePath)) {
        Write-Host "  -> No PID file found for $serviceName (already stopped)." -ForegroundColor DarkGray
        return
    }

    $targetPidStr = (Get-Content $pidFilePath -Raw).Trim()
    if (-not $targetPidStr) {
        Remove-Item $pidFilePath -Force -ErrorAction SilentlyContinue
        return
    }

    $targetPid = [int]$targetPidStr

    # Verify PID is NOT the protected external PID 5328 on port 8000
    if ($targetPid -eq 5328) {
        Write-Host "  -> [SECURITY ALERT] PID $targetPid matches external protected service on port 8000. SKIPPED!" -ForegroundColor Red
        return
    }

    # Inspect process existence and name
    $proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if ($proc) {
        $procName = $proc.ProcessName.ToLower()
        if ($procName -match "python|cmd|node") {
            Write-Host "  -> Stopping $serviceName (PID $targetPid, Process: $procName)..." -ForegroundColor Yellow
            
            # Stop any child processes
            Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.ParentProcessId -eq $targetPid } | ForEach-Object {
                if ($_.ProcessId -ne 5328) {
                    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                }
            }

            Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
            Write-Host "  -> $serviceName (PID $targetPid) terminated cleanly." -ForegroundColor Green
        } else {
            Write-Host "  -> [WARNING] PID $targetPid ($procName) does not match expected service type. Skipping." -ForegroundColor Red
        }
    } else {
        Write-Host "  -> $serviceName (PID $targetPid) was not running." -ForegroundColor DarkGray
    }

    Remove-Item $pidFilePath -Force -ErrorAction SilentlyContinue
}

# Stop Backend and Frontend
Stop-TrackedProcess $BackendPidFile "Backend API"
Stop-TrackedProcess $FrontendPidFile "Frontend UI"

Start-Sleep -Seconds 1

# Check lingering processes on 8101 and 3000
$bConn = Get-NetTCPConnection -LocalPort 8101 -State Listen -ErrorAction SilentlyContinue
if ($bConn) {
    $lingerPid = $bConn.OwningProcess
    if ($lingerPid -ne 5328) {
        $lProc = Get-Process -Id $lingerPid -ErrorAction SilentlyContinue
        if ($lProc -and $lProc.ProcessName.ToLower() -eq "python") {
            Write-Host "  -> Terminating lingering Uvicorn worker on port 8101 (PID $lingerPid)..." -ForegroundColor Yellow
            Stop-Process -Id $lingerPid -Force -ErrorAction SilentlyContinue
        }
    }
}

$fConn = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
if ($fConn) {
    $lingerPid = $fConn.OwningProcess
    if ($lingerPid -ne 5328) {
        $lProc = Get-Process -Id $lingerPid -ErrorAction SilentlyContinue
        if ($lProc -and $lProc.ProcessName.ToLower() -eq "node") {
            Write-Host "  -> Terminating lingering Next.js dev server on port 3000 (PID $lingerPid)..." -ForegroundColor Yellow
            Stop-Process -Id $lingerPid -Force -ErrorAction SilentlyContinue
        }
    }
}

# Verify ports are released
$backendPortCheck = Get-NetTCPConnection -LocalPort 8101 -State Listen -ErrorAction SilentlyContinue
$frontendPortCheck = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue

if ($backendPortCheck) {
    Write-Host "  -> Warning: Port 8101 still has an active listener (PID $($backendPortCheck.OwningProcess))." -ForegroundColor Yellow
} else {
    Write-Host "  -> Port 8101 confirmed freed." -ForegroundColor Green
}

if ($frontendPortCheck) {
    Write-Host "  -> Warning: Port 3000 still has an active listener (PID $($frontendPortCheck.OwningProcess))." -ForegroundColor Yellow
} else {
    Write-Host "  -> Port 3000 confirmed freed." -ForegroundColor Green
}

# Verify Port 8000 is still untouched
$port8000Check = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000Check) {
    Write-Host "  -> Port 8000: PID $($port8000Check.OwningProcess) remains active and untouched." -ForegroundColor Green
}

Write-Host "[VANTA] Shutdown complete.`n" -ForegroundColor Cyan
