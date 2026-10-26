# VANTA Terminal — Local Storage & Resource Budget Specification
**Document ID:** DOC-STORAGE-001  
**Host Machine:** Windows 10/11 x64 · 16 GB RAM · Intel Core i7-7700HQ · GTX 1050 Ti  
**Audit Timestamp:** 2026-10-27T05:27:00Z  

---

## 1. Physical Storage State (Audited 2026-10-27)

| Drive | Media Type | Purpose | Total Capacity | Free Space | Free % | Safety Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C:** | NVMe SSD | OS, Development Tools, Python/Node Runtimes | 237.7 GB | **20.68 GB** | 8.7% | **RESTRICTED HEADROOM** (No dataset storage allowed) |
| **D:** | HDD | VANTA Project Root, Datasets, Parquet, SQLite, Models | 931.5 GB | **64.93 GB** | 7.0% | **PRIMARY RESEARCH DRIVE** (Ample headroom for project) |

---

## 2. Dataset Candle Volume Estimates (3-Year Target Depth)

### Per-Pair Candle Volume Calculations
- **15m Timeframe**:
  - 1 Year: $365.25 \times 24 \times 4 = 35,064$ candles
  - 3 Years: $35,064 \times 3 = \mathbf{105,192\text{ candles}}$
- **1H Timeframe**:
  - 1 Year: $365.25 \times 24 = 8,766$ candles
  - 3 Years: $8,766 \times 3 = \mathbf{26,298\text{ candles}}$
- **4H Timeframe**:
  - 1 Year: $365.25 \times 6 = 2,191.5$ candles
  - 3 Years: $2,191.5 \times 3 = \mathbf{6,575\text{ candles}}$
- **Total per pair (3 years across 15m, 1H, 4H)**:
  $$105,192 + 26,298 + 6,575 = \mathbf{138,065\text{ candles}}$$

### Universe Total (10 Full Pairs + 1 Partial Pair)
- 10 Qualified Pairs ($10 \times 138,065$): $1,380,650$ candles
- XMRUSDT ($0.78 \text{ year} \times 138,065$): $107,690$ candles
- **Total Historical Universe Candles**: $\mathbf{\approx 1,488,340\text{ candles}}$ (~1.49 million candles).

---

## 3. Storage Footprint Projections

### A. Raw Market Data (Parquet Snappy Compressed)
- 8 numerical columns (`timestamp`, `open`, `high`, `low`, `close`, `volume`, `quote_vol`, `trades_count`) + nullable funding rate.
- In Snappy-compressed Parquet, 1 million OHLCV records consume $\approx 25\text{ to }35\text{ MB}$.
- **Projected Raw Parquet Storage**: **$\approx 50\text{ to }75\text{ MB}$** for the entire 11-pair universe.

### B. Processed Feature Matrices (Parquet)
- 30 engineered features per bar (trend, volatility, microstructure, multi-timeframe lags).
- $1.5\text{M rows} \times 30\text{ columns} \times 8\text{ bytes} \approx 360\text{ MB}$ uncompressed.
- Compressed with Snappy / ZSTD: **$\approx 120\text{ to }160\text{ MB}$**.

### C. Serialized ML Model Artifacts & Scalers
- LightGBM GBDT / XGBoost trees (`max_depth=6`, `num_leaves=31`):
  - ~2.5 MB per tree model dump.
  - 11 Pair Specialists + 1 Global Model + Calibration scalers: **$\approx 40\text{ to }60\text{ MB}$**.

### D. SQLite Experiment Registry & Trade Ledgers
- Experiment records, parameter manifests, and trade ledgers: **$\approx 20\text{ to }40\text{ MB}$**.

---

## 4. Recommended Allocation & Safety Reserve

| Category | Projected Storage | Safety Buffer Allocation | Location |
| :--- | :--- | :--- | :--- |
| **Raw Parquet Datasets** | ~60 MB | 250 MB | `D:\vanta-terminal\data\raw\` |
| **Processed Feature Store** | ~140 MB | 500 MB | `D:\vanta-terminal\data\processed\` |
| **Model Artifacts** | ~50 MB | 200 MB | `D:\vanta-terminal\artifacts\models\` |
| **Reports, Ledgers & SQLite** | ~30 MB | 150 MB | `D:\vanta-terminal\artifacts\reports\` |
| **Emergency Safety Reserve** | N/A | **1,500 MB (1.5 GB)** | Preserved unallocated on D: |
| **Total Project Storage Budget**| **~280 MB** | **$\mathbf{2,600\text{ MB (2.6 GB)}}$** | **Drive D: HDD Only** |

### Safety Margin Assessment:
- Available space on Drive D: is **64.93 GB**.
- Total recommended budget with conservative safety reserve is **2.6 GB** (~4.0% of available D: capacity).
- **Available headroom remaining after allocation: > 62.3 GB**.
- **Drive C: Impact**: Exactly **0.0 MB** (Zero market data or artifacts on C:).
- Conclusion: The storage footprint is exceptionally safe and will not stress laptop resources.
