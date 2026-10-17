"""FastAPI main application entrypoint."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from safetyguard.config import PROJECT_ROOT
from safetyguard.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="AI SafetyGuard API",
    description="Backend service for multimodal video & audio potential safety incident detection.",
    version="1.0.0",
)

# Enable CORS for local development (Vite typically runs on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",  # Allow local network/dev clients
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Serve built frontend if available
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "message": "AI SafetyGuard API is running.",
            "documentation": "/docs",
            "health": "/api/health",
        }


def main():
    """Run backend using uvicorn server."""
    import uvicorn
    uvicorn.run("safetyguard.api.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
