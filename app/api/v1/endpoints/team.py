"""Contrarrestar un equipo entero mirando solo los tipos."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import PokemonServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.pokemon import CounterTeamRead

router = APIRouter()

MAX_TEAM_SIZE = 6

_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Algun miembro del equipo no existe"},
    409: {"model": ErrorResponse, "description": "No hay bastantes pokemon cargados"},
}


@router.get(
    "/counters",
    response_model=CounterTeamRead,
    responses=_ERRORS,
    summary="Equipo que vence al tuyo con la maxima ventaja de tipo",
)
async def counter_team(
    service: PokemonServiceDep,
    team: Annotated[
        list[str],
        Query(
            min_length=1,
            max_length=MAX_TEAM_SIZE,
            description=(
                "Hasta 6 pokemon, por numero de Pokedex o por nombre. Repite el "
                "parametro: ?team=venusaur&team=6&team=25"
            ),
        ),
    ],
    exclude_team: Annotated[
        bool,
        Query(description="Impedir que se proponga a un miembro del propio equipo"),
    ] = False,
) -> CounterTeamRead:
    return await service.counter_team(team, exclude_team=exclude_team)
