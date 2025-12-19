from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
import os
from app.services.settings_provider import settings_provider
from app.api.v1.endpoints import admin as admin_endpoints


def create_app() -> FastAPI:
    app = FastAPI(title="DrugGenix API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")
    # Fallback wiring for admin settings (avoids editing router.py)
    app.include_router(admin_endpoints.router, prefix="/api/v1/admin", tags=["admin"])

    @app.on_event("startup")
    def on_startup():
        # Create DB tables
        Base.metadata.create_all(bind=engine)
        # Ensure storage directories
        os.makedirs(settings.STORAGE_DIR, exist_ok=True)
        os.makedirs(settings.PROTEINS_DIR, exist_ok=True)
        # Load DB-backed settings cache
        settings_provider.reload()
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
