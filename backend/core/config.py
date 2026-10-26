from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "VANTA Terminal"
    VERSION: str = "0.1.0-phase1"
    ENVIRONMENT: str = "development"
    
    # Runtime Hosts and Ports
    VANTA_HOST: str = "127.0.0.1"
    VANTA_BACKEND_PORT: int = 8101
    VANTA_FRONTEND_PORT: int = 3000
    
    # Base Directories
    PROJECT_ROOT: Path = Path("D:/vanta-terminal")
    DATA_DIR: Path = Path("D:/vanta-terminal/data")
    ARTIFACTS_DIR: Path = Path("D:/vanta-terminal/artifacts")
    EXPERIMENTS_DIR: Path = Path("D:/vanta-terminal/experiments")
    RUNTIME_DIR: Path = Path("D:/vanta-terminal/.runtime")
    
    # Safety Locks
    VANTA_LIVE_ORDERS_ENABLED: bool = False
    VANTA_SIMULATION_MODE: bool = True
    DATA_DEMO_FIXTURES_ONLY: bool = True
    
    # Exchange Adapter Metadata (AsterDEX Futures V3 Pro API)
    ASTERDEX_API_BASE_URL: str = "https://fapi.asterdex.com"
    ASTERDEX_API_VERSION: str = "FUTURES_V3_PRO"
    DATA_SOURCE_MODE: str = "PUBLIC_DATA_ONLY"
    
    # Concurrency Limits
    VANTA_MAX_WORKERS: int = 1
    VANTA_NUM_THREADS: int = 2

    model_config = SettingsConfigDict(
        env_file="D:/vanta-terminal/.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
