"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ExperimentsResponse, ExperimentRecord } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { ScrollText, Filter, Clock, HardDrive, Cpu, ShieldAlert, CheckCircle2 } from "lucide-react";

export default function ExperimentCenterPage() {
  const [data, setData] = useState<ExperimentsResponse | null>(null);
  const [filterStatus, setFilterStatus] = useState("ALL");
  const [loading, setLoading] = useState(true);

  const loadExperiments = async (status?: string) => {
    try {
      setLoading(true);
      const res = await api.getExperiments(status === "ALL" ? undefined : status);
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExperiments(filterStatus);
  }, [filterStatus]);

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              EXPERIMENT CENTER // DETERMINISTIC BACKTEST & RUN REGISTRY
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border font-mono">
              HDD PERSISTED (PHASE 3B.2)
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Immutable tracking of configurations, dataset hashes, execution telemetry, and validation artifacts.
          </p>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 bg-terminal-card border border-terminal-border rounded px-2.5 py-1 text-xs">
            <Filter className="w-3 h-3 text-terminal-dim" />
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-transparent text-terminal-muted focus:outline-none text-xs font-mono"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUCCESS">Success</option>
              <option value="COMPLETED">Completed</option>
              <option value="BLOCKED_MISSING_FUNDING_DATA">Blocked (Missing Funding)</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Engine & Safety Constraints Notice */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
        <div className="bg-terminal-card border border-terminal-border p-2.5 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Storage Engine</div>
          <div className="text-xs font-bold text-terminal-text mt-0.5 truncate">
            {data?.storage_engine || "D:\\vanta-terminal\\data\\backtests"}
          </div>
          <div className="text-[10px] text-terminal-muted">Versioned JSON &amp; Manifests</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-2.5 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Execution Semantics</div>
          <div className="text-xs font-bold text-terminal-amber mt-0.5">
            Zero Lookahead &middot; Conservative SL-First
          </div>
          <div className="text-[10px] text-terminal-muted">Market Orders @ Next Bar Open</div>
        </div>

        <div className="bg-terminal-card border border-terminal-border p-2.5 rounded">
          <div className="text-[10px] text-terminal-dim uppercase">Funding Accounting Status</div>
          <div className="text-xs font-bold text-amber-400 mt-0.5">
            BLOCKED_MISSING_FUNDING_DATA
          </div>
          <div className="text-[10px] text-terminal-dim">Historical 8h rates unvalidated</div>
        </div>
      </div>

      {/* Main Runs Table */}
      <div className="bg-terminal-surface border border-terminal-border rounded overflow-hidden">
        <div className="px-3 py-2 bg-terminal-card border-b border-terminal-border flex justify-between items-center text-xs font-mono">
          <span className="font-bold text-terminal-text">
            EXECUTED BACKTEST RUNS &amp; SYNTHETIC VERIFICATIONS
          </span>
          <span className="text-terminal-dim text-[11px]">
            Total Recorded Runs: {data?.total_count ?? 0}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left table-dense">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Config Hash</th>
                <th>Classification</th>
                <th>Status</th>
                <th>Created (UTC)</th>
                <th>Trades</th>
                <th>Sharpe</th>
                <th>Max DD</th>
                <th>Win Rate</th>
                <th>Cost / Audit Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border/50 font-mono text-xs">
              {data?.experiments.map((exp) => (
                <tr key={exp.run_id} className="hover:bg-terminal-card">
                  <td className="font-bold text-terminal-text">
                    <span className="truncate block max-w-[180px]" title={exp.run_id}>
                      {exp.run_id}
                    </span>
                  </td>
                  <td className="text-terminal-dim font-mono text-[10px]">
                    {exp.config_hash}
                  </td>
                  <td>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                      exp.strategy_family.includes("Synthetic")
                        ? "bg-purple-950/60 text-purple-300 border-purple-800/60"
                        : "bg-cyan-950/60 text-cyan-300 border-cyan-800/60"
                    }`}>
                      {exp.strategy_family.includes("Synthetic") ? "SYNTHETIC_TEST" : "HISTORICAL"}
                    </span>
                  </td>
                  <td>
                    <StatusBadge status={exp.status} />
                  </td>
                  <td className="text-terminal-muted text-[11px]">
                    {exp.created_at ? exp.created_at.slice(0, 19).replace("T", " ") : "—"}
                  </td>
                  <td className="text-terminal-text font-bold">
                    {exp.sample_size_trades ?? "—"}
                  </td>
                  <td className="text-terminal-amber">
                    {exp.sharpe_ratio != null ? exp.sharpe_ratio.toFixed(2) : "—"}
                  </td>
                  <td className="text-terminal-negative">
                    {exp.max_drawdown_pct != null ? `${exp.max_drawdown_pct.toFixed(2)}%` : "—"}
                  </td>
                  <td className="text-terminal-positive">
                    {exp.win_rate_pct != null ? `${exp.win_rate_pct.toFixed(1)}%` : "—"}
                  </td>
                  <td className="text-terminal-dim text-[11px] max-w-[220px] truncate" title={exp.notes}>
                    {exp.notes}
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
