"""El parseo de la PokeAPI se testea sin red, con payloads de ejemplo."""

from typing import Any

import pytest

from seeder.pokeapi_client import PokeAPIClient


def _payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 1,
        "name": "Bulbasaur",
        "types": [
            {"slot": 2, "type": {"name": "poison"}},
            {"slot": 1, "type": {"name": "grass"}},
        ],
        "stats": [
            {"stat": {"name": "hp"}, "base_stat": 45},
            {"stat": {"name": "attack"}, "base_stat": 49},
            {"stat": {"name": "defense"}, "base_stat": 49},
            {"stat": {"name": "special-attack"}, "base_stat": 65},
            {"stat": {"name": "special-defense"}, "base_stat": 65},
            {"stat": {"name": "speed"}, "base_stat": 45},
        ],
    }
    return base | overrides


def test_parse_orders_types_by_slot() -> None:
    """La API no garantiza el orden: el slot 1 debe acabar en type1."""
    data = PokeAPIClient._parse_pokemon(_payload())
    assert data.type1 == "grass"
    assert data.type2 == "poison"


def test_parse_normalizes_name_and_maps_stats() -> None:
    data = PokeAPIClient._parse_pokemon(_payload())
    assert data.name == "bulbasaur"
    assert (data.sp_attack, data.sp_defense) == (65, 65)


def test_parse_single_type_leaves_type2_none() -> None:
    payload = _payload(types=[{"slot": 1, "type": {"name": "fire"}}])
    data = PokeAPIClient._parse_pokemon(payload)
    assert data.type1 == "fire"
    assert data.type2 is None


def test_parse_rejects_malformed_payload() -> None:
    payload = _payload()
    del payload["stats"][0]  # falta el hp
    with pytest.raises(KeyError):
        PokeAPIClient._parse_pokemon(payload)
