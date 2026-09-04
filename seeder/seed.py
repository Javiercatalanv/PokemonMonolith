"""Script de ingesta: descarga de la PokeAPI y carga en PostgreSQL.

Uso:
    python -m seeder.seed                 # 151 pokemon (primera generacion)
    python -m seeder.seed --limit 386     # hasta la tercera generacion
    python -m seeder.seed --drop          # recrea las tablas desde cero

Es idempotente: volver a ejecutarlo actualiza las filas existentes en vez de
duplicarlas (se usa el id de la PokeAPI como clave primaria).
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from seeder.models import Pokemon, PokemonForm, Type, TypeEffectiveness
from seeder.pokeapi_client import (
    DEFAULT_MULTIPLIER,
    FormData,
    PokeAPIClient,
    PokemonData,
    TypeData,
)

logger = logging.getLogger("seeder")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    # requests/urllib3 son muy ruidosos en DEBUG
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def build_engine(database_url: str | None = None) -> Engine:
    """Motor sincrono. La app usa asyncpg; el seeder, psycopg2."""
    url = database_url or settings.sync_dsn
    logger.info("Conectando a %s", url.rsplit("@", 1)[-1])  # no logear credenciales
    return create_engine(url, echo=False, future=True)


def init_db(engine: Engine, drop: bool = False) -> None:
    if drop:
        logger.warning("Borrando las tablas existentes (--drop)")
        Base.metadata.drop_all(engine)
    logger.info("Creando las tablas si no existen...")
    Base.metadata.create_all(engine)


# --- Carga de tipos ---


def seed_types(session: Session, types: list[TypeData]) -> dict[str, int]:
    """Inserta o actualiza los 18 tipos. Devuelve el mapa nombre -> id."""
    logger.info("Guardando %s tipos...", len(types))
    for type_data in types:
        logger.info("Guardando tipo %s...", type_data.name)
        session.merge(Type(id=type_data.id, name=type_data.name))
    session.flush()

    return {name: type_id for type_id, name in session.execute(select(Type.id, Type.name))}


def seed_effectiveness(
    session: Session,
    types: list[TypeData],
    type_ids: dict[str, int],
) -> int:
    """Construye la matriz completa 18x18 de efectividad.

    Lo que la PokeAPI no declara como relacion especial es dano normal (1.0),
    asi que se rellena explicitamente en vez de dejar huecos.
    """
    names = [type_data.name for type_data in types]
    logger.info("Guardando la matriz de efectividad (%sx%s)...", len(names), len(names))

    rows = 0
    for attacker in types:
        for defender_name in names:
            multiplier = attacker.damage_to.get(defender_name, DEFAULT_MULTIPLIER)
            session.merge(
                TypeEffectiveness(
                    attacker_id=type_ids[attacker.name],
                    defender_id=type_ids[defender_name],
                    damage_multiplier=multiplier,
                )
            )
            rows += 1
        logger.info("  %s -> %s relaciones", attacker.name, len(names))

    session.flush()
    return rows


# --- Carga de pokemon ---


def seed_pokemon(
    session: Session,
    pokemon: list[PokemonData],
    type_ids: dict[str, int],
) -> int:
    logger.info("Guardando %s pokemon...", len(pokemon))

    saved = 0
    for entry in pokemon:
        if entry.type1 not in type_ids:
            logger.warning("Se omite %s: tipo desconocido '%s'", entry.name, entry.type1)
            continue

        logger.info("Guardando %s...", entry.name.capitalize())
        session.merge(
            Pokemon(
                id=entry.id,
                name=entry.name,
                type1_id=type_ids[entry.type1],
                type2_id=type_ids.get(entry.type2) if entry.type2 else None,
                hp=entry.hp,
                attack=entry.attack,
                defense=entry.defense,
                sp_attack=entry.sp_attack,
                sp_defense=entry.sp_defense,
                speed=entry.speed,
                sprite_url=entry.sprite_url,
            )
        )
        saved += 1

    session.flush()
    return saved


# --- Carga de formas alternativas ---


def combat_profile(entry: PokemonData | FormData) -> tuple[object, ...]:
    """Lo unico que este proyecto mira de un pokemon: sus tipos y sus stats base."""
    return (
        entry.type1,
        entry.type2,
        entry.hp,
        entry.attack,
        entry.defense,
        entry.sp_attack,
        entry.sp_defense,
        entry.speed,
    )


def seed_forms(
    session: Session,
    forms: list[FormData],
    type_ids: dict[str, int],
    base_by_id: dict[int, PokemonData],
) -> int:
    """Guarda las formas que aportan un enfrentamiento nuevo y descarta el resto.

    El criterio no es una lista de nombres, sino el perfil de combate (tipos y stats).
    Una forma se guarda solo si su perfil no lo tiene ya ni la especie ni otra forma
    suya anterior, y eso resuelve dos casos de una vez:

    - Las gigantamax y los disfraces son identicos a su especie, asi que caen solos.
    - Minior tiene siete colores con los mismos tipos y stats, y Tatsugiri tres poses:
      sin deduplicar, el desplegable ofreceria seis y dos opciones que no cambian nada.

    Entran las megas, las primal, las regionales y las variantes con stats propios
    (deoxys-attack, rotom-heat, giratina-origin).
    """
    logger.info("Revisando %s formas alternativas...", len(forms))

    saved = 0
    unchanged = 0
    # especie -> perfiles ya cubiertos. El de la propia especie cuenta desde el principio.
    covered: dict[int, set[tuple[object, ...]]] = {}

    # Por id ascendente: ante dos formas iguales gana la canonica, que es la de id menor
    for form in sorted(forms, key=lambda entry: entry.id):
        base = base_by_id.get(form.base_id)
        if base is None:
            continue

        known = covered.setdefault(form.base_id, {combat_profile(base)})
        profile = combat_profile(form)
        if profile in known:
            logger.debug("  %s no aporta tipos ni stats nuevos: se omite", form.name)
            unchanged += 1
            continue

        if form.type1 not in type_ids:
            logger.warning("Se omite %s: tipo desconocido '%s'", form.name, form.type1)
            continue

        logger.info("Guardando forma %s (%s)...", form.name, form.label)
        session.merge(
            PokemonForm(
                id=form.id,
                pokemon_id=form.base_id,
                name=form.name,
                label=form.label,
                type1_id=type_ids[form.type1],
                type2_id=type_ids.get(form.type2) if form.type2 else None,
                hp=form.hp,
                attack=form.attack,
                defense=form.defense,
                sp_attack=form.sp_attack,
                sp_defense=form.sp_defense,
                speed=form.speed,
                sprite_url=form.sprite_url,
            )
        )
        known.add(profile)
        saved += 1

    session.flush()
    logger.info("  %s formas guardadas, %s descartadas por no aportar nada nuevo", saved, unchanged)
    return saved


# --- Orquestacion ---


def run(
    limit: int = 151,
    drop: bool = False,
    database_url: str | None = None,
    with_forms: bool = True,
) -> None:
    engine = build_engine(database_url)
    init_db(engine, drop=drop)

    with PokeAPIClient() as client:
        types = client.fetch_types()
        pokemon = client.fetch_pokemon(limit=limit)
        forms = client.fetch_forms({entry.id for entry in pokemon}) if with_forms else []

    session_factory = sessionmaker(bind=engine, future=True)
    # Una sola transaccion: si algo falla, no queda una carga a medias
    with session_factory() as session, session.begin():
        type_ids = seed_types(session, types)
        relations = seed_effectiveness(session, types, type_ids)
        saved = seed_pokemon(session, pokemon, type_ids)
        # Las formas cuelgan de `pokemon` por clave ajena, asi que van despues
        saved_forms = seed_forms(session, forms, type_ids, {p.id: p for p in pokemon})

    engine.dispose()

    logger.info("-" * 50)
    logger.info(
        "Listo: %s tipos, %s relaciones, %s pokemon, %s formas",
        len(type_ids),
        relations,
        saved,
        saved_forms,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingesta de datos de la PokeAPI a PostgreSQL")
    parser.add_argument(
        "--limit",
        type=int,
        default=151,
        help="Cuantos pokemon descargar (por defecto 151, la primera generacion)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Borra y recrea las tablas antes de cargar",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="DSN de PostgreSQL. Por defecto se toma del .env",
    )
    parser.add_argument(
        "--no-forms",
        action="store_true",
        help="No descargar las formas alternativas (megas, regionales...): ~330 peticiones menos",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Logging en DEBUG")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    try:
        run(
            limit=args.limit,
            drop=args.drop,
            database_url=args.database_url,
            with_forms=not args.no_forms,
        )
    except KeyboardInterrupt:
        logger.warning("Interrumpido por el usuario")
        return 130
    except Exception:
        logger.exception("La ingesta ha fallado")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
