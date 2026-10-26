import time
from datetime import datetime, timezone
from fastapi import APIRouter
from backend.core.config import settings
from backend.core.telemetry import get_all_resource_telemetry
from backend.schemas.health import HealthResponse, SystemStatusResponse

router = APIRouter(tags=["System & Health"])

START_TIME = time.time()

@router.get("/health", response_model=HealthResponse)
def get_health():
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        live_orders_enabled=settings.VANTA_LIVE_ORDERS_ENABLED,
        is_demo_data=settings.DATA_DEMO_FIXTURES_ONLY,
        active_worker=False,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

@router.get("/system/status", response_model=SystemStatusResponse)
def get_system_status():
    uptime = time.time() - START_TIME
    telemetry = get_all_resource_telemetry()
    return SystemStatusResponse(
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        host=settings.VANTA_HOST,
        port=settings.VANTA_BACKEND_PORT,
        loopback_only=True,
        forbidden_port_8000_safe=True,
        live_orders_disabled=True,
        status="nominal",
        worker_status="IDLE",
        uptime_seconds=round(uptime, 1),
        resources=telemetry,
        demo_mode=settings.DATA_DEMO_FIXTURES_ONLY
    )

@router.get("/system/resources")
def get_system_resources():
    return {
        "telemetry": get_all_resource_telemetry(),
        "is_demo_data": False,
        "measured_live": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
