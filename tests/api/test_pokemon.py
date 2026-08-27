from httpx import AsyncClient


async def test_list_returns_seeded_data(client: AsyncClient) -> None:
    body = (await client.get("/pokemon")).json()
    assert body["total"] == 5
    names = {item["name"] for item in body["items"]}
    assert names == {"bulbasaur", "charmander", "squirtle", "chikorita", "cyndaquil"}


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


# --- Filtro por generacion ---


async def test_filter_by_generation(client: AsyncClient) -> None:
    gen1 = (await client.get("/pokemon", params={"generation": 1})).json()
    assert gen1["total"] == 3
    assert {item["name"] for item in gen1["items"]} == {
        "bulbasaur",
        "charmander",
        "squirtle",
    }

    gen2 = (await client.get("/pokemon", params={"generation": 2})).json()
    assert gen2["total"] == 2
    assert {item["name"] for item in gen2["items"]} == {"chikorita", "cyndaquil"}


async def test_empty_generation_returns_empty_page(client: AsyncClient) -> None:
    """Una generacion que el seeder aun no ha traido no es un error, es una pagina vacia."""
    body = (await client.get("/pokemon", params={"generation": 9})).json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_generation_filter_respects_pagination(client: AsyncClient) -> None:
    body = (await client.get("/pokemon", params={"generation": 1, "limit": 2})).json()
    assert body["total"] == 3  # el total es el de la generacion, no el de la pagina
    assert len(body["items"]) == 2


async def test_generation_out_of_range_is_rejected(client: AsyncClient) -> None:
    assert (await client.get("/pokemon", params={"generation": 0})).status_code == 422
    assert (await client.get("/pokemon", params={"generation": 10})).status_code == 422


# --- Catalogo de generaciones ---


async def test_generations_catalog(client: AsyncClient) -> None:
    body = (await client.get("/generations")).json()
    assert len(body) == 9

    first = body[0]
    assert first["number"] == 1
    assert first["region"] == "kanto"
    assert (first["first_id"], first["last_id"]) == (1, 151)
    assert first["total_species"] == 151


async def test_generations_report_what_is_loaded(client: AsyncClient) -> None:
    """El frontend usa `loaded` para desactivar las generaciones sin datos."""
    body = (await client.get("/generations")).json()
    loaded = {gen["number"]: gen["loaded"] for gen in body}
    assert loaded[1] == 3
    assert loaded[2] == 2
    assert sum(loaded.values()) == 5
    assert loaded[9] == 0
