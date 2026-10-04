"""Lectura de los datos cargados por el seeder."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import PaginationDep, PokemonServiceDep
from app.api.responses import Responses, error
from app.schemas.common import Page
from app.schemas.pokemon import (
    MatchupRead,
    PercentileRead,
    PokemonFormRead,
    PokemonRead,
    PowerScoreRead,
)

router = APIRouter()

_POKEMON_NOT_FOUND: Responses = {404: error("No existe el pokemon (`not_found`)")}
_TYPE_NOT_FOUND: Responses = {404: error("No existe el tipo (`not_found`)")}
_MATCHUP_NOT_FOUND: Responses = {404: error("No existe el tipo o el pokemon (`not_found`)")}

# Admite especie o forma, por numero o por nombre: lo resuelve `PokemonService.resolve`
Identifier = Annotated[
    str,
    Path(
        description="Numero de Pokedex, id de una forma (10001+) o nombre, sin distinguir "
        "mayusculas",
        examples=["bulbasaur", "25", "charizard-mega-x"],
    ),
]

# Solo especies base: estos endpoints buscan unicamente en la tabla `pokemon`
PokemonId = Annotated[int, Path(description="Numero de Pokedex de la especie", examples=[1])]

TypeName = Annotated[
    str,
    Path(description="Nombre del tipo en ingles, sin distinguir mayusculas", examples=["fire"]),
]


@router.get("", response_model=Page[PokemonRead], summary="Listar pokemon")
async def list_pokemon(
    service: PokemonServiceDep,
    pagination: PaginationDep,
    generation: Annotated[
        int | None,
        Query(ge=1, le=9, description="Filtrar por generacion (1-9)"),
    ] = None,
) -> Page[PokemonRead]:
    """Listado paginado por numero de Pokedex. Solo especies base, nunca formas."""
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
    "/search",
    response_model=list[PokemonRead],
    summary="Sugerencias por nombre parecido o por numero de Pokedex",
)
async def search_pokemon(
    service: PokemonServiceDep,
    q: Annotated[
        str,
        Query(min_length=1, max_length=50, description="Parte del nombre, o el numero exacto"),
    ],
    limit: Annotated[int, Query(ge=1, le=25, description="Cuantas sugerencias devolver")] = 10,
) -> list[PokemonRead]:
    """Alimenta el buscador incremental del frontend. Lista vacia si no hay parecidos."""
    return [PokemonRead.model_validate(item) for item in await service.search(q, limit=limit)]


@router.get(
    "/top",
    summary="Ranking por puntuacion combinada de stats",
    response_model=list[PowerScoreRead],
)
async def top_pokemon(
    service: PokemonServiceDep,
    limit: Annotated[int, Query(description="Cuantos devolver")] = 10,
) -> list[PowerScoreRead]:
    """De mayor a menor puntuacion, calculada en memoria sobre todos los pokemon cargados."""
    return [
        PowerScoreRead(name=name, score=score) for name, score in await service.top_by_power(limit)
    ]


@router.get(
    "/by-type/{type_name}",
    response_model=list[PokemonRead],
    responses=_TYPE_NOT_FOUND,
    summary="Pokemon de un tipo (primario o secundario)",
)
async def pokemon_by_type(
    type_name: TypeName,
    service: PokemonServiceDep,
    limit: Annotated[int, Query(description="Maximo de pokemon a devolver")] = 50,
) -> list[PokemonRead]:
    """404 si el tipo no existe; lista vacia si existe pero no hay pokemon cargados de el."""
    items = await service.list_by_type(type_name.lower(), limit=limit)
    return [PokemonRead.model_validate(item) for item in items]


@router.get(
    "/{identifier}",
    response_model=PokemonRead,
    responses=_POKEMON_NOT_FOUND,
    summary="Detalle de un pokemon por id o nombre",
)
async def get_pokemon(identifier: Identifier, service: PokemonServiceDep) -> PokemonRead:
    """Acepta tambien formas alternativas: `/pokemon/10034` es charizard-mega-x."""
    return PokemonRead.model_validate(await service.resolve(identifier))


@router.get(
    "/{identifier}/forms",
    response_model=list[PokemonFormRead],
    responses=_POKEMON_NOT_FOUND,
    summary="Formas alternativas que cambian tipos o stats",
)
async def list_forms(identifier: Identifier, service: PokemonServiceDep) -> list[PokemonFormRead]:
    """Megas, primal, regionales y variantes con stats propios.

    Lista vacia si transformarse no le cambia nada: las gigantamax y los disfraces
    no se guardan porque dejan tipos y stats intactos.
    """
    return [PokemonFormRead.model_validate(form) for form in await service.forms(identifier)]


@router.get(
    "/{pokemon_id}/percentile",
    response_model=PercentileRead,
    responses=_POKEMON_NOT_FOUND,
    summary="Percentil de su puntuacion frente al resto",
)
async def get_percentile(pokemon_id: PokemonId, service: PokemonServiceDep) -> PercentileRead:
    return PercentileRead(percentile=await service.power_percentile(pokemon_id))


@router.get(
    "/{pokemon_id}/matchup/{attacker_type}",
    response_model=MatchupRead,
    responses=_MATCHUP_NOT_FOUND,
    summary="Efectividad de un tipo atacante contra este pokemon",
)
async def get_matchup(
    pokemon_id: PokemonId,
    attacker_type: TypeName,
    service: PokemonServiceDep,
) -> MatchupRead:
    """Multiplica la efectividad contra cada tipo del defensor, como en el juego.

    Fuego contra planta/veneno es `2.0 x 1.0 = 2.0`; contra planta/acero, `2.0 x 2.0 = 4.0`.
    """
    return await service.matchup(attacker_type, pokemon_id)
