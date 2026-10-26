import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["terminal"] == "VANTA Terminal"
    assert data["mode"] == "LOCAL RESEARCH · NO LIVE ORDERS"
    assert response.headers.get("X-Terminal-Mode") == "LOCAL RESEARCH - NO LIVE ORDERS"

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["live_orders_enabled"] is False
    assert data["is_demo_data"] is True

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["loopback_only"] is True
    assert data["forbidden_port_8000_safe"] is True
    assert "resources" in data
    assert "memory" in data["resources"]

def test_system_resources():
    response = client.get("/api/system/resources")
    assert response.status_code == 200
    data = response.json()
    assert "telemetry" in data
    assert data["measured_live"] is True

def test_pairs_universe():
    response = client.get("/api/pairs")
    assert response.status_code == 200
    data = response.json()
    assert data["universe_size"] == 11
    assert data["is_demo_data"] is False  # Phase 2: verified metadata active
    symbols = [p["symbol"] for p in data["pairs"]]
    assert any("BTCUSDT" in s for s in symbols)
    assert any("ETHUSDT" in s for s in symbols)
    assert any("XMRUSDT" in s for s in symbols)
    # Verify status is VERIFIED_3Y or PARTIAL_HISTORY
    for p in data["pairs"]:
        assert p["coverage_status"] in ["VERIFIED_3Y", "PARTIAL_HISTORY", "PENDING"]

def test_pair_candles():
    response = client.get("/api/pairs/BTCUSDT.P/candles?timeframe=15m&count=50")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "BTCUSDT.P"
    assert data["is_demo_data"] is True
    assert len(data["candles"]) == 50
    assert "open" in data["candles"][0]
    assert "close" in data["candles"][0]

def test_pair_candles_invalid_symbol():
    response = client.get("/api/pairs/UNKNOWN_PAIR/candles")
    assert response.status_code == 404

def test_experiments_list():
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 3
    assert data["is_demo_data"] is True
    assert any(exp["status"] == "COMPLETED" for exp in data["experiments"])

def test_data_coverage():
    response = client.get("/api/data/coverage")
    assert response.status_code == 200
    data = response.json()
    assert data["total_pairs"] == 11
    assert data["verified_pairs"] == 10  # 10 pairs have >=3Y verified coverage
    assert data["pending_audit_pairs"] == 1  # 1 pair (XMRUSDT) is partial history (0.78y)
    assert data["is_demo_data"] is False

def test_strategies():
    response = client.get("/api/strategies")
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 3
    assert data["is_demo_data"] is True
    families = [c["family"] for c in data["candidates"]]
    assert "Sweep-Reclaim" in families
    assert "Breakout/Trend" in families
    assert "Mean Reversion" in families

def test_models_arena():
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert len(data["configurations"]) == 3
    assert data["is_demo_data"] is True
    config_ids = [c["config_id"] for c in data["configurations"]]
    assert "CONFIG-A-GLOBAL" in config_ids
    assert "CONFIG-B-SPECIALISTS" in config_ids
    assert "CONFIG-C-CALIBRATED" in config_ids

@pytest.mark.asyncio
async def test_asterdex_v3_adapter_safety_and_interface():
    from backend.data.asterdex_v3_adapter import AsterDexV3AdapterInterface, PROD_FAPI_BASE_URL
    adapter = AsterDexV3AdapterInterface()
    assert adapter.base_url == PROD_FAPI_BASE_URL
    assert adapter.api_version == "Futures V3 (Pro API)"

    # Verify order execution is permanently disabled
    with pytest.raises(RuntimeError) as exc_info:
        await adapter.create_order()
    assert "permanently disabled" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info:
        await adapter.cancel_order()
    assert "permanently disabled" in str(exc_info.value)

    # Verify Phase 1 public stubs raise NotImplementedError (pending Phase 2 audit)
    with pytest.raises(NotImplementedError):
        await adapter.get_exchange_info()

    with pytest.raises(NotImplementedError):
        await adapter.get_klines("BTCUSDT")
