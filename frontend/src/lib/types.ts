export interface HealthData {
  status: string;
  version: string;
  environment: string;
  live_orders_enabled: boolean;
  is_demo_data: boolean;
  active_worker: boolean;
  timestamp: string;
}

export interface ResourceTelemetry {
  memory: {
    total_ram_gb: number | null;
    available_ram_gb: number | null;
    used_ram_gb: number | null;
    memory_load_percent: number | null;
    status: string;
  };
  disk_d: {
    drive: string;
    total_gb: number | null;
    used_gb: number | null;
    free_gb: number | null;
    percent_free: number | null;
    status: string;
  };
  disk_c: {
    drive: string;
    total_gb: number | null;
    used_gb: number | null;
    free_gb: number | null;
    percent_free: number | null;
    status: string;
  };
  cpu: {
    logical_cores: number;
    physical_cores: number;
    architecture: string;
    processor_identifier: string;
  };
  worker_concurrency_cap: number;
}

export interface SystemStatusData {
  project_name: string;
  version: string;
  host: string;
  port: number;
  loopback_only: boolean;
  forbidden_port_8000_safe: boolean;
  live_orders_disabled: boolean;
  status: string;
  worker_status: string;
  uptime_seconds: number;
  resources: ResourceTelemetry;
  demo_mode: boolean;
}

export interface PairItem {
  symbol: string;
  base_asset: string;
  quote_asset: string;
  contract_type: string;
  timeframes: string[];
  coverage_status: string;
  model_status: string;
  last_candle_time: string | null;
  historical_depth_days: number;
  missing_bars: number;
  is_demo_data: boolean;
}

export interface PairsListResponse {
  universe_size: number;
  pairs: PairItem[];
  is_demo_data: boolean;
  audit_required: boolean;
}

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PairCandlesResponse {
  symbol: string;
  timeframe: string;
  is_demo_data: boolean;
  notice: string;
  candles: Candle[];
}

export interface ExperimentRecord {
  run_id: string;
  config_hash: string;
  dataset_version: string;
  strategy_family: string;
  model_architecture: string;
  status: string;
  created_at: string;
  runtime_seconds: number | null;
  peak_memory_mb: number | null;
  sample_size_trades: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate_pct: number | null;
  brier_score: number | null;
  is_demo_data: boolean;
  notes: string;
}

export interface ExperimentsResponse {
  total_count: number;
  active_run: ExperimentRecord | null;
  experiments: ExperimentRecord[];
  is_demo_data: boolean;
  storage_engine: string;
}

export interface TimeframeCoverage {
  timeframe: string;
  available_bars: number;
  earliest_candle: string | null;
  latest_candle: string | null;
  gap_count: number;
  coverage_pct: number;
  status: string;
}

export interface PairCoverageSummary {
  symbol: string;
  target_history_years: number;
  verified_history_years: number;
  audit_status: string;
  timeframes: Record<string, TimeframeCoverage>;
  raw_storage_mb: number;
  manifest_checksum: string | null;
  is_demo_data: boolean;
}

export interface DataCoverageResponse {
  total_pairs: number;
  verified_pairs: number;
  pending_audit_pairs: number;
  total_raw_storage_mb: number;
  disk_free_gb: number;
  coverage: PairCoverageSummary[];
  is_demo_data: boolean;
  notice: string;
}

export interface StrategyCandidate {
  id: string;
  name: string;
  family: string;
  description: string;
  status: string;
  entry_logic: string;
  stop_loss_logic: string;
  take_profit_logic: string;
  trades_count: number;
  win_rate_pct: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  expectancy_r: number;
  avg_holding_bars: number;
  is_demo_data: boolean;
}

export interface StrategyLabResponse {
  frozen_strategy_id: string | null;
  cost_framework: {
    maker_fee_pct: number;
    taker_fee_pct: number;
    base_slippage_bps: number;
    funding_accrual_hours: number;
    same_bar_ambiguity: string;
  };
  candidates: StrategyCandidate[];
  qualification_criteria: Record<string, any>;
  is_demo_data: boolean;
  notice: string;
}

export interface ModelConfigResult {
  config_id: string;
  name: string;
  architecture: string;
  description: string;
  training_scope: string;
  features_count: number;
  val_brier_score: number;
  val_roc_auc: number;
  val_sharpe: number;
  val_max_drawdown_pct: number;
  val_win_rate_pct: number;
  sample_size_trades: number;
  bootstrap_sharpe_ci95: number[];
  status: string;
  is_demo_data: boolean;
}

export interface ModelArenaResponse {
  frozen_strategy_reference: string | null;
  target_definition: string;
  configurations: ModelConfigResult[];
  oos_unlocked: boolean;
  is_demo_data: boolean;
  notice: string;
}
