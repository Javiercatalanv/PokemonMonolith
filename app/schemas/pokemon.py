"""Contratos de salida de la API. Solo lectura: los datos entran por el seeder."""

from pydantic import BaseModel, ConfigDict, Field, computed_field


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
    sprite_url: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def stat_total(self) -> int:
        return self.hp + self.attack + self.defense + self.sp_attack + self.sp_defense + self.speed


class PokemonFormRead(PokemonRead):
    """Una forma alternativa: mismos campos que un pokemon, mas de quien es.

    Solo llegan aqui las formas que cambian tipos o stats, asi que cada opcion del
    desplegable altera de verdad el enfrentamiento.
    """

    pokemon_id: int = Field(description="Numero de Pokedex de la especie base")
    label: str = Field(description="Nombre corto para el selector: 'Mega X', 'Alola'")


class MatchupRead(BaseModel):
    """Resultado de enfrentar un tipo atacante contra un pokemon."""

    attacker_type: str
    defender: str
    multiplier: float
    label: str


class CounterPickRead(BaseModel):
    """Un rival del equipo y el pokemon elegido para frenarlo."""

    enemy: PokemonRead
    counter: PokemonRead
    advantage: int = Field(
        description="Escalones log2 de ventaja del contra sobre el rival. Rango [-5, 5]",
    )
    offense_multiplier: float = Field(description="Dano que el contra le hace al rival")
    incoming_multiplier: float = Field(description="Dano que el rival le hace al contra")
    label: str


class CounterTeamRead(BaseModel):
    """Equipo propuesto para batir al equipo enviado, mirando solo los tipos."""

    total_advantage: int = Field(description="Suma de las ventajas, lo que maximiza el algoritmo")
    picks: list[CounterPickRead]


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
