from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, engine
from app import models, referee_models, service_models, venue_models, tournament_models  # noqa: F401
from app.routers.auth import router as auth_router
from app.routers.profile import router as profile_router
from app.routers.referees import router as referees_router
from app.routers.admin import router as admin_router
from app.routers.services import router as services_router
from app.routers.venues import router as venues_router
from app.routers.competitions import router as competitions_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ARENA 360 API",
    version="0.5.0",
    description="Нэгдсэн спортын үйлчилгээний API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Bootstrap-Key"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(referees_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(venues_router, prefix="/api/v1")
app.include_router(competitions_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health():
    """Liveness probe: confirms that the API process is running."""
    return {"status": "ok", "service": "arena360-api", "version": app.version}


@app.get("/health/ready", tags=["system"])
def readiness():
    """Readiness probe: confirms the API can reach its configured database."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Өгөгдлийн сантай холбогдох боломжгүй байна.",
        )
    return {"status": "ready", "service": "arena360-api", "database": "connected"}
