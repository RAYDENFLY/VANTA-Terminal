"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/MetricCard";
import { StatusBadge } from "@/components/StatusBadge";
import { PairsListResponse, ExperimentsResponse, SystemStatusData } from "@/lib/types";
import {
  Coins,
  Cpu,
  Layers,
  ArrowRight,
  ShieldAlert,
  Database,
  Activity,
} from "lucide-react";

export default function TerminalOverview() {
  const [pairsData, setPairsData] = useState<PairsListResponse | null>(null);
  const [experimentsData, setExperimentsData] = useState<ExperimentsResponse | null>(null);
  const [systemData, setSystemData] = useState<SystemStatusData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [p, exp, sys] = await Promise.all([
          api.getPairs(),
          api.getExperiments(),
          api.getSystemStatus(),
        ]);
        setPairsData(p);
        setExperimentsData(exp);
        setSystemData(sys);
        setError(null);
      } catch (err: any) {
        setError("Unable to connect to local backend at 127.0.0.1:8101.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Banner: Research Workstation Identity & Safety */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              WORKSTATION STATUS // PHASE 1 ACTIVE
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              SYNTHETIC DEMO FIXTURES ONLY
            </span>
            <span className="text-[10px] bg-amber-950/40 text-amber-400 px-2 py-0.5 rounded border border-amber-800/60 font-mono">
              ADAPTER TARGET: ASTERDEX FUTURES V3 (PRO API)
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-1">
            Bloomberg-inspired quantitative terminal for crypto-futures strategy modeling. Adapter target: AsterDEX Futures V3 Pro API (Public data only).
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <div className="px-2.5 py-1 rounded bg-amber-950/40 border border-amber-800/60 text-amber-400 font-mono flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>LOCAL RESEARCH · NO LIVE ORDERS</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/40 border border-rose-800 text-rose-300 p-3 rounded text-xs">
          {error} Verify the FastAPI backend is running on port 8101 (`scripts/start.ps1`).
        </div>
      )}

      {/* Primary Telemetry Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard
          label="Universe Size"
          value={pairsData ? `${pairsData.universe_size} Pairs` : "11 Pairs"}
          subtext="Target crypto-futures"
          isDemo={false}
        />
        <MetricCard
          label="Data Coverage"
          value="0 / 11 Verified"
          subtext="Phase 2 audit pending"
          isDemo={true}
        />
        <MetricCard
          label="Completed Runs"
          value={experimentsData ? experimentsData.total_count : "3"}
          subtext="Validation benchmark"
          isDemo={true}
        />
        <MetricCard
          label="Heavy Worker"
          value={systemData?.worker_status || "IDLE"}
          subtext="Max 1 concurrent job"
          isDemo={false}
        />
        <MetricCard
          label="Free Physical RAM"
          value={
            systemData?.resources?.memory?.available_ram_gb != null
              ? `${systemData.resources.memory.available_ram_gb} GB`
              : "3.50 GB"
          }
          subtext="16 GB total headroom"
          isDemo={false}
        />
        <MetricCard
          label="Storage Free (D:)"
          value={
            systemData?.resources?.disk_d?.free_gb != null
              ? `${systemData.resources.disk_d.free_gb} GB`
              : "64.9 GB"
          }
          subtext="Dataset & artifact store"
          isDemo={false}
        />
      </div>

      {/* Main Two-Column Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Target Pair Universe Quick Scan (7 cols) */}
        <div className="lg:col-span-7 bg-terminal-surface border border-terminal-border rounded overflow-hidden">
          <div className="px-3 py-2 bg-terminal-card border-b border-terminal-border flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Coins className="w-3.5 h-3.5 text-terminal-amber" />
              <span className="text-xs font-bold font-mono tracking-wide">
                RESEARCH UNIVERSE // 11 PAIRS
              </span>
            </div>
            <Link
              href="/pairs"
              className="text-[11px] text-terminal-amber hover:underline flex items-center gap-1 font-mono"
            >
              <span>Pair Monitor</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left table-dense">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Contract</th>
                  <th>Timeframes</th>
                  <th>Coverage</th>
                  <th>Model State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-terminal-border/50 font-mono text-xs">
                {pairsData?.pairs.slice(0, 6).map((pair) => (
                  <tr key={pair.symbol}>
                    <td className="font-semibold text-terminal-text">
                      {pair.symbol}
                    </td>
                    <td className="text-terminal-muted">{pair.contract_type}</td>
                    <td className="text-terminal-dim">15m, 1H, 4H</td>
                    <td>
                      <StatusBadge status={pair.coverage_status} />
                    </td>
                    <td>
                      <StatusBadge status={pair.model_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-2 bg-terminal-card/30 border-t border-terminal-border flex justify-between items-center text-[11px] text-terminal-dim px-3">
            <span>Displaying 6 of 11 pairs</span>
            <span className="text-amber-500/80">Pending Phase 2 Coverage Audit</span>
          </div>
        </div>

        {/* Right Column: Recent Experiments & Quick Lab Actions (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Recent Experiment Registry Card */}
          <div className="bg-terminal-surface border border-terminal-border rounded overflow-hidden">
            <div className="px-3 py-2 bg-terminal-card border-b border-terminal-border flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Layers className="w-3.5 h-3.5 text-terminal-amber" />
                <span className="text-xs font-bold font-mono tracking-wide">
                  RECENT RUNS // DEMO REGISTRY
                </span>
              </div>
              <Link
                href="/experiments"
                className="text-[11px] text-terminal-amber hover:underline flex items-center gap-1 font-mono"
              >
                <span>View All</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="p-3 space-y-2">
              {experimentsData?.experiments.slice(0, 3).map((exp) => (
                <div
                  key={exp.run_id}
                  className="p-2 rounded bg-terminal-card border border-terminal-border flex justify-between items-center text-xs"
                >
                  <div>
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-terminal-text font-bold">
                        {exp.run_id}
                      </span>
                      <StatusBadge status={exp.status} />
                    </div>
                    <div className="text-[10px] text-terminal-muted font-mono mt-0.5">
                      {exp.strategy_family} · {exp.model_architecture}
                    </div>
                  </div>
                  <div className="text-right font-mono text-[11px]">
                    <div className="text-terminal-text">
                      SR:{" "}
                      <span className="text-terminal-amber font-semibold">
                        {exp.sharpe_ratio ?? "N/A"}
                      </span>
                    </div>
                    <div className="text-[10px] text-terminal-dim">
                      MaxDD: {exp.max_drawdown_pct ? `${exp.max_drawdown_pct}%` : "N/A"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Nav Cards */}
          <div className="grid grid-cols-2 gap-3">
            <Link
              href="/strategies"
              className="p-3 bg-terminal-surface border border-terminal-border hover:border-terminal-amber/50 rounded transition-colors group block"
            >
              <div className="text-[10px] font-mono text-terminal-dim uppercase">
                Strategy Lab
              </div>
              <div className="text-xs font-bold font-mono text-terminal-text group-hover:text-terminal-amber mt-1 flex items-center justify-between">
                <span>Rule Benchmarks</span>
                <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <p className="text-[10px] text-terminal-muted mt-1">
                Sweep-Reclaim, Breakout & Mean Reversion.
              </p>
            </Link>

            <Link
              href="/models"
              className="p-3 bg-terminal-surface border border-terminal-border hover:border-terminal-amber/50 rounded transition-colors group block"
            >
              <div className="text-[10px] font-mono text-terminal-dim uppercase">
                Model Arena
              </div>
              <div className="text-xs font-bold font-mono text-terminal-text group-hover:text-terminal-amber mt-1 flex items-center justify-between">
                <span>Global vs Specialist</span>
                <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              <p className="text-[10px] text-terminal-muted mt-1">
                Triple-barrier ML probability calibration.
              </p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
