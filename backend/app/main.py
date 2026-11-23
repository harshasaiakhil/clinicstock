import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from app.api.v1.api import api_router

logger = logging.getLogger("clinicstock.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Explicit startup lifecycle without automatic DB seeding
    logger.info("ClinicStock API starting up...")
    yield
    # Cleanup database engine connections on shutdown
    logger.info("ClinicStock API shutting down...")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Request Timing & Observability Middleware (Logs method, path, status, and duration in ms without logging secrets)
@app.middleware("http")
async def add_process_time_and_log(request: Request, call_next):
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    
    # Do not log static asset requests to reduce log clutter
    if not request.url.path.startswith("/assets/"):
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.2f}ms")
    return response

# CORS origins configured via environment variables
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints
@app.get("/healthz", tags=["Health"])
async def healthz():
    """Lightweight liveness probe"""
    return {"status": "ok", "app": settings.PROJECT_NAME}

@app.get("/readyz", tags=["Health"])
async def readyz():
    """Readiness probe checking database connectivity"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "disconnected"}
        )

# API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve Frontend static files if dist directory exists
frontend_dist_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)

if os.path.exists(frontend_dist_path):
    assets_path = os.path.join(frontend_dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{catchall:path}", include_in_schema=False)
    async def serve_frontend(catchall: str):
        if (
            catchall.startswith("api/")
            or catchall.startswith("docs")
            or catchall.startswith("redoc")
            or catchall.startswith("openapi.json")
            or catchall in ("healthz", "readyz")
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = os.path.join(frontend_dist_path, catchall)
        if catchall and os.path.isfile(file_path):
            return FileResponse(file_path)

        index_path = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

        raise HTTPException(status_code=404, detail="File Not Found")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": f"Welcome to {settings.PROJECT_NAME} API. Access API docs at /docs"}
