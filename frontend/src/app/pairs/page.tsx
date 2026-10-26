"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { PairItem } from "@/lib/types";
import { Search, ArrowUpDown, ExternalLink, Filter, AlertTriangle } from "lucide-react";

export default function PairMonitorPage() {
  const [pairs, setPairs] = useState<PairItem[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [sortField, setSortField] = useState<"symbol" | "missing_bars">("symbol");
  const [sortAsc, setSortAsc] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadPairs() {
      try {
        setLoading(true);
        const data = await api.getPairs();
        setPairs(data.pairs);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadPairs();
  }, []);

  const filteredPairs = pairs
    .filter((p) => {
      const matchesSearch =
        p.symbol.toLowerCase().includes(search.toLowerCase()) ||
        p.base_asset.toLowerCase().includes(search.toLowerCase());
      const matchesStatus =
        statusFilter === "ALL" || p.coverage_status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      if (sortField === "symbol") {
        return sortAsc
          ? a.symbol.localeCompare(b.symbol)
          : b.symbol.localeCompare(a.symbol);
      } else {
        return sortAsc
          ? a.missing_bars - b.missing_bars
          : b.missing_bars - a.missing_bars;
      }
    });

  const toggleSort = (field: "symbol" | "missing_bars") => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header and Filter Controls */}
      <div className="bg-terminal-surface border border-terminal-border p-3 rounded flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-terminal-amber text-sm font-mono">
              PAIR MONITOR // 11 TARGET CRYPTO-FUTURES
            </span>
            <span className="text-[10px] bg-terminal-sub px-2 py-0.5 rounded text-terminal-muted border border-terminal-border">
              DEMO STATUS
            </span>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5">
            Full universe audit pending Phase 2 data inspection. Coverage and models default to PENDING / NOT TESTED.
          </p>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-48">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-terminal-dim" />
            <input
              type="text"
              placeholder="Search symbol..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-terminal-card border border-terminal-border text-terminal-text rounded pl-8 pr-2 py-1 text-xs font-mono placeholder-terminal-dim focus:outline-none focus:border-terminal-amber"
            />
          </div>

          <div className="flex items-center gap-1 bg-terminal-card border border-terminal-border rounded px-2 py-1 text-xs">
            <Filter className="w-3 h-3 text-terminal-dim" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent text-terminal-muted focus:outline-none text-xs font-mono"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending Audit</option>
              <option value="NOT TESTED">Not Tested</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-terminal-surface border border-terminal-border rounded overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left table-dense">
            <thead>
              <tr>
                <th
                  onClick={() => toggleSort("symbol")}
                  className="cursor-pointer hover:text-terminal-amber"
                >
                  <div className="flex items-center gap-1">
                    <span>Symbol</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th>Base / Quote</th>
                <th>Contract</th>
                <th>Timeframes</th>
                <th>Data Coverage</th>
                <th>Last Timestamp</th>
                <th
                  onClick={() => toggleSort("missing_bars")}
                  className="cursor-pointer hover:text-terminal-amber"
                >
                  <div className="flex items-center gap-1">
                    <span>Missing Gaps</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th>Model Arena</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border/50 font-mono text-xs">
              {filteredPairs.map((p) => (
                <tr key={p.symbol} className="hover:bg-terminal-card">
                  <td className="font-bold text-terminal-text flex items-center gap-2">
                    <span>{p.symbol}</span>
                  </td>
                  <td className="text-terminal-muted">
                    {p.base_asset} / {p.quote_asset}
                  </td>
                  <td className="text-terminal-dim">{p.contract_type}</td>
                  <td className="text-terminal-muted">15m, 1H, 4H</td>
                  <td>
                    <StatusBadge status={p.coverage_status} />
                  </td>
                  <td className="text-terminal-dim">
                    {p.last_candle_time || "— (Awaiting Download)"}
                  </td>
                  <td>
                    {p.missing_bars === 0 ? (
                      <span className="text-terminal-dim">0 Bars</span>
                    ) : (
                      <span className="text-amber-400 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        <span>{p.missing_bars} Bars</span>
                      </span>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={p.model_status} />
                  </td>
                  <td className="text-right">
                    <Link
                      href={`/explorer?symbol=${encodeURIComponent(p.symbol)}`}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-terminal-card hover:bg-terminal-border text-terminal-amber text-[11px] font-mono border border-terminal-border"
                    >
                      <span>Explore</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-2.5 bg-terminal-card/40 border-t border-terminal-border flex justify-between items-center text-xs font-mono text-terminal-dim px-4">
          <span>
            Total Universe: {filteredPairs.length} of {pairs.length} pairs
          </span>
          <span className="text-amber-500/80">
            Note: Historical depth cannot be claimed until audited in Phase 2
          </span>
        </div>
      </div>
    </div>
  );
}
