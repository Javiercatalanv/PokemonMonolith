"""El parseo de la PokeAPI se testea sin red, con payloads de ejemplo."""

from typing import Any

import pytest

from seeder.pokeapi_client import PokeAPIClient, form_label


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


def test_parse_extracts_sprite_url() -> None:
    payload = _payload(
        sprites={
            "front_default": "https://img.pokeapi.co/sprite.png",
            "other": {
                "official-artwork": {
                    "front_default": "https://img.pokeapi.co/artwork.png"
                }
            },
        }
    )
    data = PokeAPIClient._parse_pokemon(payload)
    assert data.sprite_url == "https://img.pokeapi.co/artwork.png"


# --- Formas alternativas ---


def test_form_label_strips_the_species_name() -> None:
    assert form_label("charizard-mega-x", "charizard") == "Mega X"
    assert form_label("raichu-alola", "raichu") == "Alola"
    assert form_label("rotom-heat", "rotom") == "Heat"


def test_form_label_falls_back_to_the_whole_name() -> None:
    """Si el nombre no empieza por la especie, mejor algo legible que una cadena vacia."""
    assert form_label("mega-charizard", "charizard") == "Mega Charizard"


def test_parse_form_records_the_species_it_belongs_to() -> None:
    payload = {
        "id": 10034,
        "name": "charizard-mega-x",
        "species": {"name": "charizard", "url": "https://pokeapi.co/api/v2/pokemon-species/6/"},
        "types": [
            {"slot": 1, "type": {"name": "fire"}},
            {"slot": 2, "type": {"name": "dragon"}},
        ],
        "stats": [
            {"stat": {"name": "hp"}, "base_stat": 78},
            {"stat": {"name": "attack"}, "base_stat": 130},
            {"stat": {"name": "defense"}, "base_stat": 111},
            {"stat": {"name": "special-attack"}, "base_stat": 130},
            {"stat": {"name": "special-defense"}, "base_stat": 85},
            {"stat": {"name": "speed"}, "base_stat": 100},
        ],
        "sprites": {"front_default": "https://img.pokeapi.co/mega-x.png"},
    }

    form = PokeAPIClient._parse_form(payload)

    assert form.id == 10034
    assert form.base_id == 6
    assert form.label == "Mega X"
    assert (form.type1, form.type2) == ("fire", "dragon")
    assert form.attack == 130
