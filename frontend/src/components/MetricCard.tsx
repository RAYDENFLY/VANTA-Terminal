import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: "up" | "down" | "neutral";
  isDemo?: boolean;
}

export function MetricCard({
  label,
  value,
  subtext,
  trend,
  isDemo = true,
}: MetricCardProps) {
  return (
    <div className="bg-terminal-card border border-terminal-border p-3 rounded flex flex-col justify-between">
      <div className="flex items-center justify-between text-[10px] font-mono text-terminal-muted uppercase tracking-wider mb-1">
        <span>{label}</span>
        {isDemo && (
          <span className="text-[8px] px-1 py-0.2 bg-terminal-sub border border-terminal-border text-terminal-dim rounded">
            DEMO
          </span>
        )}
      </div>
      <div className="text-xl font-bold font-mono text-terminal-text tracking-tight my-0.5">
        {value}
      </div>
      {subtext && (
        <div
          className={`text-[10px] font-mono mt-0.5 ${
            trend === "up"
              ? "text-terminal-positive"
              : trend === "down"
              ? "text-terminal-negative"
              : "text-terminal-dim"
          }`}
        >
          {subtext}
        </div>
      )}
    </div>
  );
}
