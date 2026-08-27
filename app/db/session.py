"""Motor async de SQLAlchemy y fabrica de sesiones."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_engine_kwargs: dict[str, Any] = {
    "echo": settings.DB_ECHO,
    "pool_pre_ping": True,
    "future": True,
}

# SQLite (tests) no soporta los parametros de pool de Postgres
if not settings.sqlalchemy_dsn.startswith("sqlite"):
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_async_engine(settings.sqlalchemy_dsn, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI: una sesion por request, commit al final o rollback si falla."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Cierra el pool de conexiones (usado en el shutdown de la app)."""
    await engine.dispose()
