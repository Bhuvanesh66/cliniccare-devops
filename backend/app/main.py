from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .db import DbSession
from .routers import appointments, doctors, patients, stats

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Book and track clinic appointments across doctors and patients.",
)

# HTTP request count/latency metrics for Prometheus. Probe and scrape traffic is
# excluded so dashboards show real user traffic only.
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(stats.router)


@app.get("/", tags=["service"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/api/info", tags=["service"])
def info():
    """Build details shown in the UI footer, so a deploy can be traced to its commit."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "git_sha": settings.git_sha,
        "environment": settings.environment,
    }


@app.get("/health", tags=["service"])
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "UP"}


@app.get("/ready", tags=["service"])
def ready(db: DbSession):
    """Readiness: the database is reachable and the schema has been migrated."""
    try:
        db.execute(text("SELECT 1 FROM alembic_version"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "NOT_READY", "reason": "database unavailable or not migrated"},
        )
    return {"status": "READY"}
