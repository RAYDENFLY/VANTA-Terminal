"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Coins,
  LineChart,
  FlaskConical,
  Swords,
  ScrollText,
  HardDriveDownload,
  ServerCog,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { name: "Terminal Overview", href: "/", icon: LayoutDashboard },
  { name: "Pair Monitor", href: "/pairs", icon: Coins, badge: "11 PAIRS" },
  { name: "Pair Explorer", href: "/explorer", icon: LineChart },
  { name: "Strategy Lab", href: "/strategies", icon: FlaskConical },
  { name: "Model Arena", href: "/models", icon: Swords, badge: "PRE-ML" },
  { name: "Experiment Center", href: "/experiments", icon: ScrollText },
  { name: "Data Center", href: "/data", icon: HardDriveDownload },
  { name: "System Monitor", href: "/system", icon: ServerCog },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <aside className="w-56 bg-terminal-surface border-r border-terminal-border flex flex-col justify-between select-none text-xs flex-shrink-0">
      <div>
        {/* Navigation Category Label */}
        <div className="px-3 pt-3 pb-2 text-[10px] font-mono font-semibold tracking-wider text-terminal-dim uppercase">
          Workstation Navigation
        </div>

        {/* Links */}
        <nav className="space-y-0.5 px-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-2.5 py-2 rounded font-mono text-[11px] transition-all ${
                  isActive
                    ? "bg-terminal-card text-terminal-amber font-semibold border-l-2 border-terminal-amber pl-2"
                    : "text-terminal-muted hover:text-terminal-text hover:bg-terminal-card/50"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-3.5 h-3.5 ${
                      isActive ? "text-terminal-amber" : "text-terminal-dim"
                    }`}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={`text-[9px] px-1 py-0.2 rounded font-semibold ${
                      isActive
                        ? "bg-terminal-amber/20 text-terminal-amber"
                        : "bg-terminal-sub text-terminal-dim"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Persistent Terminal Footer Info */}
      <div className="p-3 border-t border-terminal-border space-y-2 text-[10px] font-mono text-terminal-dim">
        <div className="flex justify-between items-center">
          <span>VANTA BUILD</span>
          <span className="text-terminal-muted">v0.1.0-P1</span>
        </div>
        <div className="flex justify-between items-center">
          <span>PORT 8000</span>
          <span className="text-terminal-amber font-bold">FORBIDDEN</span>
        </div>
        <div className="flex justify-between items-center">
          <span>ACTIVE WORKERS</span>
          <span className="text-terminal-muted">1 (MAX)</span>
        </div>
        <div className="p-1.5 rounded bg-terminal-card border border-terminal-border text-center text-terminal-muted text-[9px]">
          AIR-GAPPED SIMULATOR
        </div>
      </div>
    </aside>
  );
}
