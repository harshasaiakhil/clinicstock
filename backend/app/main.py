import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set CORS origins (configured to allow all for local development & react-native apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve Frontend static files if dist directory exists
frontend_dist_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)

if os.path.exists(frontend_dist_path):
    # Mount frontend assets folder if it exists
    assets_path = os.path.join(frontend_dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{catchall:path}")
    async def serve_frontend(catchall: str):
        # Ignore API and documentation routes so FastAPI can process them
        if (
            catchall.startswith("api/")
            or catchall.startswith("docs")
            or catchall.startswith("redoc")
            or catchall.startswith("openapi.json")
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = os.path.join(frontend_dist_path, catchall)
        if catchall and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Fallback to index.html for client-side routing
        index_path = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

        raise HTTPException(status_code=404, detail="File Not Found")
else:
    @app.get("/")
    def root():
        return {"message": f"Welcome to {settings.PROJECT_NAME} API. Access API docs at /docs"}
