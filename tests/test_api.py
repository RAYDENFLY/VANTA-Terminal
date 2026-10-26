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
    assert data["is_demo_data"] is True
    symbols = [p["symbol"] for p in data["pairs"]]
    assert "BTCUSDT.P" in symbols
    assert "ETHUSDT.P" in symbols
    assert "XMRUSDT.P" in symbols
    # Verify status is PENDING or NOT TESTED
    for p in data["pairs"]:
        assert p["coverage_status"] in ["PENDING", "NOT TESTED"]
        assert p["model_status"] in ["PENDING", "NOT TESTED"]

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
    assert data["verified_pairs"] == 0
    assert data["is_demo_data"] is True

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
