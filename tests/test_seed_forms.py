"""El filtro que decide que formas merecen guardarse."""

from seeder.pokeapi_client import FormData, PokemonData
from seeder.seed import combat_profile

BASE = PokemonData(
    id=6,
    name="charizard",
    type1="fire",
    type2="flying",
    hp=78,
    attack=84,
    defense=78,
    sp_attack=109,
    sp_defense=85,
    speed=100,
)


def _form(**overrides: object) -> FormData:
    fields: dict[str, object] = {
        "id": 10196,
        "base_id": 6,
        "name": "charizard-gmax",
        "label": "Gmax",
        "type1": "fire",
        "type2": "flying",
        "hp": 78,
        "attack": 84,
        "defense": 78,
        "sp_attack": 109,
        "sp_defense": 85,
        "speed": 100,
    }
    fields.update(overrides)
    return FormData(**fields)  # type: ignore[arg-type]


def test_gigantamax_is_indistinguishable_from_the_base() -> None:
    """Por eso el seeder la descarta: no cambia ni tipos ni stats."""
    assert combat_profile(_form()) == combat_profile(BASE)


def test_a_mega_differs_because_of_its_stats() -> None:
    mega = _form(id=10035, name="charizard-mega-y", label="Mega Y", sp_attack=159)
    assert combat_profile(mega) != combat_profile(BASE)


def test_a_regional_form_differs_because_of_its_types() -> None:
    galar = _form(id=10161, name="meowth-galar", label="Galar", type1="steel", type2=None)
    assert combat_profile(galar) != combat_profile(BASE)


# --- Deduplicado dentro de la especie ---


class _FakeSession:
    """Recoge lo que `seed_forms` guardaria, sin base de datos."""

    def __init__(self) -> None:
        self.merged: list[object] = []

    def merge(self, entity: object) -> object:
        self.merged.append(entity)
        return entity

    def flush(self) -> None:
        pass


TYPE_IDS = {"fire": 10, "water": 11, "flying": 3, "steel": 9}


def _seed(forms: list[FormData]) -> list[str]:
    from seeder.seed import seed_forms

    session = _FakeSession()
    seed_forms(session, forms, TYPE_IDS, {BASE.id: BASE})  # type: ignore[arg-type]
    return [entity.name for entity in session.merged]  # type: ignore[attr-defined]


def test_a_form_identical_to_its_species_is_dropped() -> None:
    assert _seed([_form()]) == []


def test_only_the_first_of_several_identical_forms_survives() -> None:
    """Minior tiene siete colores con los mismos tipos y stats: sobra con uno."""
    colours = [
        _form(id=10130, name="minior-blue", label="Blue", type1="water", type2=None),
        _form(id=10131, name="minior-green", label="Green", type1="water", type2=None),
        _form(id=10132, name="minior-red", label="Red", type1="water", type2=None),
    ]
    assert _seed(colours) == ["minior-blue"]


def test_the_lowest_id_wins_whatever_the_order() -> None:
    """El resultado no puede depender del orden en que llegaron de la API."""
    pair = [
        _form(id=10227, name="urshifu-rapid-strike-gmax", label="Rapid Strike Gmax", type1="water"),
        _form(id=10191, name="urshifu-rapid-strike", label="Rapid Strike", type1="water"),
    ]
    assert _seed(pair) == ["urshifu-rapid-strike"]


def test_forms_that_do_differ_are_all_kept() -> None:
    distinct = [
        _form(id=10034, name="charizard-mega-x", label="Mega X", type1="fire", type2="steel"),
        _form(id=10035, name="charizard-mega-y", label="Mega Y", sp_attack=159),
    ]
    assert _seed(distinct) == ["charizard-mega-x", "charizard-mega-y"]
