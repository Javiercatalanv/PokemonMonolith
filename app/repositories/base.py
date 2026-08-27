"""Repositorio generico de lectura sobre SQLAlchemy async.

Solo lee: la escritura la hace el seeder con su propio motor sincrono.
"""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> Sequence[ModelT]:
        stmt = (
            select(self.model)
            .order_by(self.model.id)  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        return (await self.session.execute(stmt)).unique().scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return int((await self.session.execute(stmt)).scalar_one())
