"""Extraccion de datos desde la PokeAPI.

Este modulo solo lee: no toca la base de datos. Devuelve dataclasses ya
normalizadas para que `seed.py` se limite a insertarlas.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from seeder.models import CANONICAL_TYPES

logger = logging.getLogger(__name__)

BASE_URL = "https://pokeapi.co/api/v2"

# Retardo entre peticiones para no abusar de la API publica
REQUEST_DELAY = 0.2

# Traduccion de las relaciones de dano de la PokeAPI a multiplicadores
DAMAGE_RELATIONS: dict[str, float] = {
    "no_damage_to": 0.0,
    "half_damage_to": 0.5,
    "double_damage_to": 2.0,
}
DEFAULT_MULTIPLIER = 1.0


@dataclass(frozen=True)
class TypeData:
    id: int
    name: str
    # nombre del tipo defensor -> multiplicador cuando ESTE tipo ataca.
    # Solo contiene las relaciones distintas de 1.0; el resto se rellena en seed.py.
    damage_to: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PokemonData:
    id: int
    name: str
    type1: str
    type2: str | None
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int


class PokeAPIClient:
    """Cliente HTTP con reintentos y retardo entre peticiones."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        *,
        delay: float = REQUEST_DELAY,
        timeout: float = 15.0,
        retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "newmonoliopokemon-seeder/0.1"})
        # Reintenta los errores transitorios (incluido el 429 de rate limit),
        # esperando 0.5s, 1s, 2s... entre intentos.
        retry = Retry(
            total=retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> PokeAPIClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        response = self.session.get(url, params=params or None, timeout=self.timeout)
        response.raise_for_status()
        # El retardo va DESPUES de la peticion: asi no se paga antes de la primera
        time.sleep(self.delay)
        data: dict[str, Any] = response.json()
        return data

    # --- Tipos ---

    def fetch_types(self) -> list[TypeData]:
        """Devuelve los 18 tipos canonicos con sus relaciones de dano ofensivas."""
        logger.info("Descargando listado de tipos...")
        index = self._get("/type", limit=100)

        entries = [entry for entry in index["results"] if entry["name"] in CANONICAL_TYPES]
        logger.info("Encontrados %s tipos canonicos", len(entries))

        types: list[TypeData] = []
        for position, entry in enumerate(entries, start=1):
            name = entry["name"]
            logger.info("[%s/%s] Descargando tipo %s...", position, len(entries), name)
            detail = self._get(f"/type/{name}")

            damage_to: dict[str, float] = {}
            relations = detail["damage_relations"]
            for relation, multiplier in DAMAGE_RELATIONS.items():
                for target in relations[relation]:
                    if target["name"] in CANONICAL_TYPES:
                        damage_to[target["name"]] = multiplier

            types.append(TypeData(id=int(detail["id"]), name=name, damage_to=damage_to))

        return types

    # --- Pokemon ---

    def fetch_pokemon(self, limit: int = 151, offset: int = 0) -> list[PokemonData]:
        """Descarga `limit` pokemon con sus stats base y tipos."""
        logger.info("Descargando listado de pokemon (limit=%s, offset=%s)...", limit, offset)
        index = self._get("/pokemon", limit=limit, offset=offset)
        entries = index["results"]

        pokemon: list[PokemonData] = []
        for position, entry in enumerate(entries, start=1):
            name = entry["name"]
            logger.info("[%s/%s] Descargando %s...", position, len(entries), name)
            try:
                pokemon.append(self._parse_pokemon(self._get(f"/pokemon/{name}")))
            except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
                # Un pokemon con formato raro no debe tumbar toda la ingesta
                logger.warning("Se omite %s: %s", name, exc)

        return pokemon

    @staticmethod
    def _parse_pokemon(payload: dict[str, Any]) -> PokemonData:
        """Traduce la respuesta de la PokeAPI a `PokemonData`.

        Unico punto que conoce el formato ajeno: si cambia la API, se toca aqui.
        """
        stats = {entry["stat"]["name"]: int(entry["base_stat"]) for entry in payload["stats"]}
        types = sorted(payload["types"], key=lambda entry: entry["slot"])

        return PokemonData(
            id=int(payload["id"]),
            name=str(payload["name"]).lower(),
            type1=types[0]["type"]["name"],
            type2=types[1]["type"]["name"] if len(types) > 1 else None,
            hp=stats["hp"],
            attack=stats["attack"],
            defense=stats["defense"],
            sp_attack=stats["special-attack"],
            sp_defense=stats["special-defense"],
            speed=stats["speed"],
        )
