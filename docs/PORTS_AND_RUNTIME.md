# VANTA Terminal — Ports and Runtime Specification
**Document ID:** DOC-RUNTIME-001  
**Status:** Approved for Phase 0  
**Host Machine:** Windows 10/11 x64 · Intel Core i7-7700HQ (4C/8T) · 16 GB RAM · GTX 1050 Ti (4 GB)

---

## 1. Port Allocation Matrix

| Service | Target Port | Status (Audit) | Fallback Range | Host Binding |
| :--- | :--- | :--- | :--- | :--- |
| **Backend API (FastAPI / Uvicorn)** | `8101` | **FREE** | `8102 - 8199` | `127.0.0.1` |
| **Frontend Web (Next.js)** | `3000` | **FREE** | `3001 - 3099` | `127.0.0.1` |
| **External/Other Existing Services** | `8000` | **OCCUPIED (PID 5328)** | **FORBIDDEN** | N/A |

### Strict Conflict Isolation Rules:
1. **Port 8000 is FORBIDDEN**: An active Python process (PID 5328, running an existing project) is bound to `127.0.0.1:8000`. VANTA Terminal must **never** bind, intercept, kill, or signal this process.
2. **Local Loopback Only**: All services bind exclusively to `127.0.0.1`. Binding to `0.0.0.0` or exposing ports to local network interfaces is strictly disallowed.
3. **Dynamic Conflict Resolution**: The startup script checks `8101` and `3000` before launch. If either is bound by a foreign process, the script increments within the respective range, updates the runtime configuration, and logs the assignment without terminating external processes.

---

## 2. Hardware Resource Audit & Allocation Limits

### Current Host Resources (Audited 2026-10-27)
- **Drive C: (NVMe SSD)**: Total ~237.7 GB | Free: **20.68 GB** (Operating System, tools)
- **Drive D: (Data HDD)**: Total ~931.5 GB | Free: **64.93 GB** (Project root & datasets)
- **Physical RAM**: Total 15.89 GB | Free: **3.50 GB**
- **CPU**: Intel Core i7-7700HQ (4 Cores, 8 Logical Processors)
- **GPU**: NVIDIA GeForce GTX 1050 Ti (4.0 GB VRAM)

### Resource Budgeting Limits for VANTA Terminal
Because free physical RAM is approximately **3.50 GB**, uncontrolled parallel processing or massive in-memory DataFrame operations will cause severe Windows pagefile thrashing.

| Subsystem | Memory Cap | Concurrency Limit | I/O Strategy |
| :--- | :--- | :--- | :--- |
| **Backend API** | 250 MB | Single Uvicorn process | Non-blocking async endpoints |
| **Frontend UI (Dev / Build)**| 500 MB | Next.js Node runtime | Subsampled chart points |
| **Data Ingestion** | 500 MB | 1 symbol at a time | Streamed to disk via Parquet chunks |
| **Feature Engineering** | 800 MB | Polars lazy execution | Per-pair streaming batch |
| **Backtest Engine** | 400 MB | Single worker loop | Vectorized NumPy/Polars event records |
| **Model Training** | 1,500 MB | `n_jobs=2`, single pair | Max depth 6, early stopping, explicit GC |
| **Total Headroom Budget** | **~3.45 GB** | **1 Heavy Worker Max** | **Zero swap thrashing guarantee** |

---

## 3. Process Lifecycle & Management

### PID Tracking Architecture
To prevent rogue processes or accidental termination of user applications, VANTA Terminal maintains process ID tracking inside a non-versioned runtime state directory:

```
D:\vanta-terminal\
├── .runtime\
│   ├── backend.pid    # Process ID of Uvicorn backend
│   └── frontend.pid   # Process ID of Next.js frontend
```

### Startup Protocol (`scripts/start.ps1`)
1. Read `.env` (falls back to `.env.example`).
2. Verify port `8101` and `3000` via `Get-NetTCPConnection`.
3. If free:
   - Launch Backend: `uvicorn backend.main:app --host 127.0.0.1 --port 8101` in background.
   - Save PID to `.runtime/backend.pid`.
   - Launch Frontend: `npm run dev -- -p 3000 -H 127.0.0.1` in background.
   - Save PID to `.runtime/frontend.pid`.
4. Output terminal URLs:
   - Web Dashboard: `http://127.0.0.1:3000`
   - API Docs: `http://127.0.0.1:8101/docs`
   - Health Check: `http://127.0.0.1:8101/health`

### Shutdown Protocol (`scripts/stop.ps1`)
1. Read `.runtime/backend.pid` and `.runtime/frontend.pid`.
2. Inspect the process name and command line of each recorded PID to confirm it matches the Python/Node process started by VANTA.
3. Terminate only the verified PIDs using `Stop-Process -Id $PID -ErrorAction SilentlyContinue`.
4. Remove `.runtime/*.pid`.
5. Verify that ports `8101` and `3000` are freed.
6. **NEVER execute `taskkill /F /IM python.exe` or `taskkill /F /IM node.exe`**, preserving all external user processes and services on port 8000.
