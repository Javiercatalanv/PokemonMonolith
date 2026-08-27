"""Esquema de la base de datos: tipos, tabla de efectividad y pokemon.

Se apoya en la `Base` declarativa del proyecto (`app.db.base`) para que la API y
el seeder compartan un unico `MetadataData`: una sola definicion de cada tabla.
"""

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Los 18 tipos canonicos. La PokeAPI expone ademas 'unknown', 'shadow' y 'stellar',
# que no forman parte de la tabla de efectividad y se descartan al ingestar.
CANONICAL_TYPES: frozenset[str] = frozenset(
    {
        "normal",
        "fighting",
        "flying",
        "poison",
        "ground",
        "rock",
        "bug",
        "ghost",
        "steel",
        "fire",
        "water",
        "grass",
        "electric",
        "psychic",
        "ice",
        "dragon",
        "dark",
        "fairy",
    }
)


class Type(Base):
    """Uno de los 18 tipos. El `id` es el mismo que usa la PokeAPI."""

    __tablename__ = "types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    def __repr__(self) -> str:
        return f"<Type {self.name}>"


class TypeEffectiveness(Base):
    """Multiplicador de dano de un tipo atacante contra uno defensor.

    Se almacena la matriz completa 18x18 (324 filas), incluidos los 1.0, para que
    una consulta de efectividad sea un JOIN directo sin tener que asumir defaults.
    """

    __tablename__ = "type_effectiveness"

    attacker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("types.id", ondelete="CASCADE"), primary_key=True
    )
    defender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("types.id", ondelete="CASCADE"), primary_key=True
    )
    # 0.0 (inmune) | 0.5 (poco eficaz) | 1.0 (normal) | 2.0 (muy eficaz)
    damage_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    attacker: Mapped[Type] = relationship(foreign_keys=[attacker_id], lazy="joined")
    defender: Mapped[Type] = relationship(foreign_keys=[defender_id], lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<TypeEffectiveness {self.attacker_id}->{self.defender_id} x{self.damage_multiplier}>"
        )


class Pokemon(Base):
    """Pokemon con sus stats base. El `id` es el numero de la Pokedex nacional."""

    __tablename__ = "pokemon"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)

    type1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("types.id", ondelete="RESTRICT"), nullable=False
    )
    type2_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("types.id", ondelete="RESTRICT"), nullable=True
    )

    hp: Mapped[int] = mapped_column(Integer, nullable=False)
    attack: Mapped[int] = mapped_column(Integer, nullable=False)
    defense: Mapped[int] = mapped_column(Integer, nullable=False)
    sp_attack: Mapped[int] = mapped_column(Integer, nullable=False)
    sp_defense: Mapped[int] = mapped_column(Integer, nullable=False)
    speed: Mapped[int] = mapped_column(Integer, nullable=False)

    type1: Mapped[Type] = relationship(foreign_keys=[type1_id], lazy="joined")
    type2: Mapped[Type | None] = relationship(foreign_keys=[type2_id], lazy="joined")

    __table_args__ = (
        Index("ix_pokemon_type1_id", "type1_id"),
        Index("ix_pokemon_type2_id", "type2_id"),
    )

    def __repr__(self) -> str:
        return f"<Pokemon #{self.id} {self.name}>"
