"""Algoritmos de dominio.

Funciones puras: sin I/O, sin base de datos, sin HTTP. Asi son triviales de
testear y de reutilizar desde cualquier servicio.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
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


# --- Contrarrestar un equipo entero ---

# Matriz de efectividad indexada por (tipo atacante, tipo defensor).
EffectivenessMatrix = Mapping[tuple[int, int], float]

# Un x0 (inmunidad) se trata como tres escalones por debajo de x1, la misma distancia
# que separa x0.125 de x1. Sin este suelo, log2(0) seria -inf y contaminaria las sumas.
_MULTIPLIER_FLOOR = 0.125

# La ventaja de tipo siempre es un entero (ver `type_advantage`), asi que este peso solo
# puede desempatar: un stat score de 100 aporta 1e-4, muy por debajo de un escalon.
_STAT_TIEBREAK = 1e-6

_NEG_INF = float("-inf")


class Contender(NamedTuple):
    """Lo unico que el emparejamiento necesita saber de un pokemon."""

    id: int
    name: str
    type_ids: tuple[int, ...]  # uno o dos
    power: float = 0.0


class CounterPick(NamedTuple):
    """Un rival y el pokemon asignado para frenarlo."""

    enemy: Contender
    counter: Contender
    advantage: int
    offense: float  # lo que el contra le hace al rival
    incoming: float  # lo que el rival le hace al contra


def attack_multiplier(
    matrix: EffectivenessMatrix,
    attacker_type_id: int,
    defender_type_ids: Iterable[int],
) -> float:
    """Dano de UN tipo atacante contra un defensor de uno o dos tipos."""
    return combined_effectiveness(
        matrix.get((attacker_type_id, defender_type_id), 1.0)
        for defender_type_id in defender_type_ids
    )


def best_attack(
    matrix: EffectivenessMatrix,
    attacker: Contender,
    defender: Contender,
) -> float:
    """El mejor multiplicador que el atacante consigue con sus propios tipos.

    Como no se miran los ataques, se asume que cada pokemon pega con el mas favorable
    de sus dos tipos: es la mejor aproximacion posible sin conocer su moveset.
    """
    return max(
        (attack_multiplier(matrix, type_id, defender.type_ids) for type_id in attacker.type_ids),
        default=1.0,
    )


def _steps(multiplier: float) -> int:
    """Escalones log2 de un multiplicador: x4 -> 2, x1 -> 0, x0.5 -> -1, x0 -> -3."""
    return round(math.log2(max(multiplier, _MULTIPLIER_FLOOR)))


def type_advantage(
    matrix: EffectivenessMatrix,
    candidate: Contender,
    enemy: Contender,
) -> int:
    """Cuanto le conviene a `candidate` enfrentarse a `enemy`, solo por tipos.

    Positivo = le pega mas fuerte de lo que recibe. Se mide en escalones log2 para que
    "pegar el doble" y "recibir la mitad" valgan lo mismo; el resultado es un entero
    en [-5, 5]. Ejemplos: pegar x4 y recibir x1 da 2; pegar x2 y recibir x0.5 tambien.
    """
    dealt = _steps(best_attack(matrix, candidate, enemy))
    taken = _steps(best_attack(matrix, enemy, candidate))
    return dealt - taken


def assign_counters(
    matrix: EffectivenessMatrix,
    team: Sequence[Contender],
    candidates: Sequence[Contender],
) -> list[CounterPick]:
    """Asigna a cada miembro de `team` un contrincante distinto sacado de `candidates`.

    Maximiza la ventaja de tipo TOTAL, no la de cada emparejamiento por separado: a
    veces conviene ceder el mejor contra de un rival a otro que no tiene alternativa.
    La puntuacion de stats solo entra a romper empates.

    El optimo es exacto, no codicioso. Dos recortes lo hacen barato: a cada rival le
    basta con mirar sus `len(team)` mejores candidatos (los otros rivales no pueden
    ocuparlos todos), lo que deja 36 candidatos como mucho, y sobre ellos se resuelve
    el emparejamiento con programacion dinamica sobre los 2^6 = 64 subconjuntos del
    equipo. Devuelve una eleccion por rival, en el mismo orden que `team`.
    """
    size = len(team)
    if size == 0:
        return []
    if len(candidates) < size:
        raise ValueError(
            f"Hacen falta al menos {size} pokemon entre los que elegir y solo hay {len(candidates)}"
        )

    advantage = [
        [type_advantage(matrix, candidate, enemy) for enemy in team] for candidate in candidates
    ]

    # Se ordena por (ventaja, stats, id ascendente): los stats desempatan y el id hace
    # que el resultado no dependa del orden en que llegaron los candidatos.
    pool: list[int] = []
    seen: set[int] = set()
    for enemy_index in range(size):
        ranked = sorted(
            (advantage[ci][enemy_index], candidates[ci].power, -candidates[ci].id, ci)
            for ci in range(len(candidates))
        )
        for *_, candidate_index in reversed(ranked[-size:]):
            if candidate_index not in seen:
                seen.add(candidate_index)
                pool.append(candidate_index)

    full = (1 << size) - 1
    # layers[k][mask] = mejor puntuacion cubriendo los rivales de `mask` con los k
    # primeros candidatos del pool. Cada capa mira la anterior, asi que ningun
    # candidato se usa dos veces.
    layers: list[list[float]] = [[0.0] + [_NEG_INF] * full]
    parents: list[list[tuple[int, int] | None]] = []

    for candidate_index in pool:
        previous = layers[-1]
        current = list(previous)  # opcion "no uso este candidato"
        parent: list[tuple[int, int] | None] = [None] * (full + 1)
        score = advantage[candidate_index]
        bonus = candidates[candidate_index].power * _STAT_TIEBREAK

        for mask in range(full + 1):
            if previous[mask] == _NEG_INF:
                continue
            for enemy_index in range(size):
                bit = 1 << enemy_index
                if mask & bit:
                    continue
                value = previous[mask] + score[enemy_index] + bonus
                if value > current[mask | bit]:
                    current[mask | bit] = value
                    parent[mask | bit] = (mask, enemy_index)

        layers.append(current)
        parents.append(parent)

    # Se deshace el camino: un `parent` no vacio significa que ese candidato mejoro
    # la casilla, es decir, que se uso.
    chosen: dict[int, int] = {}
    mask = full
    for step in range(len(pool), 0, -1):
        transition = parents[step - 1][mask]
        if transition is None:
            continue
        mask, enemy_index = transition
        chosen[enemy_index] = pool[step - 1]

    picks: list[CounterPick] = []
    for enemy_index, enemy in enumerate(team):
        counter = candidates[chosen[enemy_index]]
        picks.append(
            CounterPick(
                enemy=enemy,
                counter=counter,
                advantage=advantage[chosen[enemy_index]][enemy_index],
                offense=best_attack(matrix, counter, enemy),
                incoming=best_attack(matrix, enemy, counter),
            )
        )
    return picks
