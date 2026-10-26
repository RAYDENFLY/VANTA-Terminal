"""
AsterDEX Futures V3 Public Market Data Client
=============================================
Official Documentation:
- API Repo: https://github.com/asterdex/api-docs
- Futures V3 General Info: https://asterdex.github.io/aster-api-website/futures-v3/general-info/
- Verified Date: 2026-10-27

Purely read-only, unauthenticated public market data access.
Order placement and authenticated execution are strictly prohibited.
"""

import json
import ssl
import time
import urllib.request
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

PROD_FAPI_BASE_URL = "https://fapi.asterdex.com"
TESTNET_FAPI_BASE_URL = "https://fapi.asterdex-testnet.com"

class AsterDexPublicClient:
    """
    Lightweight, read-only HTTP client for AsterDEX Futures V3 public endpoints.
    Uses Python standard library with zero external heavyweight dependencies.
    """

    def __init__(self, base_url: str = PROD_FAPI_BASE_URL, timeout_sec: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.ssl_context = ssl.create_default_context()
        self.headers = {
            "User-Agent": "VANTA-Terminal-Research/1.0 (Public Market Data Auditor)",
            "Accept": "application/json"
        }

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}
            query_str = "&".join(f"{k}={v}" for k, v in clean_params.items())
            url = f"{url}?{query_str}"

        req = urllib.request.Request(url, headers=self.headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec, context=self.ssl_context) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"AsterDEX HTTP Error {resp.status} on {endpoint}")
                raw_body = resp.read().decode("utf-8")
                return json.loads(raw_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"AsterDEX API Error [{e.code}] on {endpoint}: {err_body}")
        except Exception as e:
            raise RuntimeError(f"AsterDEX Connection Error on {endpoint}: {str(e)}")

    def ping(self) -> bool:
        """Endpoint: GET /fapi/v1/ping"""
        data = self._get("/fapi/v1/ping")
        return data == {}

    def get_server_time(self) -> int:
        """Endpoint: GET /fapi/v1/time"""
        data = self._get("/fapi/v1/time")
        return data.get("serverTime", 0)

    def get_exchange_info(self) -> Dict[str, Any]:
        """Endpoint: GET /fapi/v1/exchangeInfo"""
        return self._get("/fapi/v1/exchangeInfo")

    def get_klines(
        self,
        symbol: str,
        interval: str = "15m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[List[Any]]:
        """
        Endpoint: GET /fapi/v1/klines
        Max limit: 1500 bars per request.
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": min(limit, 1500)
        }
        data = self._get("/fapi/v1/klines", params)
        if not isinstance(data, list):
            raise ValueError(f"Expected klines list response, got {type(data)}")
        return data

    def get_funding_rate_history(
        self,
        symbol: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Endpoint: GET /fapi/v1/fundingRate"""
        params = {
            "symbol": symbol,
            "startTime": start_time,
            "endTime": end_time,
            "limit": min(limit, 1000)
        }
        return self._get("/fapi/v1/fundingRate", params)

    def get_premium_index(self, symbol: Optional[str] = None) -> Any:
        """Endpoint: GET /fapi/v1/premiumIndex"""
        params = {"symbol": symbol} if symbol else None
        return self._get("/fapi/v1/premiumIndex", params)
