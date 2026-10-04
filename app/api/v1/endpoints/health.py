"""Endpoints de salud: liveness y readiness."""

from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.deps import SessionDep
from app.api.responses import error
from app.core.config import settings
from app.schemas.common import HealthRead, ReadinessRead

router = APIRouter()


@router.get("/health", response_model=HealthRead, summary="Liveness probe")
async def health() -> HealthRead:
    """Responde mientras el proceso este vivo, sin mirar la base de datos."""
    return HealthRead(status="ok", environment=settings.ENVIRONMENT, version="0.1.0")


@router.get(
    "/health/ready",
    response_model=ReadinessRead,
    summary="Readiness probe (comprueba la base de datos)",
    status_code=status.HTTP_200_OK,
    responses={500: error("La base de datos no responde (`internal_error`)")},
)
async def readiness(session: SessionDep) -> ReadinessRead:
    """Lanza un `SELECT 1`. Si la base de datos no contesta, responde 500."""
    await session.execute(text("SELECT 1"))
    return ReadinessRead(status="ready", database="ok")
