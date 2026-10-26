"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ExperimentsResponse, ExperimentRecord } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import { ScrollText, Filter, Clock, HardDrive, Cpu } from "lucide-react";

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
              EXPERIMENT CENTER // REPRODUCIBLE RUN REGISTRY
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              IN-MEMORY REGISTRY (PHASE 1)
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
              <option value="COMPLETED">Completed</option>
              <option value="RUNNING">Running</option>
              <option value="QUEUED">Queued</option>
            </select>
          </div>
        </div>
      </div>

      {/* Active Run Card (if any) */}
      {data?.active_run && (
        <div className="bg-terminal-surface border border-amber-800/60 p-3 rounded flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-terminal-amber animate-ping" />
            <div>
              <span className="font-bold text-terminal-amber">
                ACTIVE EXPERIMENT: {data.active_run.run_id}
              </span>
              <span className="text-terminal-dim ml-2">
                [{data.active_run.strategy_family} // {data.active_run.model_architecture}]
              </span>
            </div>
          </div>
          <StatusBadge status={data.active_run.status} />
        </div>
      )}

      {/* Main Runs Table */}
      <div className="bg-terminal-surface border border-terminal-border rounded overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left table-dense">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Config Hash</th>
                <th>Strategy / Model</th>
                <th>Status</th>
                <th>Created (UTC)</th>
                <th>Runtime</th>
                <th>Peak RAM</th>
                <th>Trades</th>
                <th>Sharpe</th>
                <th>Max DD</th>
                <th>Win Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border/50 font-mono text-xs">
              {data?.experiments.map((exp) => (
                <tr key={exp.run_id} className="hover:bg-terminal-card">
                  <td className="font-bold text-terminal-text">{exp.run_id}</td>
                  <td className="text-terminal-dim">#{exp.config_hash}</td>
                  <td>
                    <div className="text-terminal-text font-medium">
                      {exp.strategy_family}
                    </div>
                    <div className="text-[10px] text-terminal-dim">
                      {exp.model_architecture}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={exp.status} />
                  </td>
                  <td className="text-terminal-dim">{exp.created_at}</td>
                  <td className="text-terminal-muted">
                    {exp.runtime_seconds != null ? `${exp.runtime_seconds}s` : "—"}
                  </td>
                  <td className="text-terminal-muted">
                    {exp.peak_memory_mb != null ? `${exp.peak_memory_mb} MB` : "—"}
                  </td>
                  <td className="text-terminal-text">
                    {exp.sample_size_trades != null ? exp.sample_size_trades : "—"}
                  </td>
                  <td className="font-semibold text-terminal-amber">
                    {exp.sharpe_ratio != null ? exp.sharpe_ratio.toFixed(2) : "—"}
                  </td>
                  <td className="text-terminal-text">
                    {exp.max_drawdown_pct != null
                      ? `${exp.max_drawdown_pct.toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="text-terminal-text">
                    {exp.win_rate_pct != null
                      ? `${exp.win_rate_pct.toFixed(1)}%`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-2.5 bg-terminal-card/40 border-t border-terminal-border flex justify-between items-center text-xs font-mono text-terminal-dim px-4">
          <span>Total runs in registry: {data?.total_count ?? 0}</span>
          <span>Engine: {data?.storage_engine ?? "In-Memory"}</span>
        </div>
      </div>
    </div>
  );
}
