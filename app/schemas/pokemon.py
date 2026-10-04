"""Contratos de salida de la API. Solo lectura: los datos entran por el seeder."""

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Id del tipo en la PokeAPI", examples=[12])
    name: str = Field(description="Nombre en minusculas, en ingles", examples=["grass"])


class PokemonRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "bulbasaur",
                "type1": {"id": 12, "name": "grass"},
                "type2": {"id": 4, "name": "poison"},
                "hp": 45,
                "attack": 49,
                "defense": 49,
                "sp_attack": 65,
                "sp_defense": 65,
                "speed": 45,
                "sprite_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/1.png",
                "stat_total": 318,
            }
        },
    )

    id: int = Field(description="Numero de Pokedex, o 10001+ si es una forma alternativa")
    name: str = Field(description="Nombre en minusculas, tal como viene de la PokeAPI")
    type1: TypeRead = Field(description="Tipo primario")
    type2: TypeRead | None = Field(description="Tipo secundario, o null si es monotipo")
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    sprite_url: str | None = Field(default=None, description="Imagen frontal por defecto")

    @computed_field(description="Suma de los seis stats base")  # type: ignore[prop-decorator]
    @property
    def stat_total(self) -> int:
        return self.hp + self.attack + self.defense + self.sp_attack + self.sp_defense + self.speed


class PokemonFormRead(PokemonRead):
    """Una forma alternativa: mismos campos que un pokemon, mas de quien es.

    Solo llegan aqui las formas que cambian tipos o stats, asi que cada opcion del
    desplegable altera de verdad el enfrentamiento.
    """

    pokemon_id: int = Field(description="Numero de Pokedex de la especie base", examples=[6])
    label: str = Field(
        description="Nombre corto para el selector: 'Mega X', 'Alola'", examples=["Mega X"]
    )


class PowerScoreRead(BaseModel):
    """Una entrada del ranking por puntuacion combinada de stats."""

    name: str = Field(examples=["mewtwo"])
    score: float = Field(
        description="Puntuacion 0-100 que pondera los seis stats base", examples=[78.42]
    )


class PercentileRead(BaseModel):
    percentile: float = Field(
        description="Porcentaje de pokemon cargados con menor puntuacion (0-100)",
        ge=0,
        le=100,
        examples=[87.5],
    )


class MatchupRead(BaseModel):
    """Resultado de enfrentar un tipo atacante contra un pokemon."""

    attacker_type: str = Field(examples=["fire"])
    defender: str = Field(description="Nombre del pokemon defensor", examples=["bulbasaur"])
    multiplier: float = Field(
        description="Producto de la efectividad contra cada tipo del defensor: 0, 0.25 ... 4",
        examples=[2.0],
    )
    label: str = Field(
        description="'inmune', 'poco eficaz', 'normal' o 'muy eficaz'", examples=["muy eficaz"]
    )


class CounterPickRead(BaseModel):
    """Un rival del equipo y el pokemon elegido para frenarlo."""

    enemy: PokemonRead = Field(description="Miembro del equipo enviado")
    counter: PokemonRead = Field(description="Especie base propuesta para vencerlo")
    advantage: int = Field(
        description="Escalones log2 de ventaja del contra sobre el rival. Rango [-5, 5]",
        ge=-5,
        le=5,
        examples=[3],
    )
    offense_multiplier: float = Field(
        description="Dano que el contra le hace al rival", examples=[4.0]
    )
    incoming_multiplier: float = Field(
        description="Dano que el rival le hace al contra", examples=[0.5]
    )
    label: str = Field(
        description="Etiqueta de `offense_multiplier`: 'inmune', 'poco eficaz', 'normal' "
        "o 'muy eficaz'",
        examples=["muy eficaz"],
    )


class CounterTeamRead(BaseModel):
    """Equipo propuesto para batir al equipo enviado, mirando solo los tipos."""

    total_advantage: int = Field(
        description="Suma de las ventajas, lo que maximiza el algoritmo", examples=[14]
    )
    picks: list[CounterPickRead] = Field(
        description="Un contra distinto por cada miembro, en el mismo orden que `team`"
    )


class GenerationRead(BaseModel):
    """Una generacion y cuantos de sus pokemon hay cargados ahora mismo.

    `loaded` deja que el frontend desactive las generaciones que el seeder
    todavia no ha traido, en vez de ofrecer un filtro que no devuelve nada.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "number": 1,
                "name": "generation-i",
                "region": "kanto",
                "first_id": 1,
                "last_id": 151,
                "total_species": 151,
                "loaded": 151,
            }
        }
    )

    number: int = Field(ge=1, le=9)
    name: str
    region: str
    first_id: int = Field(description="Primer numero de Pokedex de la generacion")
    last_id: int = Field(description="Ultimo numero de Pokedex de la generacion")
    total_species: int = Field(description="Especies que tiene la generacion")
    loaded: int = Field(description="Especies de esta generacion cargadas en la base de datos")
