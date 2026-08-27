"""Los algoritmos son funciones puras: se testean sin base de datos ni red."""

import pytest

from app.services.algorithms import (
    combined_effectiveness,
    compute_power_score,
    effectiveness_label,
    percentile,
    rank_by_score,
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
