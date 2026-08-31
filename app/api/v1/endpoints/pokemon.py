"""Lectura de los datos cargados por el seeder."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import PaginationDep, PokemonServiceDep
from app.schemas.common import ErrorResponse, Page
from app.schemas.pokemon import MatchupRead, PokemonRead

router = APIRouter()

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "No encontrado"}
}


@router.get("", response_model=Page[PokemonRead], summary="Listar pokemon")
async def list_pokemon(
    service: PokemonServiceDep,
    pagination: PaginationDep,
    generation: Annotated[
        int | None,
        Query(ge=1, le=9, description="Filtrar por generacion (1-9)"),
    ] = None,
) -> Page[PokemonRead]:
    items, total = await service.list(
        limit=pagination.limit,
        offset=pagination.offset,
        generation=generation,
    )
    return Page[PokemonRead](
        items=[PokemonRead.model_validate(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get(
    "/top",
    summary="Ranking por puntuacion combinada de stats",
    response_model=list[dict[str, float | str]],
)
async def top_pokemon(service: PokemonServiceDep, limit: int = 10) -> list[dict[str, float | str]]:
    return [{"name": name, "score": score} for name, score in await service.top_by_power(limit)]


@router.get(
    "/by-type/{type_name}",
    response_model=list[PokemonRead],
    responses=_NOT_FOUND,
    summary="Pokemon de un tipo (primario o secundario)",
)
async def pokemon_by_type(
    type_name: str,
    service: PokemonServiceDep,
    limit: int = 50,
) -> list[PokemonRead]:
    items = await service.list_by_type(type_name.lower(), limit=limit)
    return [PokemonRead.model_validate(item) for item in items]


@router.get(
    "/{identifier}",
    response_model=PokemonRead,
    responses=_NOT_FOUND,
    summary="Detalle de un pokemon por id o nombre",
)
async def get_pokemon(identifier: str, service: PokemonServiceDep) -> PokemonRead:
    return PokemonRead.model_validate(await service.resolve(identifier))


@router.get(
    "/{pokemon_id}/percentile",
    responses=_NOT_FOUND,
    summary="Percentil de su puntuacion frente al resto",
)
async def get_percentile(pokemon_id: int, service: PokemonServiceDep) -> dict[str, float]:
    return {"percentile": await service.power_percentile(pokemon_id)}


@router.get(
    "/{pokemon_id}/matchup/{attacker_type}",
    response_model=MatchupRead,
    responses=_NOT_FOUND,
    summary="Efectividad de un tipo atacante contra este pokemon",
)
async def get_matchup(
    pokemon_id: int,
    attacker_type: str,
    service: PokemonServiceDep,
) -> MatchupRead:
    return await service.matchup(attacker_type, pokemon_id)
