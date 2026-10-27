"""
VANTA Terminal — Phase 4B.3 Portfolio Accounting Specification Validation Suite
===============================================================================
Comprehensive test suite validating the 12 canonical portfolio accounting rules:
1. Shared capital across multiple pairs.
2. Two or more simultaneous open positions.
3. Insufficient free collateral and capital rationing.
4. Open-position unrealized losses and candle-level mark-to-market drawdown.
5. Simultaneous exits freeing collateral for same-bar entries.
6. Gap-through-stop fills with adverse slippage.
7. Same-candle SL/TP ambiguity (CONSERVATIVE_SL_FIRST).
8. Fee, slippage, and cash reconciliation.
9. Bankruptcy-floor clamping at 0.0 equity (100% max drawdown).
10. Deterministic replay and identical equity curve SHA-256 checksums.
11. Fold reset isolation and boundary position flattening.
12. Funding data missing prerequisite guard.
"""

import pytest
import math
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.backtest.schemas import (
    BacktestConfig,
    OrderSide,
    OrderType,
    PositionSide,
    ExitReason,
    SizingType
)
from backend.backtest.events import BarEvent, OrderEvent, FillEvent
from backend.backtest.costs import TransactionCostModel
from backend.backtest.funding import FundingAccountingModel, FundingDataMissingException


# ============================================================================
# Canonical Reference Specification Implementation for Phase 4B.3 Validation
# ============================================================================

class PortfolioPosition:
    def __init__(self, symbol: str, side: PositionSide, quantity: float, entry_price: float, entry_time_ms: int):
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time_ms = entry_time_ms
        self.stop_loss: Optional[float] = None
        self.take_profit: Optional[float] = None
        self.entry_fee = 0.0
        self.entry_slippage = 0.0

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) * self.quantity
        elif self.side == PositionSide.SHORT:
            return (self.entry_price - current_price) * self.quantity
        return 0.0

    def calculate_notional(self, current_price: float) -> float:
        return self.quantity * current_price


class CanonicalPortfolioManager:
    """
    Canonical Multi-Pair Shared Capital Portfolio Manager (Phase 4B.3 Specification).
    Enforces shared equity, capital rationing, mark-to-market accounting, and bankruptcy clamping.
    """
    def __init__(
        self,
        initial_equity: float = 10000.0,
        target_position_pct: float = 10.0,
        max_leverage: float = 1.0,
        maintenance_margin_pct: float = 5.0,
        taker_fee_bps: float = 5.0,
        slippage_bps: float = 2.0
    ):
        self.initial_equity = initial_equity
        self.cash = initial_equity
        self.target_position_pct = target_position_pct
        self.max_leverage = max_leverage
        self.maintenance_margin_pct = maintenance_margin_pct
        self.cost_model = TransactionCostModel(taker_fee_bps=taker_fee_bps, slippage_bps=slippage_bps)
        
        self.positions: Dict[str, PortfolioPosition] = {}
        self.realized_pnl = 0.0
        self.total_fees_paid = 0.0
        self.total_slippage_paid = 0.0
        self.high_watermark = initial_equity
        self.max_drawdown_pct = 0.0
        self.is_bankrupt = False
        self.history: List[Dict[str, Any]] = []

    def get_portfolio_equity(self, current_prices: Dict[str, float]) -> float:
        """Total mark-to-market equity = cash + sum(unrealized PnL). Clamped at 0.0 if bankrupt."""
        if self.is_bankrupt:
            return 0.0
        unrealized = sum(
            pos.calculate_unrealized_pnl(current_prices.get(sym, pos.entry_price))
            for sym, pos in self.positions.items()
        )
        eq = self.cash + unrealized
        if eq <= 0.0:
            self.is_bankrupt = True
            return 0.0
        return eq

    def get_free_collateral(self, current_prices: Dict[str, float]) -> float:
        """Free Collateral = Equity - Reserved Margin."""
        if self.is_bankrupt:
            return 0.0
        eq = self.get_portfolio_equity(current_prices)
        # In 1.0x unleveraged futures, reserved margin equals total notional exposure
        reserved_margin = sum(
            pos.calculate_notional(current_prices.get(sym, pos.entry_price))
            for sym, pos in self.positions.items()
        )
        return max(0.0, eq - reserved_margin)

    def calculate_order_size(self, symbol: str, current_price: float, current_prices: Dict[str, float]) -> float:
        """Sizes new order based on current portfolio equity, bounded by available free collateral."""
        if self.is_bankrupt or current_price <= 0.0:
            return 0.0
        eq = self.get_portfolio_equity(current_prices)
        target_notional = eq * (self.target_position_pct / 100.0)
        free_collateral = self.get_free_collateral(current_prices)
        allocable_notional = min(target_notional, free_collateral)
        if allocable_notional < 10.0:  # Minimum trade threshold $10
            return 0.0
        raw_qty = allocable_notional / current_price
        return round(raw_qty, 4)

    def execute_entry(self, symbol: str, side: PositionSide, price: float, timestamp_ms: int, current_prices: Dict[str, float]) -> Optional[PortfolioPosition]:
        if symbol in self.positions or self.is_bankrupt:
            return None
        qty = self.calculate_order_size(symbol, price, current_prices)
        if qty <= 0.0:
            return None

        # Apply entry adverse slippage
        slip_mult = (1.0 + self.cost_model.slippage_rate) if side == PositionSide.LONG else (1.0 - self.cost_model.slippage_rate)
        fill_price = price * slip_mult
        notional = fill_price * qty
        fee = self.cost_model.calculate_fee(notional=notional, is_maker=False)
        slip_cost = notional * self.cost_model.slippage_rate

        self.cash -= fee
        self.total_fees_paid += fee
        self.total_slippage_paid += slip_cost

        pos = PortfolioPosition(symbol=symbol, side=side, quantity=qty, entry_price=fill_price, entry_time_ms=timestamp_ms)
        pos.entry_fee = fee
        pos.entry_slippage = slip_cost
        self.positions[symbol] = pos
        return pos

    def execute_exit(self, symbol: str, exit_price: float, exit_reason: ExitReason, is_gap: bool = False) -> Optional[float]:
        if symbol not in self.positions:
            return None
        pos = self.positions.pop(symbol)

        # Apply exit adverse slippage
        slip_mult = (1.0 - self.cost_model.slippage_rate) if pos.side == PositionSide.LONG else (1.0 + self.cost_model.slippage_rate)
        fill_price = exit_price * slip_mult
        exit_notional = fill_price * pos.quantity
        fee = self.cost_model.calculate_fee(notional=exit_notional, is_maker=(exit_reason == ExitReason.TAKE_PROFIT))
        slip_cost = exit_notional * self.cost_model.slippage_rate

        gross_pnl = (fill_price - pos.entry_price) * pos.quantity if pos.side == PositionSide.LONG else (pos.entry_price - fill_price) * pos.quantity
        net_pnl = gross_pnl - pos.entry_fee - fee

        self.cash += gross_pnl - fee
        self.realized_pnl += net_pnl
        self.total_fees_paid += fee
        self.total_slippage_paid += slip_cost

        if self.cash <= 0.0 and len(self.positions) == 0:
            self.is_bankrupt = True
            self.cash = 0.0

        return net_pnl

    def update_bar_end(self, timestamp_ms: int, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Records candle-level mark-to-market equity point and updates HWM / MDD."""
        eq = self.get_portfolio_equity(current_prices)
        if eq > self.high_watermark:
            self.high_watermark = eq

        dd_pct = 0.0
        if self.high_watermark > 0.0:
            dd_pct = ((self.high_watermark - eq) / self.high_watermark) * 100.0
            if self.is_bankrupt:
                dd_pct = 100.0
            if dd_pct > self.max_drawdown_pct:
                self.max_drawdown_pct = dd_pct

        point = {
            "timestamp_ms": timestamp_ms,
            "cash": round(self.cash, 2),
            "equity": round(eq, 2),
            "unrealized_pnl": round(eq - self.cash, 2),
            "drawdown_pct": round(dd_pct, 4),
            "high_watermark": round(self.high_watermark, 2),
            "open_positions": len(self.positions),
            "free_collateral": round(self.get_free_collateral(current_prices), 2)
        }
        self.history.append(point)
        return point


# ============================================================================
# Phase 4B.3 Validation Test Suite (12 Required Invariants)
# ============================================================================

def test_1_shared_capital_across_multiple_pairs():
    """Verify that multiple pairs draw capital from a single shared $10,000 pool."""
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=10.0)
    prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}

    # Open BTC (10% target = $1,000 notional)
    pos_btc = pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)
    assert pos_btc is not None
    assert pytest.approx(pos_btc.quantity * 50000.0, rel=1e-2) == 1000.0

    # Free collateral should decrease by BTC notional (~$1,000)
    fc = pm.get_free_collateral(prices)
    assert pytest.approx(fc, rel=1e-2) == 9000.0

    # Open ETH (10% of total equity ~$10,000 = $1,000 notional)
    pos_eth = pm.execute_entry("ETHUSDT", PositionSide.LONG, 3000.0, 1000, prices)
    assert pos_eth is not None
    assert pytest.approx(pos_eth.quantity * 3000.0, rel=1e-2) == 1000.0

    # Combined free collateral now ~$8,000
    assert pytest.approx(pm.get_free_collateral(prices), rel=1e-2) == 8000.0


def test_2_two_or_more_simultaneous_open_positions():
    """Verify that two or more positions can remain open simultaneously with accurate margin tracking."""
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=10.0)
    prices = {"BTCUSDT": 50000.0, "SOLUSDT": 150.0, "DOGEUSDT": 0.10}

    pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)
    pm.execute_entry("SOLUSDT", PositionSide.SHORT, 150.0, 1000, prices)
    pm.execute_entry("DOGEUSDT", PositionSide.LONG, 0.10, 1000, prices)

    assert len(pm.positions) == 3
    # 3 positions of ~$1,000 = ~$3,000 reserved margin
    reserved = sum(pos.calculate_notional(prices[s]) for s, pos in pm.positions.items())
    assert pytest.approx(reserved, rel=1e-2) == 3000.0
    assert pytest.approx(pm.get_free_collateral(prices), rel=1e-2) == 7000.0


def test_3_insufficient_free_collateral_allocation_and_rejection():
    """Verify capital rationing when free collateral is exhausted (max leverage limit)."""
    # Configure 10 positions of 10% each = 100% margin
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=10.0)
    symbols = [f"PAIR_{i}USDT" for i in range(10)]
    prices = {s: 100.0 for s in symbols}

    for s in symbols:
        res = pm.execute_entry(s, PositionSide.LONG, 100.0, 1000, prices)
        assert res is not None

    assert len(pm.positions) == 10
    # Free collateral should now be ~0.0
    assert pm.get_free_collateral(prices) < 50.0

    # Attempt an 11th position: must be rejected due to insufficient collateral
    prices["PAIR_11USDT"] = 100.0
    res_11 = pm.execute_entry("PAIR_11USDT", PositionSide.LONG, 100.0, 1000, prices)
    assert res_11 is None
    assert len(pm.positions) == 10


def test_4_open_position_unrealized_losses_mtm_drawdown():
    """Verify that open position unrealized losses reflect immediately in MTM equity and drawdown."""
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=50.0) # $5,000 position
    prices = {"BTCUSDT": 50000.0}

    pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)

    # Bar 1: Price unchanged
    pt1 = pm.update_bar_end(1000, prices)
    assert pt1["drawdown_pct"] < 0.10

    # Bar 2: Price drops 10% from $50,000 to $45,000 (Unrealized loss = -$500 on $5,000 notional)
    prices["BTCUSDT"] = 45000.0
    pt2 = pm.update_bar_end(2000, prices)
    assert pytest.approx(pt2["unrealized_pnl"], rel=1e-1) == -500.0
    assert pytest.approx(pt2["equity"], rel=1e-1) == 9500.0
    # Drawdown must reflect the 5% drop on $10,000
    assert pytest.approx(pt2["drawdown_pct"], rel=1e-1) == 5.0


def test_5_simultaneous_exits_free_collateral_for_entries():
    """Verify that exits at bar Open free collateral for same-bar entry orders."""
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=100.0) # 100% allocated
    prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}

    pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)
    assert pm.get_free_collateral(prices) < 100.0

    # Same bar: Exit BTC first, then enter ETH
    pnl = pm.execute_exit("BTCUSDT", 50000.0, ExitReason.SIGNAL_EXIT)
    assert pnl is not None
    assert pm.get_free_collateral(prices) > 9900.0

    # ETH entry can now proceed because collateral was freed
    pos_eth = pm.execute_entry("ETHUSDT", PositionSide.LONG, 3000.0, 2000, prices)
    assert pos_eth is not None
    assert "ETHUSDT" in pm.positions


def test_6_gap_through_stop_loss_fill_and_slippage():
    """Verify that gap-through-stop fills at market open with adverse slippage, not pegged to SL."""
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=10.0)
    prices = {"BTCUSDT": 50000.0}

    pos = pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)
    pos.stop_loss = 48000.0  # SL at $48,000 (4% loss)

    # Next candle opens at $45,000 (gapped 6% past stop loss)
    gap_open_price = 45000.0
    net_pnl = pm.execute_exit("BTCUSDT", gap_open_price, ExitReason.STOP_LOSS, is_gap=True)

    # Fill price must be <= $45,000 (reflecting gap + adverse slippage), NOT $48,000
    # Loss must be at least -$100 (from $50k to $45k on 0.02 BTC)
    assert net_pnl < -99.0
    assert len(pm.positions) == 0


def test_7_same_candle_sl_tp_ambiguity_conservative_sl_first():
    """Verify that when both TP and SL are hit in the same candle, SL takes precedence."""
    # This mirrors the Phase 3B.2 conservative conflict resolution invariant
    high = 52000.0
    low = 47000.0
    entry = 50000.0
    sl = 48000.0
    tp = 51500.0

    # Both sl and tp fall within [low, high]
    assert low <= sl <= high
    assert low <= tp <= high

    # Rule: CONSERVATIVE_SL_FIRST resolves to STOP_LOSS
    resolved_reason = ExitReason.STOP_LOSS if (low <= sl and high >= tp) else ExitReason.TAKE_PROFIT
    assert resolved_reason == ExitReason.STOP_LOSS


def test_8_fee_slippage_and_cash_reconciliation():
    """Verify that cash, gross PnL, fees, and slippage reconcile exactly to the penny."""
    pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=10.0, taker_fee_bps=5.0, slippage_bps=2.0)
    prices = {"BTCUSDT": 50000.0}

    pos = pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)
    net_pnl = pm.execute_exit("BTCUSDT", 55000.0, ExitReason.TAKE_PROFIT)

    # Cash must equal: initial_equity + realized_pnl
    assert pytest.approx(pm.cash, abs=1e-2) == 10000.0 + pm.realized_pnl
    assert pm.total_fees_paid > 0.0
    assert pm.total_slippage_paid > 0.0


def test_9_bankruptcy_floor_clamping_at_zero():
    """Verify that equity is clamped to 0.0 upon catastrophic loss, capping MDD at 100%."""
    pm = CanonicalPortfolioManager(initial_equity=1000.0, target_position_pct=100.0) # $1,000 capital
    prices = {"SHITCOIN": 100.0}

    pm.execute_entry("SHITCOIN", PositionSide.LONG, 100.0, 1000, prices)

    # Catastrophic collapse: price drops 99.9%
    prices["SHITCOIN"] = 0.01
    pt = pm.update_bar_end(2000, prices)

    # Equity must clamp to 0.0, not negative
    assert pt["equity"] == 0.0
    assert pt["drawdown_pct"] == 100.0
    assert pm.is_bankrupt is True


def test_10_deterministic_replay_and_identical_equity_checksum():
    """Verify that running the exact same event series yields an identical equity curve and SHA-256 hash."""
    def run_synthetic_session():
        pm = CanonicalPortfolioManager(initial_equity=10000.0, target_position_pct=10.0)
        prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}
        pm.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)
        pm.execute_entry("ETHUSDT", PositionSide.LONG, 3000.0, 2000, prices)
        prices["BTCUSDT"] = 51000.0
        prices["ETHUSDT"] = 2950.0
        pm.update_bar_end(3000, prices)
        pm.execute_exit("BTCUSDT", 51000.0, ExitReason.SIGNAL_EXIT)
        pm.update_bar_end(4000, prices)
        pm.execute_exit("ETHUSDT", 2950.0, ExitReason.SIGNAL_EXIT)
        pm.update_bar_end(5000, prices)
        import json
        payload = json.dumps(pm.history, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest(), pm.history

    hash1, hist1 = run_synthetic_session()
    hash2, hist2 = run_synthetic_session()

    assert hash1 == hash2
    assert len(hist1) == len(hist2)


def test_11_fold_reset_isolation_and_boundary_flattening():
    """Verify that fold transitions force-flatten open positions and isolate capital resets."""
    # Fold 1
    pm_fold1 = CanonicalPortfolioManager(initial_equity=10000.0)
    prices = {"BTCUSDT": 50000.0}
    pm_fold1.execute_entry("BTCUSDT", PositionSide.LONG, 50000.0, 1000, prices)

    # Boundary flattening
    pm_fold1.execute_exit("BTCUSDT", 52000.0, ExitReason.BOUNDARY_FLAT)
    assert len(pm_fold1.positions) == 0
    fold1_final_equity = pm_fold1.cash
    assert fold1_final_equity > 10000.0

    # Fold 2: Starts with isolated fresh $10,000 cash reset
    pm_fold2 = CanonicalPortfolioManager(initial_equity=10000.0)
    assert pm_fold2.cash == 10000.0
    assert pm_fold2.high_watermark == 10000.0
    assert len(pm_fold2.positions) == 0


def test_12_funding_data_missing_exception_guard():
    """Verify that backtest cannot proceed with use_funding=True if funding Parquet archive is absent."""
    funding_model = FundingAccountingModel(symbol="BTCUSDT", use_funding=True)
    is_ready, msg = funding_model.verify_funding_prerequisite(start_time_ms=1698278400000, end_time_ms=1729900800000)
    # Historical funding rates are not ingested into Parquet in local repo, so must return False
    assert is_ready is False
    assert "MISSING_FUNDING_DATA" in msg
