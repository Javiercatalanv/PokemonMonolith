"""Contrarrestar un equipo entero mirando solo los tipos."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import PokemonServiceDep
from app.api.responses import Responses, error
from app.schemas.pokemon import CounterTeamRead

router = APIRouter()

MAX_TEAM_SIZE = 6

_ERRORS: Responses = {
    404: error("Algun miembro del equipo no existe (`not_found`)"),
    409: error("No hay bastantes pokemon cargados (`insufficient_data`)"),
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
            examples=[["venusaur", "6", "25"]],
        ),
    ],
    exclude_team: Annotated[
        bool,
        Query(description="Impedir que se proponga a un miembro del propio equipo"),
    ] = False,
) -> CounterTeamRead:
    """Devuelve un contra distinto para cada miembro, mirando solo los tipos.

    - Cada pokemon pega con el mejor de sus dos tipos.
    - `advantage` es lo que reparte menos lo que encaja, en escalones log2.
    - Se maximiza la ventaja total del equipo (optimo exacto, no codicioso). Los stats
      base solo desempatan.

    Los miembros pueden ser formas (`charizard-mega-x`), pero los contras propuestos son
    siempre especies base.
    """
    return await service.counter_team(team, exclude_team=exclude_team)
