"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ModelArenaResponse } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Swords,
  Lock,
  Layers,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Scale,
} from "lucide-react";

export default function ModelArenaPage() {
  const [data, setData] = useState<ModelArenaResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadModels() {
      try {
        setLoading(true);
        const res = await api.getModels();
        setData(res);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadModels();
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Banner: Arena Comparison Protocol */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              MODEL ARENA // THREE ARCHITECTURAL CONFIGURATIONS
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              PRE-COMPUTATION DEMO
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Target: Probability of Take Profit before Stop Loss / Expiry under Triple-Barrier Labeling.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400 font-mono text-xs flex items-center gap-1.5">
            <Lock className="w-3.5 h-3.5 text-amber-500" />
            <span>OOS HOLDOUT: LOCKED (UNTOUCHED)</span>
          </div>
        </div>
      </div>

      {/* Model Configurations Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data?.configurations.map((config) => {
          return (
            <div
              key={config.config_id}
              className="bg-terminal-surface border border-terminal-border hover:border-terminal-borderLight rounded p-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-mono text-terminal-dim uppercase tracking-wider">
                    {config.config_id}
                  </span>
                  <StatusBadge status={config.status} />
                </div>

                <h3 className="text-sm font-bold font-mono text-terminal-text">
                  {config.name}
                </h3>
                <div className="text-[11px] font-mono text-terminal-amber mt-0.5">
                  {config.architecture}
                </div>
                <p className="text-xs text-terminal-muted mt-2 leading-relaxed">
                  {config.description}
                </p>

                {/* Scope & Features pill */}
                <div className="mt-3 py-1.5 px-2.5 rounded bg-terminal-card border border-terminal-border text-[11px] font-mono flex justify-between items-center text-terminal-muted">
                  <span>Scope: {config.training_scope}</span>
                  <span className="text-terminal-text font-semibold">
                    {config.features_count} Features
                  </span>
                </div>

                {/* Validation Benchmark Metrics Table */}
                <div className="mt-4 pt-3 border-t border-terminal-border space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Validation Sharpe:</span>
                    <span className="font-bold text-terminal-amber">
                      {config.val_sharpe.toFixed(2)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Sharpe 95% Bootstrap CI:</span>
                    <span className="text-terminal-text">
                      [{config.bootstrap_sharpe_ci95[0].toFixed(2)}, {config.bootstrap_sharpe_ci95[1].toFixed(2)}]
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Brier Calibration Score:</span>
                    <span className="text-terminal-positive font-semibold">
                      {config.val_brier_score.toFixed(3)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Validation ROC-AUC:</span>
                    <span className="text-terminal-text">
                      {config.val_roc_auc.toFixed(3)}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Max Drawdown:</span>
                    <span className="text-terminal-text">
                      {config.val_max_drawdown_pct.toFixed(1)}%
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Sample Size:</span>
                    <span className="text-terminal-muted">
                      {config.sample_size_trades} trades
                    </span>
                  </div>
                </div>
              </div>

              {/* Locked OOS Notice */}
              <div className="mt-4 pt-3 border-t border-terminal-border">
                <div className="p-2 rounded bg-terminal-card border border-terminal-border text-[10px] font-mono text-terminal-dim flex items-center justify-between">
                  <span>OOS Test Holdout:</span>
                  <span className="text-amber-500 font-semibold flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    <span>LOCKED</span>
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Rigorous Evaluation Rules Card */}
      <div className="bg-terminal-surface border border-terminal-border rounded p-4 font-mono text-xs space-y-2">
        <div className="flex items-center gap-2 font-bold text-terminal-text">
          <Scale className="w-4 h-4 text-terminal-amber" />
          <span>STATISTICAL INTEGRITY & EVALUATION PROTOCOL</span>
        </div>
        <p className="text-terminal-muted text-xs leading-relaxed">
          1. <strong>Chronological Walk-Forward:</strong> Folds are strictly chronological. Past observations train future folds with no shuffle leakage.
          <br />
          2. <strong>Purged & Embargoed:</strong> Samples adjacent to fold boundaries are purged by the maximum label duration (24 bars) to eliminate overlapping event leakage.
          <br />
          3. <strong>Calibration on Validation Only:</strong> In Configuration C, Platt/Isotonic calibration curves are fitted exclusively on the validation fold and never on test holdout.
        </p>
      </div>
    </div>
  );
}
