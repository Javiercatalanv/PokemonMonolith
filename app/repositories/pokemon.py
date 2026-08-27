"""Acceso a datos de pokemon y de la tabla de efectividad."""

from collections.abc import Sequence

from sqlalchemy import select

from app.models import Pokemon, Type, TypeEffectiveness
from app.repositories.base import BaseRepository


class PokemonRepository(BaseRepository[Pokemon]):
    model = Pokemon

    async def get_by_name(self, name: str) -> Pokemon | None:
        stmt = select(Pokemon).where(Pokemon.name == name)
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def list_by_type(self, type_name: str, limit: int = 50) -> Sequence[Pokemon]:
        """Pokemon que tienen ese tipo, como primario o como secundario."""
        stmt = (
            select(Pokemon)
            .join(Type, Type.id.in_([Pokemon.type1_id, Pokemon.type2_id]))
            .where(Type.name == type_name)
            .order_by(Pokemon.id)
            .limit(limit)
        )
        return (await self.session.execute(stmt)).unique().scalars().all()


class TypeRepository(BaseRepository[Type]):
    model = Type

    async def get_by_name(self, name: str) -> Type | None:
        stmt = select(Type).where(Type.name == name)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def effectiveness_against(self, attacker_id: int, defender_ids: list[int]) -> list[float]:
        """Multiplicadores de un tipo atacante contra uno o dos tipos defensores."""
        stmt = select(TypeEffectiveness.damage_multiplier).where(
            TypeEffectiveness.attacker_id == attacker_id,
            TypeEffectiveness.defender_id.in_(defender_ids),
        )
        return list((await self.session.execute(stmt)).scalars().all())
