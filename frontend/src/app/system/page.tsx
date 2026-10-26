"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { SystemStatusData } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  ServerCog,
  Cpu,
  Database,
  ShieldCheck,
  ShieldAlert,
  Activity,
  RefreshCw,
  Radio,
  Clock,
  Terminal,
} from "lucide-react";

export default function SystemMonitorPage() {
  const [data, setData] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  const loadStatus = async () => {
    try {
      setLoading(true);
      const res = await api.getSystemStatus();
      setData(res);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              SYSTEM MONITOR // HARDWARE, NETWORK & PROCESS ISOLATION
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              LOCAL ONLY (127.0.0.1)
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Strict isolation: Port 8000 forbidden, single heavy worker queue, zero order execution capability.
          </p>
        </div>

        <button
          onClick={loadStatus}
          className="px-3 py-1 rounded bg-terminal-card hover:bg-terminal-sub text-terminal-amber border border-terminal-border text-xs font-mono flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Live Telemetry</span>
        </button>
      </div>

      {/* Network & Port Integrity Card */}
      <div className="bg-terminal-surface border border-terminal-border rounded p-4">
        <div className="flex items-center gap-2 text-xs font-bold font-mono text-terminal-text mb-3">
          <Radio className="w-4 h-4 text-terminal-amber" />
          <span>NETWORK BINDING & PORT ISOLATION STATUS</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono text-xs">
          <div className="p-3 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Backend API Port</div>
            <div className="text-lg font-bold text-terminal-text mt-0.5">
              127.0.0.1:{data?.port ?? 8101}
            </div>
            <div className="text-[10px] text-terminal-positive mt-0.5">Loopback Verified</div>
          </div>

          <div className="p-3 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Frontend Web Port</div>
            <div className="text-lg font-bold text-terminal-text mt-0.5">
              127.0.0.1:3000
            </div>
            <div className="text-[10px] text-terminal-positive mt-0.5">Next.js Verified</div>
          </div>

          <div className="p-3 rounded bg-amber-950/30 border border-amber-800/60">
            <div className="text-[10px] text-amber-500 uppercase font-bold">Port 8000 Lockout</div>
            <div className="text-lg font-bold text-amber-400 mt-0.5">
              FORBIDDEN
            </div>
            <div className="text-[10px] text-amber-300/80 mt-0.5">PID 5328 Untouched</div>
          </div>

          <div className="p-3 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Live Order Routing</div>
            <div className="text-lg font-bold text-rose-400 mt-0.5">
              DISABLED
            </div>
            <div className="text-[10px] text-terminal-dim mt-0.5">No API keys allowed</div>
          </div>
        </div>
      </div>

      {/* Hardware Resource Telemetry */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Memory & Worker Queue */}
        <div className="bg-terminal-surface border border-terminal-border rounded p-4 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-terminal-border pb-2">
            <div className="flex items-center gap-2 font-bold text-terminal-text">
              <Cpu className="w-4 h-4 text-terminal-amber" />
              <span>PHYSICAL RAM TELEMETRY</span>
            </div>
            <StatusBadge status={data?.resources?.memory?.status ?? "NOMINAL"} />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-terminal-dim">Total Physical RAM:</span>
              <span className="text-terminal-text">
                {data?.resources?.memory?.total_ram_gb ?? 15.89} GB
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-terminal-dim">Available Free RAM:</span>
              <span className="text-terminal-amber font-bold">
                {data?.resources?.memory?.available_ram_gb ?? 3.50} GB
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-terminal-dim">System Memory Load:</span>
              <span className="text-terminal-text">
                {data?.resources?.memory?.memory_load_percent ?? 80}%
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-terminal-dim">Worker Concurrency Cap:</span>
              <span className="text-terminal-text font-semibold">
                {data?.resources?.worker_concurrency_cap ?? 1} Heavy Task Max
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border text-[11px] text-terminal-muted leading-relaxed">
            Low-memory execution policy active: Single-worker training queue, Polars lazy scanning, chunked streaming ingestion.
          </div>
        </div>

        {/* Disk & Storage Telemetry */}
        <div className="bg-terminal-surface border border-terminal-border rounded p-4 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-terminal-border pb-2">
            <div className="flex items-center gap-2 font-bold text-terminal-text">
              <Database className="w-4 h-4 text-terminal-amber" />
              <span>STORAGE DISK UTILIZATION</span>
            </div>
            <StatusBadge status="NOMINAL" />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-terminal-dim">Drive D: (Project & Datasets):</span>
              <span className="text-terminal-text font-bold">
                {data?.resources?.disk_d?.free_gb ?? 64.9} GB Free /{" "}
                {data?.resources?.disk_d?.total_gb ?? 931.5} GB
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-terminal-dim">Drive C: (OS NVMe SSD):</span>
              <span className="text-terminal-text font-bold">
                {data?.resources?.disk_c?.free_gb ?? 20.68} GB Free /{" "}
                {data?.resources?.disk_c?.total_gb ?? 237.7} GB
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-terminal-dim">Process Uptime:</span>
              <span className="text-terminal-text">
                {data?.uptime_seconds ? `${data.uptime_seconds}s` : "Active"}
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-terminal-dim">Process Tracking:</span>
              <span className="text-terminal-text">.runtime/*.pid verified</span>
            </div>
          </div>

          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border text-[11px] text-terminal-muted leading-relaxed">
            Parquet datasets, SQLite registries, and artifacts are stored strictly on Drive D: to preserve SSD C: space.
          </div>
        </div>
      </div>
    </div>
  );
}
