# VANTA Terminal

**Independent Quantitative ML Research & Backtesting Platform**  
*Bloomberg-inspired professional quantitative workstation for crypto-futures strategy research and ML validation.*

> **SAFETY NOTICE: STRICT AIR-GAPPED SIMULATION**  
> `LOCAL RESEARCH · NO LIVE ORDERS`  
> This software is strictly for historical simulation, statistical validation, and machine learning research. It contains **no live trading execution capability**, order routing engines, or exchange trade execution permissions.

---

## 1. System Specifications & Allocation

- **Host Environment**: Windows 10/11 x64 (Intel Core i7-7700HQ, 4C/8T)
- **Available RAM Target**: 16 GB Physical (~3.5 GB free headroom)
- **GPU Acceleration**: NVIDIA GeForce GTX 1050 Ti (4 GB VRAM)
- **Primary Storage**: `D:\vanta-terminal\` (HDD storage for Parquet datasets and SQLite registry)

### Port Allocation:
- **Frontend Dashboard**: `http://127.0.0.1:3000` (Next.js)
- **Backend Research API**: `http://127.0.0.1:8101` (FastAPI / Uvicorn)
- **Interactive Documentation**: `http://127.0.0.1:8101/docs`
- **Port 8000**: **STRICTLY FORBIDDEN** (Dedicated to existing external system services).

---

## 2. Architecture & Design Principles

- **Modular Python Backend**: Decoupled modules for `data`, `features`, `strategies`, `labels`, `backtest`, `models`, `evaluation`, and `experiments`.
- **Low-Memory Strategy**: Single heavy worker model (`VANTA_MAX_WORKERS=1`), Polars lazy execution, streaming Parquet writes, bounded chart subsampling.
- **Bloomberg Ergonomics**: High information density, dark graphite UI (`#0B0D13`), amber accent (`#F59E0B`), fixed-width tabular numerals, keyboard-friendly scanning.
- **Statistical Integrity**: Purged walk-forward cross-validation, stationary block-bootstrap confidence intervals, and strict separation between validation tuning and untouched Out-Of-Sample (OOS) testing.

---

## 3. Project Documentation

Detailed technical documentation is available under `docs/`:
- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md): 7-phase phased execution plan and acceptance criteria.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Full architectural specification, data schemas, and mathematical foundations.
- [`docs/PORTS_AND_RUNTIME.md`](docs/PORTS_AND_RUNTIME.md): Port audit, hardware budgets, and PID-tracked process lifecycle.

---

## 4. Current Status: PHASE 0 COMPLETE
Phase 0 environment audit and architectural specifications are complete. Awaiting user approval to proceed to **Phase 1 (UI Shell & Project Skeleton)**.
