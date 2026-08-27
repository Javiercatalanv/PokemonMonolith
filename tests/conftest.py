"""Fixtures compartidas: SQLite en memoria con un dataset minimo ya sembrado.

Los tests no tocan PostgreSQL ni salen a internet.
"""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models import Pokemon, Type, TypeEffectiveness

# Subconjunto de tipos suficiente para probar la efectividad combinada
TYPES = {"fire": 10, "water": 11, "grass": 12, "poison": 4}

# atacante -> defensor -> multiplicador (lo que no aparece es 1.0)
EFFECTIVENESS = {
    "fire": {"grass": 2.0, "water": 0.5, "fire": 0.5, "poison": 1.0},
    "water": {"fire": 2.0, "grass": 0.5, "water": 0.5, "poison": 1.0},
    "grass": {"water": 2.0, "fire": 0.5, "grass": 0.5, "poison": 1.0},
    "poison": {"grass": 2.0, "fire": 1.0, "water": 1.0, "poison": 0.5},
}


async def _seed(session: AsyncSession) -> None:
    for name, type_id in TYPES.items():
        session.add(Type(id=type_id, name=name))
    await session.flush()

    for attacker, relations in EFFECTIVENESS.items():
        for defender, multiplier in relations.items():
            session.add(
                TypeEffectiveness(
                    attacker_id=TYPES[attacker],
                    defender_id=TYPES[defender],
                    damage_multiplier=multiplier,
                )
            )

    session.add_all(
        [
            # planta/veneno: el fuego le hace 2.0 * 1.0 = 2.0
            Pokemon(
                id=1,
                name="bulbasaur",
                type1_id=TYPES["grass"],
                type2_id=TYPES["poison"],
                hp=45,
                attack=49,
                defense=49,
                sp_attack=65,
                sp_defense=65,
                speed=45,
            ),
            Pokemon(
                id=4,
                name="charmander",
                type1_id=TYPES["fire"],
                type2_id=None,
                hp=39,
                attack=52,
                defense=43,
                sp_attack=60,
                sp_defense=50,
                speed=65,
            ),
            Pokemon(
                id=7,
                name="squirtle",
                type1_id=TYPES["water"],
                type2_id=None,
                hp=44,
                attack=48,
                defense=65,
                sp_attack=50,
                sp_defense=64,
                speed=43,
            ),
        ]
    )
    await session.flush()


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        await _seed(s)
        yield s


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as ac:
        yield ac

    app.dependency_overrides.clear()
