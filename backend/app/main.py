from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .routers import appointments, doctors, patients, stats


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Containers run `alembic upgrade head` before Uvicorn; create_all is a no-op then
    # and keeps tests and `uvicorn --reload` self-contained.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Clinic appointment booking: doctors, patients and the front-desk appointment workflow.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(stats.router)


@app.get("/", tags=["ops"])
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/api/info", tags=["ops"])
def info():
    """Shown in the UI footer: proves which commit is deployed where."""
    return {"version": settings.app_version, "environment": settings.environment}


@app.get("/health", tags=["ops"])
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "UP"}


@app.get("/ready", tags=["ops"])
def ready(db: Session = Depends(get_db)):
    """Readiness: can we serve traffic right now? Requires a working database connection."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "NOT_READY", "reason": "database unavailable"})
    return {"status": "READY"}
