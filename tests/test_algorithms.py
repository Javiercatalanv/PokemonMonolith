"""Los algoritmos son funciones puras: se testean sin base de datos ni red."""

from itertools import count

import pytest

from app.services.algorithms import (
    GENERATIONS,
    Contender,
    assign_counters,
    best_attack,
    combined_effectiveness,
    compute_power_score,
    effectiveness_label,
    generation_range,
    percentile,
    rank_by_score,
    type_advantage,
)


def test_score_is_bounded() -> None:
    assert compute_power_score(0, 0, 0, 0, 0, 0) == 0.0
    assert compute_power_score(255, 255, 255, 255, 255, 255) == 100.0


def test_score_grows_with_stats() -> None:
    assert compute_power_score(90, 90, 90, 90, 90, 90) > compute_power_score(30, 30, 30, 30, 30, 30)


@pytest.mark.parametrize(
    ("multipliers", "expected"),
    [
        ([2.0, 1.0], 2.0),  # planta/veneno frente a fuego
        ([2.0, 2.0], 4.0),  # doble debilidad
        ([0.5, 0.5], 0.25),  # doble resistencia
        ([0.0, 2.0], 0.0),  # la inmunidad manda
        ([], 1.0),  # sin datos, dano normal
    ],
)
def test_combined_effectiveness(multipliers: list[float], expected: float) -> None:
    assert combined_effectiveness(multipliers) == expected


@pytest.mark.parametrize(
    ("multiplier", "label"),
    [(0.0, "inmune"), (0.25, "poco eficaz"), (1.0, "normal"), (4.0, "muy eficaz")],
)
def test_effectiveness_label(multiplier: float, label: str) -> None:
    assert effectiveness_label(multiplier) == label


def test_rank_by_score() -> None:
    assert rank_by_score([("a", 1.0), ("b", 3.0), ("c", 2.0)], 2) == [("b", 3.0), ("c", 2.0)]
    assert rank_by_score([], 5) == []


def test_percentile() -> None:
    assert percentile([10.0, 20.0, 30.0, 40.0], 30.0) == 50.0
    assert percentile([], 10.0) == 0.0


# --- Generaciones ---


def test_generation_range() -> None:
    assert generation_range(1) == (1, 151)
    assert generation_range(2) == (152, 251)
    assert generation_range(9) == (906, 1025)


def test_unknown_generation_raises() -> None:
    with pytest.raises(ValueError, match="No existe la generacion 10"):
        generation_range(10)


def test_generations_are_contiguous_and_cover_the_national_dex() -> None:
    """Sin huecos ni solapes: cada generacion empieza donde acaba la anterior."""
    assert GENERATIONS[0].first_id == 1
    assert GENERATIONS[-1].last_id == 1025

    for previous, current in zip(GENERATIONS[:-1], GENERATIONS[1:], strict=True):
        assert current.first_id == previous.last_id + 1

    assert sum(gen.total_species for gen in GENERATIONS) == 1025


# --- Contrarrestar un equipo ---

# Tipos de juguete. `attack_multiplier` asume 1.0 en lo que no este declarado, asi que
# basta con listar los cruces interesantes.
FIRE, WATER, GRASS, GROUND, ELECTRIC = 1, 2, 3, 4, 5

MATRIX = {
    (FIRE, GRASS): 2.0,
    (FIRE, WATER): 0.5,
    (FIRE, FIRE): 0.5,
    (WATER, FIRE): 2.0,
    (WATER, GROUND): 2.0,
    (WATER, GRASS): 0.5,
    (WATER, WATER): 0.5,
    (GRASS, WATER): 2.0,
    (GRASS, GROUND): 2.0,
    (GRASS, FIRE): 0.5,
    (GRASS, GRASS): 0.5,
    (GROUND, FIRE): 2.0,
    (GROUND, ELECTRIC): 2.0,
    (GROUND, GRASS): 0.5,
    (ELECTRIC, WATER): 2.0,
    (ELECTRIC, GROUND): 0.0,
    (ELECTRIC, GRASS): 0.5,
    (ELECTRIC, ELECTRIC): 0.5,
}


_ids = count(1)


def _unit(name: str, *type_ids: int, power: float = 50.0) -> Contender:
    """Un pokemon de mentira. Los ids son correlativos: el desempate por id es estable."""
    return Contender(id=next(_ids), name=name, type_ids=type_ids, power=power)


def test_best_attack_uses_the_attackers_best_type() -> None:
    """Un doble tipo pega con el que mas dano haga, no con el primero."""
    dual = _unit("dual", WATER, GRASS)
    assert best_attack(MATRIX, dual, _unit("fire", FIRE)) == 2.0  # water, no grass


def test_best_attack_multiplies_both_defender_types() -> None:
    """Contra dos tipos, los multiplicadores se acumulan igual que en el juego."""
    assert best_attack(MATRIX, _unit("water", WATER), _unit("gg", GROUND, FIRE)) == 4.0


def test_type_advantage_is_symmetric() -> None:
    """Lo que uno gana en el cruce, el otro lo pierde exactamente."""
    left, right = _unit("water", WATER), _unit("fire", FIRE)
    assert type_advantage(MATRIX, left, right) == -type_advantage(MATRIX, right, left)


def test_type_advantage_counts_log2_steps() -> None:
    # water pega x2 al fuego y recibe x0.5: dos escalones arriba, uno abajo
    assert type_advantage(MATRIX, _unit("water", WATER), _unit("fire", FIRE)) == 2
    assert type_advantage(MATRIX, _unit("fire", FIRE), _unit("fire", FIRE)) == 0


def test_immunity_is_a_three_step_penalty() -> None:
    """Electrico no puede tocar a tierra (x0) y encima recibe x2."""
    electric, ground = _unit("electric", ELECTRIC), _unit("ground", GROUND)
    assert type_advantage(MATRIX, electric, ground) == -4
    assert type_advantage(MATRIX, ground, electric) == 4


def test_assign_counters_gives_one_distinct_pick_per_member() -> None:
    team = [_unit("charmander", FIRE), _unit("bulbasaur", GRASS), _unit("squirtle", WATER)]
    candidates = [*team, _unit("golem", GROUND), _unit("pikachu", ELECTRIC)]

    picks = assign_counters(MATRIX, team, candidates)

    assert [pick.enemy.name for pick in picks] == [unit.name for unit in team]
    assert len({pick.counter.id for pick in picks}) == len(team)
    assert all(pick.advantage > 0 for pick in picks)


def test_assign_counters_reports_both_directions() -> None:
    team = [_unit("charmander", FIRE)]
    picks = assign_counters(MATRIX, team, [_unit("squirtle", WATER), _unit("golem", GROUND)])

    assert picks[0].counter.name == "squirtle"  # golem tambien pega x2, pero encaja x1
    assert picks[0].offense == 2.0  # le pega x2
    assert picks[0].incoming == 0.5  # y recibe x0.5
    assert picks[0].advantage == 2


def test_assign_counters_maximizes_the_team_total_not_each_pair() -> None:
    """Un emparejamiento codicioso fallaria aqui.

    X es el mejor contra de A (ventaja 3), pero si se lo queda, a B solo le llega Y con
    ventaja 0: total 3. Cediendo X a B y Y a A el total sube a 4.
    """
    a, b = _unit("a", 10), _unit("b", 20)
    x, y = _unit("x", 30), _unit("y", 40)
    matrix = {
        (30, 10): 4.0,
        (10, 30): 0.5,  # adv(x, a) = 2 - (-1) = 3
        (30, 20): 2.0,
        (20, 30): 0.5,  # adv(x, b) = 1 - (-1) = 2
        (40, 10): 2.0,
        (10, 40): 0.5,  # adv(y, a) = 1 - (-1) = 2
    }  # adv(y, b) = 0 - 0     = 0

    picks = assign_counters(matrix, [a, b], [x, y])

    assert sum(pick.advantage for pick in picks) == 4
    assert picks[0].counter.name == "y"  # a <- y
    assert picks[1].counter.name == "x"  # b <- x


def test_stats_only_break_ties() -> None:
    """Con la misma ventaja de tipo, gana el de mejor puntuacion de stats."""
    team = [_unit("charmander", FIRE)]
    weak = _unit("magikarp", WATER, power=5.0)
    strong = _unit("gyarados", WATER, power=90.0)

    picks = assign_counters(MATRIX, team, [weak, strong])

    assert picks[0].counter.name == "gyarados"


def test_assign_counters_needs_one_candidate_per_member() -> None:
    team = [_unit("a", FIRE), _unit("b", WATER)]
    with pytest.raises(ValueError, match="al menos 2"):
        assign_counters(MATRIX, team, [_unit("solo", GRASS)])


def test_empty_team_returns_nothing() -> None:
    assert assign_counters(MATRIX, [], [_unit("golem", GROUND)]) == []
