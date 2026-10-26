import React from "react";

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const norm = (status || "").toUpperCase();

  let bgClass = "bg-terminal-sub text-terminal-muted border-terminal-border";

  if (norm === "COMPLETED" || norm === "NOMINAL" || norm === "FROZEN" || norm === "OK") {
    bgClass = "bg-emerald-950/60 text-emerald-400 border-emerald-800/60";
  } else if (norm === "PENDING" || norm === "PENDING_AUDIT" || norm === "QUEUED" || norm === "RUNNING") {
    bgClass = "bg-amber-950/60 text-amber-400 border-amber-800/60";
  } else if (norm === "FAILED" || norm === "REJECTED" || norm === "ERROR" || norm === "WARNING") {
    bgClass = "bg-rose-950/60 text-rose-400 border-rose-800/60";
  } else if (norm === "NOT TESTED" || norm === "NOT_EVALUATED") {
    bgClass = "bg-slate-900 text-slate-400 border-slate-800";
  } else if (norm === "CANDIDATE") {
    bgClass = "bg-sky-950/60 text-sky-400 border-sky-800/60";
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium border ${bgClass}`}
    >
      {status}
    </span>
  );
}
