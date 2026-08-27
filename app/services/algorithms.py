"""Algoritmos de dominio.

Funciones puras: sin I/O, sin base de datos, sin HTTP. Asi son triviales de
testear y de reutilizar desde cualquier servicio.
"""

from collections.abc import Iterable, Sequence
from typing import NamedTuple

# Los stats base se mueven en [1, 255]
_STAT_MAX = 255


class Generation(NamedTuple):
    number: int
    name: str
    region: str
    first_id: int
    last_id: int

    @property
    def total_species(self) -> int:
        return self.last_id - self.first_id + 1


# Cada generacion es un tramo contiguo de la Pokedex nacional, y el `id` de la tabla
# `pokemon` ES ese numero. Por eso filtrar por generacion es un BETWEEN sobre la clave
# primaria, sin necesidad de una columna extra.
GENERATIONS: tuple[Generation, ...] = (
    Generation(1, "generation-i", "kanto", 1, 151),
    Generation(2, "generation-ii", "johto", 152, 251),
    Generation(3, "generation-iii", "hoenn", 252, 386),
    Generation(4, "generation-iv", "sinnoh", 387, 493),
    Generation(5, "generation-v", "unova", 494, 649),
    Generation(6, "generation-vi", "kalos", 650, 721),
    Generation(7, "generation-vii", "alola", 722, 809),
    Generation(8, "generation-viii", "galar", 810, 905),
    Generation(9, "generation-ix", "paldea", 906, 1025),
)


def generation_range(number: int) -> tuple[int, int]:
    """Primer y ultimo id de la Pokedex nacional de una generacion."""
    for generation in GENERATIONS:
        if generation.number == number:
            return generation.first_id, generation.last_id
    raise ValueError(f"No existe la generacion {number}")


# Peso de cada stat en la puntuacion combinada. Ajusta a tu criterio.
_WEIGHTS = {
    "hp": 0.20,
    "attack": 0.20,
    "defense": 0.15,
    "sp_attack": 0.20,
    "sp_defense": 0.15,
    "speed": 0.10,
}


def compute_power_score(
    hp: int,
    attack: int,
    defense: int,
    sp_attack: int,
    sp_defense: int,
    speed: int,
) -> float:
    """Puntuacion 0-100 combinando los seis stats base con pesos."""
    stats = {
        "hp": hp,
        "attack": attack,
        "defense": defense,
        "sp_attack": sp_attack,
        "sp_defense": sp_defense,
        "speed": speed,
    }
    score = sum(value / _STAT_MAX * _WEIGHTS[name] for name, value in stats.items())
    return round(score * 100, 2)


def combined_effectiveness(multipliers: Iterable[float]) -> float:
    """Efectividad contra un pokemon de uno o dos tipos.

    Los multiplicadores se acumulan multiplicando, que es como funciona el juego:
    fuego contra planta/veneno es 2.0 * 1.0 = 2.0; contra planta/acero, 2.0 * 2.0 = 4.0.
    """
    result = 1.0
    for multiplier in multipliers:
        result *= multiplier
    return round(result, 3)


def effectiveness_label(multiplier: float) -> str:
    """Etiqueta legible para un multiplicador de dano."""
    if multiplier == 0:
        return "inmune"
    if multiplier < 1:
        return "poco eficaz"
    if multiplier > 1:
        return "muy eficaz"
    return "normal"


def rank_by_score(items: Iterable[tuple[str, float]], top: int = 10) -> list[tuple[str, float]]:
    """Devuelve los `top` elementos con mayor puntuacion, de mayor a menor."""
    return sorted(items, key=lambda pair: pair[1], reverse=True)[:top]


def percentile(scores: Sequence[float], value: float) -> float:
    """Porcentaje de `scores` que queda por debajo de `value` (0-100)."""
    if not scores:
        return 0.0
    below = sum(1 for score in scores if score < value)
    return round(below / len(scores) * 100, 2)
