"""El endpoint que propone un equipo capaz de batir al tuyo, solo por tipos.

El dataset de `conftest` tiene 5 pokemon y 4 tipos, asi que aqui se usan equipos
pequenos; el emparejamiento en si se prueba a fondo en `tests/test_algorithms.py`.
"""

from httpx import AsyncClient


async def test_counters_one_pick_per_member(client: AsyncClient) -> None:
    response = await client.get("/team/counters", params={"team": ["bulbasaur", "squirtle"]})
    assert response.status_code == 200

    body = response.json()
    assert [pick["enemy"]["name"] for pick in body["picks"]] == ["bulbasaur", "squirtle"]
    assert len({pick["counter"]["id"] for pick in body["picks"]}) == 2


async def test_counters_pick_the_type_that_wins(client: AsyncClient) -> None:
    """A bulbasaur (planta/veneno) le gana el fuego.

    El fuego le pega x2 (2.0 a planta * 1.0 a veneno) y solo encaja x1: bulbasaur ataca
    con el mejor de sus dos tipos, y veneno contra fuego es neutro. Un escalon de ventaja.
    """
    body = (await client.get("/team/counters", params={"team": "bulbasaur"})).json()

    pick = body["picks"][0]
    assert pick["counter"]["type1"]["name"] == "fire"
    assert pick["offense_multiplier"] == 2.0
    assert pick["incoming_multiplier"] == 1.0
    assert pick["advantage"] == 1
    assert pick["label"] == "muy eficaz"
    assert body["total_advantage"] == 1


async def test_team_accepts_ids_and_names_mixed(client: AsyncClient) -> None:
    by_name = (await client.get("/team/counters", params={"team": "bulbasaur"})).json()
    by_id = (await client.get("/team/counters", params={"team": "1"})).json()
    assert by_name == by_id


async def test_exclude_team_keeps_your_own_pokemon_out(client: AsyncClient) -> None:
    """charmander es el mejor contra de bulbasaur, pero tambien esta en el equipo."""
    team = ["bulbasaur", "charmander"]
    included = (await client.get("/team/counters", params={"team": team})).json()
    assert "charmander" in {pick["counter"]["name"] for pick in included["picks"]}

    excluded = (
        await client.get("/team/counters", params={"team": team, "exclude_team": "true"})
    ).json()
    assert {pick["counter"]["name"] for pick in excluded["picks"]}.isdisjoint(team)


async def test_unknown_member_is_a_404(client: AsyncClient) -> None:
    response = await client.get("/team/counters", params={"team": "mewtwo"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_team_larger_than_six_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/team/counters", params={"team": ["bulbasaur"] * 7})
    assert response.status_code == 422


async def test_empty_team_is_rejected(client: AsyncClient) -> None:
    assert (await client.get("/team/counters")).status_code == 422


async def test_not_enough_pokemon_loaded_is_a_409(client: AsyncClient) -> None:
    """Con 5 pokemon en la BD no se puede armar un contraequipo de 6."""
    team = ["1", "4", "7", "152", "155", "1"]
    response = await client.get("/team/counters", params={"team": team})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_data"
