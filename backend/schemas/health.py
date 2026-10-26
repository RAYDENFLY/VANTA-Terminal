from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    data_source: str = "ASTERDEX FUTURES V3"
    data_mode: str = "PUBLIC DATA ONLY"
    live_orders_enabled: bool = False
    is_demo_data: bool = True
    active_worker: bool = False
    timestamp: str

class SystemStatusResponse(BaseModel):
    project_name: str
    version: str
    data_source: str = "ASTERDEX FUTURES V3"
    data_mode: str = "PUBLIC DATA ONLY"
    host: str
    port: int
    loopback_only: bool = True
    forbidden_port_8000_safe: bool = True
    live_orders_disabled: bool = True
    status: str = "nominal"
    worker_status: str = "IDLE"
    uptime_seconds: float
    resources: Dict[str, Any]
    demo_mode: bool = True
