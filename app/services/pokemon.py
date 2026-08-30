"""Logica de negocio sobre los datos que ha cargado el seeder.

Esta capa no descarga nada de la PokeAPI: de eso se encarga `seeder/`. Aqui solo
se lee de la base de datos y se aplican los algoritmos.
"""

# Imprescindible: el metodo `list` de esta clase tapa al `list` incorporado dentro del
# cuerpo de la clase, asi que anotaciones como `-> list[GenerationRead]` intentarian
# indexar la funcion. Con las anotaciones diferidas no se evaluan al definir el metodo.
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import Pokemon
from app.repositories.pokemon import PokemonRepository, TypeRepository
from app.schemas.pokemon import GenerationRead, MatchupRead
from app.services.algorithms import (
    GENERATIONS,
    combined_effectiveness,
    compute_power_score,
    effectiveness_label,
    generation_range,
    percentile,
    rank_by_score,
)


class PokemonService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = PokemonRepository(session)
        self.types = TypeRepository(session)

    async def get(self, pokemon_id: int) -> Pokemon:
        pokemon = await self.repo.get(pokemon_id)
        if pokemon is None:
            raise NotFoundError(f"No existe el pokemon con id {pokemon_id}")
        return pokemon

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        generation: int | None = None,
    ) -> tuple[Sequence[Pokemon], int]:
        if generation is None:
            return await self.repo.list(limit=limit, offset=offset), await self.repo.count()

        try:
            first_id, last_id = generation_range(generation)
        except ValueError as exc:
            raise NotFoundError(str(exc)) from exc

        items = await self.repo.list_by_id_range(first_id, last_id, limit=limit, offset=offset)
        total = await self.repo.count_by_id_range(first_id, last_id)
        return items, total

    async def generations(self) -> list[GenerationRead]:
        """Las 9 generaciones, con cuantos pokemon de cada una hay cargados."""
        return [
            GenerationRead(
                number=generation.number,
                name=generation.name,
                region=generation.region,
                first_id=generation.first_id,
                last_id=generation.last_id,
                total_species=generation.total_species,
                loaded=await self.repo.count_by_id_range(generation.first_id, generation.last_id),
            )
            for generation in GENERATIONS
        ]

    async def list_by_type(self, type_name: str, limit: int = 50) -> Sequence[Pokemon]:
        if await self.types.get_by_name(type_name) is None:
            raise NotFoundError(f"No existe el tipo '{type_name}'")
        return await self.repo.list_by_type(type_name, limit=limit)

    def power_score(self, pokemon: Pokemon) -> float:
        return compute_power_score(
            pokemon.hp,
            pokemon.attack,
            pokemon.defense,
            pokemon.sp_attack,
            pokemon.sp_defense,
            pokemon.speed,
        )

    async def top_by_power(self, limit: int = 10) -> list[tuple[str, float]]:
        """Ranking calculado en memoria a partir de los stats guardados."""
        items = await self.repo.list(limit=10_000)
        return rank_by_score(((item.name, self.power_score(item)) for item in items), top=limit)

    async def power_percentile(self, pokemon_id: int) -> float:
        pokemon = await self.get(pokemon_id)
        items = await self.repo.list(limit=10_000)
        return percentile([self.power_score(item) for item in items], self.power_score(pokemon))

    async def matchup(self, attacker_type: str, pokemon_id: int) -> MatchupRead:
        """Cuanto dano hace un tipo atacante contra un pokemon concreto."""
        attacker = await self.types.get_by_name(attacker_type.lower())
        if attacker is None:
            raise NotFoundError(f"No existe el tipo '{attacker_type}'")

        defender = await self.get(pokemon_id)
        defender_type_ids = [defender.type1_id]
        if defender.type2_id is not None:
            defender_type_ids.append(defender.type2_id)

        multipliers = await self.types.effectiveness_against(attacker.id, defender_type_ids)
        total = combined_effectiveness(multipliers)

        return MatchupRead(
            attacker_type=attacker.name,
            defender=defender.name,
            multiplier=total,
            label=effectiveness_label(total),
        )
