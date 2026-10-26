"use client";

import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Candle, PairCandlesResponse } from "@/lib/types";
import {
  LineChart,
  Calendar,
  Layers,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
} from "lucide-react";

const TARGET_SYMBOLS = [
  "BTCUSDT.P",
  "ETHUSDT.P",
  "SOLUSDT.P",
  "BNBUSDT.P",
  "XRPUSDT.P",
  "ADAUSDT.P",
  "AVAXUSDT.P",
  "LINKUSDT.P",
  "DOGEUSDT.P",
  "LTCUSDT.P",
  "XMRUSDT.P",
];

function PairExplorerContent() {
  const searchParams = useSearchParams();
  const initialSymbol = searchParams.get("symbol") || "BTCUSDT.P";

  const [symbol, setSymbol] = useState(initialSymbol);
  const [timeframe, setTimeframe] = useState("15m");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredCandle, setHoveredCandle] = useState<Candle | null>(null);
  const [showEMA, setShowEMA] = useState(true);
  const [showSimulatedSignals, setShowSimulatedSignals] = useState(true);

  const fetchCandles = async (sym: string, tf: string) => {
    try {
      setLoading(true);
      const res = await api.getPairCandles(sym, tf, 80);
      setCandles(res.candles);
      setHoveredCandle(res.candles[res.candles.length - 1] || null);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandles(symbol, timeframe);
  }, [symbol, timeframe]);

  // Chart coordinate calculations
  const chartHeight = 320;
  const chartWidth = 900;
  const paddingY = 20;

  const { minPrice, maxPrice, priceRange, maxVol } = useMemo(() => {
    if (candles.length === 0)
      return { minPrice: 0, maxPrice: 1, priceRange: 1, maxVol: 1 };
    let min = Infinity;
    let max = -Infinity;
    let mv = 0;
    for (const c of candles) {
      if (c.low < min) min = c.low;
      if (c.high > max) max = c.high;
      if (c.volume > mv) mv = c.volume;
    }
    return {
      minPrice: min,
      maxPrice: max,
      priceRange: max - min || 1,
      maxVol: mv || 1,
    };
  }, [candles]);

  const candleWidth = chartWidth / (candles.length || 1);

  // EMA calculation
  const emaData = useMemo(() => {
    if (!showEMA || candles.length < 10) return [];
    const k = 2 / (21 + 1);
    let ema = candles[0].close;
    return candles.map((c) => {
      ema = c.close * k + ema * (1 - k);
      return ema;
    });
  }, [candles, showEMA]);

  return (
    <div className="space-y-4">
      {/* Top Banner: Synthetic Demo Data Warning */}
      <div className="bg-amber-950/30 border border-amber-800/60 p-3 rounded flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 text-amber-400">
          <ShieldAlert className="w-4 h-4 text-amber-500" />
          <span className="font-bold">DEMO DATA NOTICE:</span>
          <span className="text-amber-200">
            Displaying synthetic pseudo-random candles for visual UI testing. No exchange data downloaded.
          </span>
        </div>
        <div className="text-terminal-dim text-[11px]">
          LOCAL RESEARCH · NO LIVE ORDERS
        </div>
      </div>

      {/* Control Bar: Symbol selector, Timeframes, Overlays */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-wrap justify-between items-center gap-3">
        {/* Symbol Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto max-w-full">
          {TARGET_SYMBOLS.map((s) => (
            <button
              key={s}
              onClick={() => setSymbol(s)}
              className={`px-2.5 py-1 rounded text-xs font-mono transition-colors ${
                symbol === s
                  ? "bg-terminal-amber text-terminal-bg font-bold"
                  : "bg-terminal-card text-terminal-muted hover:text-terminal-text border border-terminal-border"
              }`}
            >
              {s.replace(".P", "")}
            </button>
          ))}
        </div>

        {/* Timeframe & Overlays */}
        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="flex bg-terminal-card border border-terminal-border rounded p-0.5">
            {["15m", "1H", "4H"].map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2 py-0.5 rounded text-[11px] ${
                  timeframe === tf
                    ? "bg-terminal-border text-terminal-amber font-semibold"
                    : "text-terminal-muted hover:text-terminal-text"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          <label className="flex items-center gap-1.5 cursor-pointer text-terminal-muted text-xs">
            <input
              type="checkbox"
              checked={showEMA}
              onChange={(e) => setShowEMA(e.target.checked)}
              className="accent-terminal-amber rounded"
            />
            <span>EMA(21)</span>
          </label>

          <label className="flex items-center gap-1.5 cursor-pointer text-terminal-muted text-xs">
            <input
              type="checkbox"
              checked={showSimulatedSignals}
              onChange={(e) => setShowSimulatedSignals(e.target.checked)}
              className="accent-terminal-amber rounded"
            />
            <span>Signals (Sim)</span>
          </label>

          <button
            onClick={() => fetchCandles(symbol, timeframe)}
            className="p-1 text-terminal-muted hover:text-terminal-amber border border-terminal-border rounded bg-terminal-card"
            title="Refresh Synthetic Series"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Chart Container */}
      <div className="bg-terminal-surface border border-terminal-border rounded p-4 space-y-2">
        {/* OHLCV Crosshair Header */}
        <div className="flex justify-between items-center text-xs font-mono border-b border-terminal-border pb-2">
          <div className="flex items-center gap-4">
            <span className="font-bold text-terminal-amber text-sm">
              {symbol}
            </span>
            <span className="text-terminal-dim">[{timeframe}]</span>
            {hoveredCandle && (
              <div className="flex items-center gap-3 text-terminal-muted">
                <span>
                  O:{" "}
                  <span className="text-terminal-text">
                    {hoveredCandle.open}
                  </span>
                </span>
                <span>
                  H:{" "}
                  <span className="text-terminal-text">
                    {hoveredCandle.high}
                  </span>
                </span>
                <span>
                  L:{" "}
                  <span className="text-terminal-text">
                    {hoveredCandle.low}
                  </span>
                </span>
                <span>
                  C:{" "}
                  <span
                    className={
                      hoveredCandle.close >= hoveredCandle.open
                        ? "text-terminal-positive"
                        : "text-terminal-negative"
                    }
                  >
                    {hoveredCandle.close}
                  </span>
                </span>
                <span>
                  VOL:{" "}
                  <span className="text-terminal-dim">
                    {hoveredCandle.volume.toLocaleString()}
                  </span>
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-terminal-dim">Sim Model Prob:</span>
            <span className="px-2 py-0.5 rounded bg-terminal-card border border-terminal-border text-terminal-amber font-bold">
              0.64 (Long TP)
            </span>
          </div>
        </div>

        {/* SVG Interactive Candlestick Chart */}
        <div className="relative w-full overflow-hidden bg-terminal-bg rounded border border-terminal-border">
          <svg
            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            className="w-full h-80 select-none cursor-crosshair"
            onMouseLeave={() =>
              setHoveredCandle(candles[candles.length - 1] || null)
            }
          >
            {/* Horizontal Grid lines */}
            {[0.2, 0.4, 0.6, 0.8].map((pct, idx) => {
              const y = paddingY + pct * (chartHeight - paddingY * 2);
              const p = maxPrice - pct * priceRange;
              return (
                <g key={idx}>
                  <line
                    x1="0"
                    y1={y}
                    x2={chartWidth}
                    y2={y}
                    stroke="#1E2330"
                    strokeDasharray="3,3"
                  />
                  <text
                    x={chartWidth - 45}
                    y={y - 4}
                    fill="#556073"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {p.toFixed(symbol === "XRPUSDT.P" ? 4 : 2)}
                  </text>
                </g>
              );
            })}

            {/* Candlesticks & Volume Bars */}
            {candles.map((c, i) => {
              const x = i * candleWidth + candleWidth / 2;
              const isGreen = c.close >= c.open;
              const color = isGreen ? "#10B981" : "#EF4444";

              const yHigh =
                paddingY +
                ((maxPrice - c.high) / priceRange) * (chartHeight - paddingY * 2);
              const yLow =
                paddingY +
                ((maxPrice - c.low) / priceRange) * (chartHeight - paddingY * 2);
              const yOpen =
                paddingY +
                ((maxPrice - c.open) / priceRange) * (chartHeight - paddingY * 2);
              const yClose =
                paddingY +
                ((maxPrice - c.close) / priceRange) * (chartHeight - paddingY * 2);

              const bodyTop = Math.min(yOpen, yClose);
              const bodyHeight = Math.max(Math.abs(yClose - yOpen), 1.5);

              // Volume bar in bottom 50px
              const volHeight = (c.volume / maxVol) * 45;
              const volY = chartHeight - volHeight;

              return (
                <g
                  key={c.time}
                  onMouseEnter={() => setHoveredCandle(c)}
                  className="cursor-pointer"
                >
                  {/* Volume bar */}
                  <rect
                    x={x - candleWidth * 0.4}
                    y={volY}
                    width={candleWidth * 0.8}
                    height={volHeight}
                    fill={isGreen ? "#064E3B" : "#7F1D1D"}
                    opacity="0.5"
                  />

                  {/* Wick */}
                  <line
                    x1={x}
                    y1={yHigh}
                    x2={x}
                    y2={yLow}
                    stroke={color}
                    strokeWidth="1"
                  />

                  {/* Body */}
                  <rect
                    x={x - candleWidth * 0.35}
                    y={bodyTop}
                    width={candleWidth * 0.7}
                    height={bodyHeight}
                    fill={color}
                  />

                  {/* Simulated Signals markers at periodic points */}
                  {showSimulatedSignals && i % 25 === 8 && (
                    <g>
                      <circle cx={x} cy={yLow + 12} r="4" fill="#10B981" />
                      <text
                        x={x - 10}
                        y={yLow + 24}
                        fill="#10B981"
                        fontSize="8"
                        fontFamily="monospace"
                      >
                        SIM BUY
                      </text>
                    </g>
                  )}
                  {showSimulatedSignals && i % 25 === 20 && (
                    <g>
                      <circle cx={x} cy={yHigh - 12} r="4" fill="#EF4444" />
                      <text
                        x={x - 10}
                        y={yHigh - 16}
                        fill="#EF4444"
                        fontSize="8"
                        fontFamily="monospace"
                      >
                        SIM TP
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* EMA Line overlay */}
            {showEMA && emaData.length > 0 && (
              <polyline
                fill="none"
                stroke="#F59E0B"
                strokeWidth="1.5"
                points={emaData
                  .map((val, idx) => {
                    const x = idx * candleWidth + candleWidth / 2;
                    const y =
                      paddingY +
                      ((maxPrice - val) / priceRange) *
                        (chartHeight - paddingY * 2);
                    return `${x},${y}`;
                  })
                  .join(" ")}
              />
            )}
          </svg>
        </div>

        {/* Legend */}
        <div className="flex items-center justify-between text-[11px] font-mono text-terminal-dim pt-1">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 bg-terminal-positive rounded-sm" />
              <span>Bullish Bar</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 bg-terminal-negative rounded-sm" />
              <span>Bearish Bar</span>
            </span>
            {showEMA && (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-terminal-amber" />
                <span>EMA(21) Overlay</span>
              </span>
            )}
          </div>
          <span>Showing 80 synthetic demo bars</span>
        </div>
      </div>
    </div>
  );
}

export default function PairExplorerPage() {
  return (
    <Suspense
      fallback={
        <div className="p-4 bg-terminal-surface border border-terminal-border rounded text-xs font-mono text-terminal-muted">
          Loading Pair Explorer...
        </div>
      }
    >
      <PairExplorerContent />
    </Suspense>
  );
}
