"""Catalogo de generaciones, para que el frontend pinte el selector."""

from fastapi import APIRouter

from app.api.deps import PokemonServiceDep
from app.schemas.pokemon import GenerationRead

router = APIRouter()


@router.get(
    "",
    response_model=list[GenerationRead],
    summary="Las 9 generaciones y cuantos pokemon hay cargados de cada una",
)
async def list_generations(service: PokemonServiceDep) -> list[GenerationRead]:
    return await service.generations()
