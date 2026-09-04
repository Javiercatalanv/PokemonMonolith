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

from app.core.exceptions import InsufficientDataError, NotFoundError
from app.models import Pokemon, PokemonForm
from app.repositories.pokemon import (
    PokemonFormRepository,
    PokemonRepository,
    TypeRepository,
)
from app.schemas.pokemon import (
    CounterPickRead,
    CounterTeamRead,
    GenerationRead,
    MatchupRead,
    PokemonRead,
)
from app.services.algorithms import (
    GENERATIONS,
    Contender,
    assign_counters,
    combined_effectiveness,
    compute_power_score,
    effectiveness_label,
    generation_range,
    percentile,
    rank_by_score,
)

# Cuantos pokemon se traen a memoria para los calculos que necesitan verlos todos
# (ranking, percentil, contraequipo). Con la Pokedex completa son 1025.
_MAX_SCAN = 10_000

# Un pokemon del equipo rival puede ser una especie o una de sus formas. Las dos traen
# los mismos atributos de combate, asi que los algoritmos y los schemas no distinguen.
Fighter = Pokemon | PokemonForm


def species_id(fighter: Fighter) -> int:
    """Numero de Pokedex de la especie: el de una forma es el de su base."""
    return fighter.pokemon_id if isinstance(fighter, PokemonForm) else fighter.id


class PokemonService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = PokemonRepository(session)
        self.forms_repo = PokemonFormRepository(session)
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

    async def search(self, query: str, *, limit: int = 10) -> Sequence[Pokemon]:
        """Sugerencias mientras se escribe: por numero exacto o por nombre parecido.

        Un termino numerico es un numero de Pokedex, no un trozo de nombre, asi que
        se resuelve como tal en vez de buscar digitos dentro de los nombres.
        """
        query = query.strip().lower()
        if not query:
            return []

        if query.isdigit():
            pokemon = await self.repo.get(int(query))
            return [pokemon] if pokemon is not None else []

        return await self.repo.search_by_name(query, limit=limit)

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
        items = await self.repo.list(limit=_MAX_SCAN)
        return rank_by_score(((item.name, self.power_score(item)) for item in items), top=limit)

    async def power_percentile(self, pokemon_id: int) -> float:
        pokemon = await self.get(pokemon_id)
        items = await self.repo.list(limit=_MAX_SCAN)
        return percentile([self.power_score(item) for item in items], self.power_score(pokemon))

    async def resolve(self, reference: str) -> Fighter:
        """Busca por numero o por nombre, y acepta tanto una especie como una forma.

        Se mira primero en `pokemon`: los numeros de la Pokedex y los nombres de
        especie son lo habitual, y una forma solo se pide cuando alguien la elige
        expresamente en su tarjeta ('charizard-mega-x' o su id 10034).
        """
        reference = reference.strip()

        if reference.isdigit():
            number = int(reference)
            pokemon = await self.repo.get(number)
            if pokemon is not None:
                return pokemon

            form = await self.forms_repo.get(number)
            if form is not None:
                return form
            raise NotFoundError(f"No existe el pokemon con id {number}")

        name = reference.lower()
        pokemon = await self.repo.get_by_name(name)
        if pokemon is not None:
            return pokemon

        form = await self.forms_repo.get_by_name(name)
        if form is not None:
            return form
        raise NotFoundError(f"No existe el pokemon '{reference}'")

    async def forms(self, reference: str) -> Sequence[PokemonForm]:
        """Formas de una especie. Acepta la especie o cualquiera de sus formas.

        Solo estan cargadas las que cambian tipos o stats, asi que una lista vacia
        significa que a ese pokemon no le cambia nada transformarse.
        """
        return await self.forms_repo.list_for(species_id(await self.resolve(reference)))

    def _contender(self, pokemon: Fighter) -> Contender:
        """Lo reduce a lo que el emparejamiento necesita: sus tipos y su potencia."""
        type_ids = (pokemon.type1_id, pokemon.type2_id) if pokemon.type2_id else (pokemon.type1_id,)
        return Contender(
            id=pokemon.id,
            name=pokemon.name,
            type_ids=type_ids,
            power=self.power_score(pokemon),
        )

    async def counter_team(
        self,
        references: Sequence[str],
        *,
        exclude_team: bool = False,
    ) -> CounterTeamRead:
        """Un equipo que bate al enviado, emparejando cada rival con su propio contra.

        Solo se miran los tipos: quien pega mas fuerte y quien encaja menos. Los stats
        unicamente desempatan entre candidatos con la misma ventaja de tipo.
        """
        team = [await self.resolve(reference) for reference in references]

        # Los candidatos son siempre especies base: una forma sirve para armar el
        # equipo rival, pero el generador no propone megas como contras.
        candidates = list(await self.repo.list(limit=_MAX_SCAN))
        if exclude_team:
            # Se excluye por especie: elegir Mega Charizard X descarta tambien al
            # Charizard de siempre, que es el mismo bicho con otra chaqueta.
            on_team = {species_id(fighter) for fighter in team}
            candidates = [pokemon for pokemon in candidates if pokemon.id not in on_team]

        matrix = await self.types.effectiveness_matrix()
        try:
            picks = assign_counters(
                matrix,
                [self._contender(pokemon) for pokemon in team],
                [self._contender(pokemon) for pokemon in candidates],
            )
        except ValueError as exc:
            raise InsufficientDataError(str(exc)) from exc

        by_id = {pokemon.id: pokemon for pokemon in candidates}
        return CounterTeamRead(
            total_advantage=sum(pick.advantage for pick in picks),
            picks=[
                CounterPickRead(
                    # `picks` viene en el mismo orden que `team`
                    enemy=PokemonRead.model_validate(enemy),
                    counter=PokemonRead.model_validate(by_id[pick.counter.id]),
                    advantage=pick.advantage,
                    offense_multiplier=pick.offense,
                    incoming_multiplier=pick.incoming,
                    label=effectiveness_label(pick.offense),
                )
                for enemy, pick in zip(team, picks, strict=True)
            ],
        )

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
