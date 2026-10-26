"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StrategyLabResponse, StrategyCandidate } from "@/lib/types";
import { StatusBadge } from "@/components/StatusBadge";
import {
  FlaskConical,
  ShieldCheck,
  Lock,
  Percent,
  CheckCircle2,
  AlertOctagon,
  Scale,
} from "lucide-react";

export default function StrategyLabPage() {
  const [data, setData] = useState<StrategyLabResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [freezing, setFreezing] = useState<string | null>(null);
  const [freezeMessage, setFreezeMessage] = useState<string | null>(null);

  const loadStrategies = async () => {
    try {
      setLoading(true);
      const res = await api.getStrategies();
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStrategies();
  }, []);

  const handleFreeze = async (strategyId: string) => {
    try {
      setFreezing(strategyId);
      const res = await api.freezeStrategy(strategyId);
      setFreezeMessage(res.message);
      await loadStrategies();
    } catch (err) {
      console.error(err);
    } finally {
      setFreezing(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner: Pre-ML Strategy Selection Protocol */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              STRATEGY LAB // CANDIDATE BENCHMARK & FREEZE
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              VALIDATION BENCHMARK
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Rule-based strategy selection must precede ML model comparison. Evaluated over identical walk-forward splits.
          </p>
        </div>

        <div className="px-3 py-1 rounded bg-amber-950/40 border border-amber-800/60 text-amber-400 font-mono text-xs flex items-center gap-1.5">
          <Scale className="w-3.5 h-3.5" />
          <span>Cost-Adjusted Walk-Forward Validation</span>
        </div>
      </div>

      {freezeMessage && (
        <div className="bg-emerald-950/40 border border-emerald-800 text-emerald-300 p-3 rounded text-xs font-mono flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{freezeMessage}</span>
        </div>
      )}

      {/* Strategy Candidates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data?.candidates.map((cand) => {
          const isFrozen = cand.status === "FROZEN";
          const isRejected = cand.status === "REJECTED";

          return (
            <div
              key={cand.id}
              className={`bg-terminal-surface border rounded p-4 flex flex-col justify-between transition-all ${
                isFrozen
                  ? "border-emerald-500/80 shadow-sm shadow-emerald-950"
                  : isRejected
                  ? "border-terminal-border opacity-60"
                  : "border-terminal-border hover:border-terminal-borderLight"
              }`}
            >
              <div>
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-mono text-terminal-dim uppercase tracking-wider">
                    {cand.family}
                  </span>
                  <StatusBadge status={cand.status} />
                </div>

                <h3 className="text-sm font-bold font-mono text-terminal-text">
                  {cand.name}
                </h3>
                <p className="text-xs text-terminal-muted mt-1 leading-relaxed">
                  {cand.description}
                </p>

                {/* Performance Metrics Table */}
                <div className="mt-4 pt-3 border-t border-terminal-border space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Sharpe Ratio:</span>
                    <span
                      className={`font-bold ${
                        cand.sharpe_ratio >= 1.0
                          ? "text-terminal-amber"
                          : "text-terminal-muted"
                      }`}
                    >
                      {cand.sharpe_ratio.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Max Drawdown:</span>
                    <span className="text-terminal-text">
                      {cand.max_drawdown_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Win Rate:</span>
                    <span className="text-terminal-text">
                      {cand.win_rate_pct.toFixed(1)}% ({cand.trades_count} trades)
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Profit Factor:</span>
                    <span className="text-terminal-positive font-semibold">
                      {cand.profit_factor.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Expectancy (R):</span>
                    <span className="text-terminal-text">
                      +{cand.expectancy_r.toFixed(2)}R
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-terminal-dim">Avg Holding Bars:</span>
                    <span className="text-terminal-muted">
                      {cand.avg_holding_bars.toFixed(1)} bars
                    </span>
                  </div>
                </div>

                {/* Logic Rules Summary */}
                <div className="mt-4 p-2 bg-terminal-card rounded border border-terminal-border text-[10px] font-mono space-y-1 text-terminal-muted">
                  <div>
                    <span className="text-terminal-dim">Entry: </span>
                    {cand.entry_logic}
                  </div>
                  <div>
                    <span className="text-terminal-dim">Stop: </span>
                    {cand.stop_loss_logic}
                  </div>
                  <div>
                    <span className="text-terminal-dim">Target: </span>
                    {cand.take_profit_logic}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="mt-4 pt-3 border-t border-terminal-border">
                {isFrozen ? (
                  <div className="w-full py-1.5 px-3 rounded bg-emerald-950/60 border border-emerald-800 text-emerald-400 font-mono text-xs font-bold flex items-center justify-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" />
                    <span>FROZEN FOR ML MODEL ARENA</span>
                  </div>
                ) : (
                  <button
                    onClick={() => handleFreeze(cand.id)}
                    disabled={freezing !== null}
                    className="w-full py-1.5 px-3 rounded bg-terminal-card hover:bg-terminal-sub text-terminal-amber hover:text-terminal-text font-mono text-xs font-semibold border border-terminal-border transition-colors flex items-center justify-center gap-1.5"
                  >
                    <Lock className="w-3.5 h-3.5 text-terminal-dim" />
                    <span>
                      {freezing === cand.id ? "Freezing..." : "Freeze Candidate"}
                    </span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Cost Assumptions & Risk Rules Card */}
      <div className="bg-terminal-surface border border-terminal-border rounded p-4">
        <div className="flex items-center gap-2 text-xs font-bold font-mono text-terminal-text mb-3">
          <Percent className="w-3.5 h-3.5 text-terminal-amber" />
          <span>STANDARDIZED EXECUTION & FRICTION ASSUMPTIONS</span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-xs">
          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Maker Fee</div>
            <div className="text-sm font-bold text-terminal-text mt-0.5">
              {data?.cost_framework.maker_fee_pct ?? 0.02}%
            </div>
            <div className="text-[10px] text-terminal-muted">Post-only limit</div>
          </div>

          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Taker Fee</div>
            <div className="text-sm font-bold text-terminal-text mt-0.5">
              {data?.cost_framework.taker_fee_pct ?? 0.05}%
            </div>
            <div className="text-[10px] text-terminal-muted">Aggressive market</div>
          </div>

          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Base Slippage</div>
            <div className="text-sm font-bold text-terminal-text mt-0.5">
              {data?.cost_framework.base_slippage_bps ?? 2.0} bps
            </div>
            <div className="text-[10px] text-terminal-muted">+ Impact scaling</div>
          </div>

          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Funding Accrual</div>
            <div className="text-sm font-bold text-terminal-text mt-0.5">
              Every {data?.cost_framework.funding_accrual_hours ?? 8}h
            </div>
            <div className="text-[10px] text-terminal-muted">Perpetual rate debit</div>
          </div>

          <div className="p-2.5 rounded bg-terminal-card border border-terminal-border">
            <div className="text-[10px] text-terminal-dim uppercase">Bar Conflict</div>
            <div className="text-xs font-bold text-amber-400 mt-0.5">
              STOP FIRST
            </div>
            <div className="text-[10px] text-terminal-muted">Conservative penalty</div>
          </div>
        </div>
      </div>
    </div>
  );
}
