"""Dependencias reutilizables de FastAPI."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.pokemon import PokemonService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class Pagination:
    """Parametros de paginacion compartidos por los endpoints de listado."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100, description="Registros por pagina")] = 50,
        offset: Annotated[int, Query(ge=0, description="Registros a saltar")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PaginationDep = Annotated[Pagination, Depends()]


def get_pokemon_service(session: SessionDep) -> PokemonService:
    return PokemonService(session)


PokemonServiceDep = Annotated[PokemonService, Depends(get_pokemon_service)]
