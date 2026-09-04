"""Formas alternativas: listarlas, resolverlas y usarlas como rival."""

from httpx import AsyncClient


async def test_lists_the_forms_of_a_species(client: AsyncClient) -> None:
    forms = (await client.get("/pokemon/4/forms")).json()
    assert [form["name"] for form in forms] == ["charmander-mega"]

    mega = forms[0]
    assert mega["label"] == "Mega"
    assert mega["pokemon_id"] == 4
    assert mega["id"] == 10004


async def test_a_form_carries_its_own_types_and_stats(client: AsyncClient) -> None:
    """La tarjeta pinta los stats de la forma, no los de la especie."""
    base = (await client.get("/pokemon/4")).json()
    mega = (await client.get("/pokemon/4/forms")).json()[0]

    assert base["type2"] is None
    assert mega["type2"]["name"] == "water"
    assert mega["stat_total"] > base["stat_total"]


async def test_species_without_forms_returns_empty(client: AsyncClient) -> None:
    """Vacio significa que transformarse no le cambia nada, no que falte el dato."""
    assert (await client.get("/pokemon/1/forms")).json() == []


async def test_forms_can_be_asked_by_species_name(client: AsyncClient) -> None:
    by_name = (await client.get("/pokemon/charmander/forms")).json()
    by_id = (await client.get("/pokemon/4/forms")).json()
    assert by_name == by_id


async def test_forms_can_be_asked_from_the_form_itself(client: AsyncClient) -> None:
    """Con una forma seleccionada, el desplegable sigue pudiendo listar las hermanas."""
    from_form = (await client.get("/pokemon/charmander-mega/forms")).json()
    assert [form["name"] for form in from_form] == ["charmander-mega"]


async def test_unknown_species_forms_returns_404(client: AsyncClient) -> None:
    response = await client.get("/pokemon/9999/forms")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --- Resolver una forma como si fuera un pokemon mas ---


async def test_a_form_resolves_by_name(client: AsyncClient) -> None:
    body = (await client.get("/pokemon/charmander-mega")).json()
    assert body["id"] == 10004
    assert body["type2"]["name"] == "water"


async def test_a_form_resolves_by_id(client: AsyncClient) -> None:
    assert (await client.get("/pokemon/10004")).json()["name"] == "charmander-mega"


async def test_forms_stay_out_of_the_catalogue(client: AsyncClient) -> None:
    """Solo se ven al abrir su tarjeta: no cuentan como pokemon del catalogo."""
    listing = (await client.get("/pokemon")).json()
    assert listing["total"] == 5
    assert "charmander-mega" not in {item["name"] for item in listing["items"]}


async def test_forms_stay_out_of_the_search(client: AsyncClient) -> None:
    names = {p["name"] for p in (await client.get("/pokemon/search?q=charmander")).json()}
    assert names == {"charmander"}


# --- El contraequipo mira los tipos de la forma elegida ---


async def test_a_form_changes_the_matchup(client: AsyncClient) -> None:
    """Elegir la forma cambia el resultado, porque se enfrenta a otros tipos.

    Charmander base es fuego puro: squirtle le pega x2 y solo encaja x0.5, dos
    escalones de ventaja. Su mega es fuego/agua, que resiste el agua (2.0 * 0.5 = 1.0)
    sin dejar de encajarle x0.5, asi que la ventaja baja a uno: es mas dificil de
    contrarrestar, no menos.
    """
    against_base = (await client.get("/team/counters", params={"team": "4"})).json()
    against_mega = (await client.get("/team/counters", params={"team": "charmander-mega"})).json()

    assert against_base["picks"][0]["enemy"]["name"] == "charmander"
    assert against_mega["picks"][0]["enemy"]["name"] == "charmander-mega"

    assert against_base["total_advantage"] == 2
    assert against_mega["total_advantage"] == 1


async def test_counters_are_always_base_species(client: AsyncClient) -> None:
    """Se pueden armar rivales con formas, pero el generador no propone megas."""
    body = (await client.get("/team/counters", params={"team": "charmander-mega"})).json()
    assert body["picks"][0]["counter"]["name"] in {
        "bulbasaur",
        "charmander",
        "squirtle",
        "chikorita",
        "cyndaquil",
    }


async def test_excluding_the_team_also_drops_the_base_species(client: AsyncClient) -> None:
    """Elegir la mega descarta tambien al charmander de siempre: es el mismo bicho."""
    body = (
        await client.get(
            "/team/counters",
            params={"team": "charmander-mega", "exclude_team": "true"},
        )
    ).json()
    assert body["picks"][0]["counter"]["name"] != "charmander"
