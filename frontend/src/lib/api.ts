import {
  HealthData,
  SystemStatusData,
  PairsListResponse,
  PairCandlesResponse,
  ExperimentsResponse,
  DataCoverageResponse,
  StrategyLabResponse,
  ModelArenaResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8101";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
      cache: "no-store",
    });

    if (!res.ok) {
      throw new Error(`API Error ${res.status}: ${res.statusText} at ${path}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Failed to fetch ${url}:`, err.message);
    throw err;
  }
}

export const api = {
  getHealth: () => fetchJson<HealthData>("/api/health"),
  getSystemStatus: () => fetchJson<SystemStatusData>("/api/system/status"),
  getSystemResources: () => fetchJson<{ telemetry: any }>("/api/system/resources"),
  getPairs: () => fetchJson<PairsListResponse>("/api/pairs"),
  getPairCandles: (symbol: string, timeframe = "15m", count = 120) =>
    fetchJson<PairCandlesResponse>(`/api/pairs/${encodeURIComponent(symbol)}/candles?timeframe=${timeframe}&count=${count}`),
  getExperiments: (status?: string) =>
    fetchJson<ExperimentsResponse>(`/api/experiments${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  getDataCoverage: () => fetchJson<DataCoverageResponse>("/api/data/coverage"),
  getStrategies: () => fetchJson<StrategyLabResponse>("/api/strategies"),
  freezeStrategy: (strategyId: string) =>
    fetchJson<{ status: string; strategy_id: string; message: string }>("/api/strategies/freeze", {
      method: "POST",
      body: JSON.stringify({ strategy_id: strategyId }),
    }),
  getModels: () => fetchJson<ModelArenaResponse>("/api/models"),
};
