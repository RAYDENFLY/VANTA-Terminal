from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.core.config import settings
from backend.api.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Independent Quantitative ML Research Workstation for Crypto-Futures. Local Research Only · Zero Live Orders.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware (Local loopback only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{settings.VANTA_FRONTEND_PORT}",
        f"http://localhost:{settings.VANTA_FRONTEND_PORT}",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Custom Security & Research Header Middleware
@app.middleware("http")
async def add_research_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Terminal-Mode"] = "LOCAL RESEARCH - NO LIVE ORDERS"
    response.headers["X-Vanta-Version"] = settings.VERSION
    return response

# Include all API routes
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "terminal": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": "LOCAL RESEARCH · NO LIVE ORDERS",
        "api_docs": f"http://127.0.0.1:{settings.VANTA_BACKEND_PORT}/docs",
        "frontend": f"http://127.0.0.1:{settings.VANTA_FRONTEND_PORT}",
        "demo_data_active": True
    }
