from httpx import AsyncClient


async def test_list_returns_seeded_data(client: AsyncClient) -> None:
    body = (await client.get("/pokemon")).json()
    assert body["total"] == 3
    names = {item["name"] for item in body["items"]}
    assert names == {"bulbasaur", "charmander", "squirtle"}


async def test_detail_includes_both_types_and_stat_total(client: AsyncClient) -> None:
    body = (await client.get("/pokemon/1")).json()
    assert body["type1"]["name"] == "grass"
    assert body["type2"]["name"] == "poison"
    assert body["stat_total"] == 45 + 49 + 49 + 65 + 65 + 45


async def test_single_type_pokemon_has_null_type2(client: AsyncClient) -> None:
    assert (await client.get("/pokemon/4")).json()["type2"] is None


async def test_by_type_matches_primary_and_secondary(client: AsyncClient) -> None:
    poison = (await client.get("/pokemon/by-type/poison")).json()
    assert [item["name"] for item in poison] == ["bulbasaur"]  # lo tiene como secundario


async def test_by_type_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.get("/pokemon/by-type/ghost")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_matchup_combines_both_defender_types(client: AsyncClient) -> None:
    """Fuego contra planta/veneno: 2.0 * 1.0 = 2.0."""
    body = (await client.get("/pokemon/1/matchup/fire")).json()
    assert body == {
        "attacker_type": "fire",
        "defender": "bulbasaur",
        "multiplier": 2.0,
        "label": "muy eficaz",
    }


async def test_matchup_resisted(client: AsyncClient) -> None:
    """Agua contra fuego mono-tipo: 2.0."""
    body = (await client.get("/pokemon/4/matchup/water")).json()
    assert body["multiplier"] == 2.0
    body = (await client.get("/pokemon/7/matchup/fire")).json()
    assert body["multiplier"] == 0.5
    assert body["label"] == "poco eficaz"


async def test_matchup_unknown_type_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/pokemon/1/matchup/dragon")).status_code == 404


async def test_top_is_ordered_by_score(client: AsyncClient) -> None:
    top = (await client.get("/pokemon/top", params={"limit": 5})).json()
    scores = [item["score"] for item in top]
    assert scores == sorted(scores, reverse=True)


async def test_percentile(client: AsyncClient) -> None:
    body = (await client.get("/pokemon/1/percentile")).json()
    assert 0.0 <= body["percentile"] <= 100.0


async def test_get_missing_returns_404(client: AsyncClient) -> None:
    response = await client.get("/pokemon/9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
