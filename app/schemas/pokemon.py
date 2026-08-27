"""Contratos de salida de la API. Solo lectura: los datos entran por el seeder."""

from pydantic import BaseModel, ConfigDict, computed_field


class TypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class PokemonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type1: TypeRead
    type2: TypeRead | None
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stat_total(self) -> int:
        return self.hp + self.attack + self.defense + self.sp_attack + self.sp_defense + self.speed


class MatchupRead(BaseModel):
    """Resultado de enfrentar un tipo atacante contra un pokemon."""

    attacker_type: str
    defender: str
    multiplier: float
    label: str


class GenerationRead(BaseModel):
    """Una generacion y cuantos de sus pokemon hay cargados ahora mismo.

    `loaded` deja que el frontend desactive las generaciones que el seeder
    todavia no ha traido, en vez de ofrecer un filtro que no devuelve nada.
    """

    number: int
    name: str
    region: str
    first_id: int
    last_id: int
    total_species: int
    loaded: int
