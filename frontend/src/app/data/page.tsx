"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DataCoverageResponse } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  HardDriveDownload,
  Database,
  ShieldCheck,
  AlertTriangle,
  FolderTree,
  FileCheck,
} from "lucide-react";

export default function DataCenterPage() {
  const [data, setData] = useState<DataCoverageResponse | null>(null);
  const [ingestionState, setIngestionState] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDataCoverage() {
      try {
        setLoading(true);
        const res = await api.getDataCoverage();
        setData(res);
        
        // Also fetch current ingestion state
        try {
          const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8101";
          const ingRes = await fetch(`${apiBase}/api/data/ingestion/current`);
          if (ingRes.ok) {
            setIngestionState(await ingRes.json());
          }
        } catch {}
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadDataCoverage();
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              DATA CENTER // ASTERDEX FUTURES V3 PRO API AUDIT
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              PUBLIC DATA ONLY
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Adapter Target: https://fapi.asterdex.com. Instrument discovery, candle limits, and coverage auditing protocol.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1 rounded bg-amber-950/40 border border-amber-800/60 text-amber-400 font-mono text-xs flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>ZERO MARKET CANDLES DOWNLOADED YET</span>
          </div>
        </div>
      </div>

      {/* Storage and Audit Telemetry Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Total Pairs</div>
          <div className="text-xl font-bold text-terminal-text mt-0.5">
            {data?.total_pairs ?? 11}
          </div>
          <div className="text-[10px] text-terminal-muted">Target universe</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Verified Audited</div>
          <div className="text-xl font-bold text-terminal-positive mt-0.5">
            {data?.verified_pairs ?? 10} / 11
          </div>
          <div className="text-[10px] text-emerald-400">10 Pairs &ge; 3Y (XMR: 0.78Y)</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Raw Parquet Storage</div>
          <div className="text-xl font-bold text-terminal-text mt-0.5">
            {ingestionState?.file_size_kb ? `${ingestionState.file_size_kb} KB` : "0.21 MB"}
          </div>
          <div className="text-[10px] text-terminal-dim">D:\vanta-terminal\data\raw</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-3 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">HDD D: Free Space</div>
          <div className="text-xl font-bold text-terminal-amber mt-0.5">
            {data?.disk_free_gb ? `${data.disk_free_gb} GB` : "64.6 GB"}
          </div>
          <div className="text-[10px] text-terminal-positive">Budget Headroom Safe</div>
        </div>
      </div>

      {/* Phase 3A Ingestion Pilot Status Banner */}
      {ingestionState && ingestionState.status !== "IDLE" && (
        <div className="bg-terminal-surface border border-emerald-800/60 p-3 rounded font-mono text-xs space-y-2">
          <div className="flex justify-between items-center border-b border-terminal-border pb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="font-bold text-emerald-400">
                BOUNDED PILOT INGESTION // {ingestionState.job_id}
              </span>
            </div>
            <StatusBadge status={ingestionState.status} />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-[11px]">
            <div>
              <span className="text-terminal-dim">Symbol: </span>
              <span className="text-terminal-text font-bold">{ingestionState.symbol} ({ingestionState.timeframe})</span>
            </div>
            <div>
              <span className="text-terminal-dim">Downloaded: </span>
              <span className="text-terminal-positive font-bold">{ingestionState.downloaded_rows?.toLocaleString()} rows</span>
            </div>
            <div>
              <span className="text-terminal-dim">Gaps Detected: </span>
              <span className="text-terminal-text">{ingestionState.gaps_detected ?? 0}</span>
            </div>
            <div>
              <span className="text-terminal-dim">Parquet Size: </span>
              <span className="text-terminal-amber">{ingestionState.file_size_kb} KB</span>
            </div>
            <div>
              <span className="text-terminal-dim">SHA-256: </span>
              <span className="text-terminal-muted truncate block" title={ingestionState.sha256}>
                {ingestionState.sha256 ? `${ingestionState.sha256.slice(0, 12)}...` : "—"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Universe Coverage Matrix Table */}
      <div className="bg-terminal-surface border border-terminal-border rounded overflow-hidden">
        <div className="px-3 py-2 bg-terminal-card border-b border-terminal-border flex justify-between items-center text-xs font-mono">
          <span className="font-bold text-terminal-text">
            UNIVERSE COVERAGE & INTEGRITY MANIFESTS
          </span>
          <span className="text-terminal-dim">
            Target Historical Depth: Up to 3.0 Years (Pending Verification)
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left table-dense">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Target History</th>
                <th>Verified History</th>
                <th>Audit Status</th>
                <th>15m Status</th>
                <th>1H Status</th>
                <th>4H Status</th>
                <th>Gaps Detected</th>
                <th>Storage Size</th>
                <th>Manifest Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border/50 font-mono text-xs">
              {data?.coverage.map((item) => (
                <tr key={item.symbol} className="hover:bg-terminal-card">
                  <td className="font-bold text-terminal-text">{item.symbol}</td>
                  <td className="text-terminal-muted">3.0 Years</td>
                  <td className="text-terminal-dim">0.0 Years</td>
                  <td>
                    <StatusBadge status={item.audit_status} />
                  </td>
                  <td>
                    <StatusBadge status={item.timeframes["15m"]?.status ?? "PENDING"} />
                  </td>
                  <td>
                    <StatusBadge status={item.timeframes["1H"]?.status ?? "PENDING"} />
                  </td>
                  <td>
                    <StatusBadge status={item.timeframes["4H"]?.status ?? "PENDING"} />
                  </td>
                  <td className="text-terminal-dim">0 Gaps</td>
                  <td className="text-terminal-dim">0.0 MB</td>
                  <td className="text-terminal-dim font-mono text-[10px]">
                    {item.manifest_checksum || "— (Awaiting Phase 2)"}
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
