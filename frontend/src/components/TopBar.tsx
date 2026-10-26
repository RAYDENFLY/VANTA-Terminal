"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { HealthData, SystemStatusData } from "@/lib/types";
import { Activity, ShieldAlert, Cpu, Database, RefreshCw } from "lucide-react";

export function TopBar() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [system, setSystem] = useState<SystemStatusData | null>(null);
  const [connected, setConnected] = useState<boolean>(false);
  const [lastCheck, setLastCheck] = useState<string>("");

  const checkTelemetry = async () => {
    try {
      const [hData, sData] = await Promise.all([
        api.getHealth(),
        api.getSystemStatus(),
      ]);
      setHealth(hData);
      setSystem(sData);
      setConnected(true);
      setLastCheck(new Date().toLocaleTimeString());
    } catch {
      setConnected(false);
    }
  };

  useEffect(() => {
    checkTelemetry();
    // Poll every 10 seconds only
    const interval = setInterval(checkTelemetry, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-10 bg-terminal-surface border-b border-terminal-border px-4 flex items-center justify-between text-xs select-none sticky top-0 z-50">
      {/* Left: Branding & Strict Safety Watermark */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 font-bold tracking-wider text-terminal-amber font-mono">
          <div className="w-2.5 h-2.5 bg-terminal-amber rounded-sm animate-pulse" />
          <span>VANTA // TERMINAL</span>
        </div>

        <div className="h-3.5 w-[1px] bg-terminal-border" />

        {/* Persistent Safety Notice */}
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-terminal-card border border-terminal-borderLight font-mono font-medium text-amber-400">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
          <span>LOCAL RESEARCH · NO LIVE ORDERS</span>
        </div>

        {/* Demo Data Watermark */}
        <div className="px-2 py-0.5 rounded bg-terminal-sub border border-terminal-border text-[10px] font-mono text-terminal-muted">
          DEMO FIXTURES ACTIVE
        </div>
      </div>

      {/* Right: Telemetry & Port Health */}
      <div className="flex items-center gap-4 text-terminal-muted font-mono">
        {/* Backend Heartbeat */}
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-terminal-positive" : "bg-terminal-negative"
            }`}
          />
          <span className="text-[11px]">
            API: {connected ? "CONNECTED (8101)" : "DISCONNECTED"}
          </span>
        </div>

        <div className="h-3 w-[1px] bg-terminal-border" />

        {/* Worker State */}
        <div className="flex items-center gap-1">
          <Activity className="w-3.5 h-3.5 text-terminal-dim" />
          <span className="text-[11px]">
            WORKER:{" "}
            <span className="text-terminal-text font-semibold">
              {system?.worker_status || "IDLE"}
            </span>
          </span>
        </div>

        <div className="h-3 w-[1px] bg-terminal-border" />

        {/* Memory Telemetry */}
        <div className="flex items-center gap-1">
          <Cpu className="w-3.5 h-3.5 text-terminal-dim" />
          <span className="text-[11px]">
            RAM FREE:{" "}
            <span className="text-terminal-amber font-medium">
              {system?.resources?.memory?.available_ram_gb != null
                ? `${system.resources.memory.available_ram_gb} GB`
                : "3.50 GB (EST)"}
            </span>
          </span>
        </div>

        <div className="h-3 w-[1px] bg-terminal-border" />

        {/* Disk D */}
        <div className="flex items-center gap-1">
          <Database className="w-3.5 h-3.5 text-terminal-dim" />
          <span className="text-[11px]">
            HDD D:{" "}
            <span className="text-terminal-text">
              {system?.resources?.disk_d?.free_gb != null
                ? `${system.resources.disk_d.free_gb} GB`
                : "64.9 GB"}
            </span>
          </span>
        </div>

        <div className="h-3 w-[1px] bg-terminal-border" />

        <button
          onClick={checkTelemetry}
          title="Refresh Telemetry"
          className="p-1 hover:text-terminal-amber transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
        </button>
      </div>
    </header>
  );
}
