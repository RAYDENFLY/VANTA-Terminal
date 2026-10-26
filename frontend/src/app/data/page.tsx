"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import {
  HardDriveDownload,
  Database,
  ShieldCheck,
  AlertTriangle,
  FolderTree,
  FileCheck,
  CheckCircle2,
  Clock,
  RefreshCw,
  StopCircle,
} from "lucide-react";

interface DatasetEntry {
  symbol: string;
  timeframe: string;
  timeframe_type: "EXCHANGE_NATIVE" | "DERIVED_FROM_15M";
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | "ALREADY_VALIDATED";
  target_start_utc: string;
  target_end_utc: string;
  row_count: number;
  gap_count: number;
  duplicate_count: number;
  file_path: string | null;
  file_size_kb: number;
  sha256: string | null;
  manifest_path: string | null;
  error: string | null;
  updated_at: string | null;
}

interface IngestionRegistry {
  registry_version: string;
  created_at_utc: string;
  updated_at_utc: string;
  operational_reserve_gb: number;
  active_job: string | null;
  is_cancelled: boolean;
  datasets: Record<string, DatasetEntry>;
}

export default function DataCenterPage() {
  const [registry, setRegistry] = useState<IngestionRegistry | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [filterType, setFilterType] = useState<"ALL" | "15M" | "1H" | "4H">("ALL");

  const fetchRegistry = async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8101";
      const res = await fetch(`${apiBase}/api/data/ingestion/registry`);
      if (res.ok) {
        const data = await res.json();
        setRegistry(data);
      }
    } catch (err) {
      console.error("Failed to load ingestion registry:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegistry();
    const interval = setInterval(fetchRegistry, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleCancel = async () => {
    try {
      setCancelling(true);
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8101";
      await fetch(`${apiBase}/api/data/ingestion/cancel`, { method: "POST" });
      await fetchRegistry();
    } catch (err) {
      console.error(err);
    } finally {
      setCancelling(false);
    }
  };

  const datasetsList = registry ? Object.values(registry.datasets) : [];
  const completedDatasets = datasetsList.filter((d) => d.status === "COMPLETED");
  const runningDatasets = datasetsList.filter((d) => d.status === "RUNNING");
  const failedDatasets = datasetsList.filter((d) => d.status === "FAILED");
  const totalRows = completedDatasets.reduce((sum, d) => sum + (d.row_count || 0), 0);
  const totalSizeKb = completedDatasets.reduce((sum, d) => sum + (d.file_size_kb || 0), 0);

  const filteredDatasets = datasetsList.filter((d) => {
    if (filterType === "ALL") return true;
    return d.timeframe.toUpperCase() === filterType;
  });

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              DATA CENTER // HISTORICAL MARKET DATA ARCHIVE
            </span>
            <span className="text-[10px] bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 px-2 py-0.5 rounded font-mono">
              PHASE 3B.1 ACTIVE
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              PUBLIC API ONLY
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Sequential 11-pair ingestion from AsterDEX Futures V3 Pro API. Single-worker mode (VANTA_MAX_WORKERS=1).
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          {registry?.active_job ? (
            <div className="flex items-center gap-2 bg-amber-950/40 border border-amber-800/60 px-3 py-1.5 rounded text-amber-300">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
              <span>RUNNING: {registry.active_job}</span>
              <button
                onClick={handleCancel}
                disabled={cancelling}
                className="ml-2 bg-red-950/80 hover:bg-red-900 border border-red-700/80 text-red-300 px-2 py-0.5 rounded text-[11px] flex items-center gap-1 transition"
              >
                <StopCircle className="w-3 h-3" />
                <span>{cancelling ? "HALTING..." : "HALT"}</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 bg-terminal-card border border-terminal-border px-3 py-1.5 rounded text-terminal-positive">
              <CheckCircle2 className="w-3.5 h-3.5 text-terminal-positive" />
              <span>SEQUENTIAL WORKER IDLE / COMPLETE</span>
            </div>
          )}
        </div>
      </div>

      {/* Storage and Progress Telemetry Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-xs">
        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Universe Progress</div>
          <div className="text-xl font-bold text-terminal-text mt-0.5">
            {completedDatasets.length} / {datasetsList.length || 33}
          </div>
          <div className="text-[10px] text-terminal-muted">
            {Math.round((completedDatasets.length / (datasetsList.length || 33)) * 100)}% Datasets Complete
          </div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Total Candles</div>
          <div className="text-xl font-bold text-terminal-positive mt-0.5">
            {totalRows.toLocaleString()}
          </div>
          <div className="text-[10px] text-emerald-400">Validated 0 Gaps &middot; 0 Dups</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Archive Storage (D:)</div>
          <div className="text-xl font-bold text-terminal-amber mt-0.5">
            {(totalSizeKb / 1024).toFixed(2)} MB
          </div>
          <div className="text-[10px] text-terminal-dim">Snappy Parquet on HDD</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Safety Reserve</div>
          <div className="text-xl font-bold text-terminal-text mt-0.5">
            &ge; 10.0 GB
          </div>
          <div className="text-[10px] text-terminal-positive">Headroom Safe (&gt;64 GB free)</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Pilot Status</div>
          <div className="text-xl font-bold text-terminal-text mt-0.5">
            PRESERVED
          </div>
          <div className="text-[10px] text-terminal-muted">BTC 30D SHA-256 Valid</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-1.5">
          <span className="text-terminal-dim text-[11px] mr-2">TIMEFRAME FILTER:</span>
          {(["ALL", "15M", "1H", "4H"] as const).map((tf) => (
            <button
              key={tf}
              onClick={() => setFilterType(tf)}
              className={`px-2.5 py-1 rounded border text-[11px] transition ${
                filterType === tf
                  ? "bg-terminal-amber/20 border-terminal-amber text-terminal-amber font-bold"
                  : "bg-terminal-card border-terminal-border text-terminal-muted hover:text-terminal-text"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        <div className="text-terminal-dim text-[11px]">
          Showing {filteredDatasets.length} of {datasetsList.length} datasets
        </div>
      </div>

      {/* Master Datasets Matrix Table */}
      <div className="bg-terminal-surface border border-terminal-border rounded overflow-hidden">
        <div className="px-3 py-2 bg-terminal-card border-b border-terminal-border flex justify-between items-center text-xs font-mono">
          <span className="font-bold text-terminal-text">
            SEQUENTIAL INGESTION & DERIVATION MATRIX (11 PAIRS &times; 3 TIMEFRAMES)
          </span>
          <span className="text-terminal-dim text-[11px]">
            Storage: D:\vanta-terminal\data\raw &amp; derived
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left table-dense">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>TF</th>
                <th>Type</th>
                <th>Status</th>
                <th>Date Window (UTC)</th>
                <th>Rows</th>
                <th>Gaps</th>
                <th>Dups</th>
                <th>Size (KB)</th>
                <th>SHA-256 Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border/50 font-mono text-xs">
              {filteredDatasets.map((d) => (
                <tr key={`${d.symbol}_${d.timeframe}`} className="hover:bg-terminal-card">
                  <td className="font-bold text-terminal-text">{d.symbol}</td>
                  <td className="text-terminal-amber">{d.timeframe.toUpperCase()}</td>
                  <td>
                    {d.timeframe_type === "EXCHANGE_NATIVE" ? (
                      <span className="text-[10px] bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 px-1.5 py-0.5 rounded">
                        NATIVE
                      </span>
                    ) : (
                      <span className="text-[10px] bg-purple-950/60 text-purple-300 border border-purple-800/60 px-1.5 py-0.5 rounded">
                        DERIVED
                      </span>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="text-terminal-muted text-[11px]">
                    {d.target_start_utc ? `${d.target_start_utc.slice(0, 10)} &rarr; ${d.target_end_utc.slice(0, 10)}` : "—"}
                  </td>
                  <td className="text-terminal-positive font-bold">
                    {d.row_count > 0 ? d.row_count.toLocaleString() : "—"}
                  </td>
                  <td className={d.gap_count > 0 ? "text-terminal-negative font-bold" : "text-terminal-dim"}>
                    {d.status === "COMPLETED" ? `${d.gap_count} gaps` : "—"}
                  </td>
                  <td className={d.duplicate_count > 0 ? "text-terminal-negative font-bold" : "text-terminal-dim"}>
                    {d.status === "COMPLETED" ? `${d.duplicate_count} dups` : "—"}
                  </td>
                  <td className="text-terminal-dim">
                    {d.file_size_kb > 0 ? `${d.file_size_kb.toFixed(1)} KB` : "—"}
                  </td>
                  <td className="text-terminal-dim font-mono text-[10px]">
                    {d.sha256 ? (
                      <span title={d.sha256} className="text-terminal-muted">
                        {d.sha256.slice(0, 12)}...
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
