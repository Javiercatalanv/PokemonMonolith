# NewMonolioPokemon — Backend

Backend en Python que **ingesta datos de la PokéAPI**, los guarda en **PostgreSQL** y los
sirve vía **FastAPI**, aplicando algoritmos de dominio (puntuación de stats, efectividad
de tipos) sobre lo almacenado.

```
PokéAPI  ──>  seeder/     descarga + carga (script, sincrono)
                  │
                  v
     PostgreSQL (en Docker)
                  │
                  v
               app/       API de lectura + algoritmos (async)
```

La ingesta y la API están separadas a propósito: el seeder es un proceso que se lanza
cuando toca, no una ruta HTTP. La API nunca sale a internet.

## Esquema

| Tabla | Columnas |
|---|---|
| `types` | `id`, `name` — los 18 tipos canónicos, con el id de la PokéAPI |
| `type_effectiveness` | `attacker_id`, `defender_id`, `damage_multiplier` — matriz **completa** 18×18 (324 filas) |
| `pokemon` | `id`, `name`, `type1_id`, `type2_id` (nullable), `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`, `speed` |

`damage_multiplier` toma los valores `0.0` (inmune), `0.5`, `1.0`, `2.0`. Se guardan también
los `1.0` para que consultar una efectividad sea un JOIN directo, sin asumir defaults.

## Estructura

```
.
├── docker-compose.yml          # PostgreSQL
├── seeder/                     # ingesta (sincrono: requests + psycopg2)
│   ├── models.py               # las 3 tablas SQLAlchemy
│   ├── pokeapi_client.py       # descarga y parseo de la PokéAPI
│   └── seed.py                 # script ejecutable que orquesta todo
├── app/                        # API (async: FastAPI + asyncpg)
│   ├── main.py
│   ├── api/v1/endpoints/       # health.py, pokemon.py
│   ├── core/                   # config.py, logging.py, exceptions.py
│   ├── db/                     # base.py (Base declarativa), session.py
│   ├── models/__init__.py      # reexporta las tablas de seeder/models.py
│   ├── schemas/                # contratos de salida (Pydantic)
│   ├── repositories/           # consultas SQL
│   └── services/
│       ├── algorithms.py       # funciones puras: sin I/O, sin BD
│       └── pokemon.py          # orquestacion
├── tests/
└── .env.example
```

Las tablas se definen **una sola vez**, en `seeder/models.py`, sobre la `Base` declarativa
de `app/db/base.py`. `app/models/__init__.py` las reexporta: un único `metadata`, sin
definiciones duplicadas.

## Puesta en marcha

Requiere Python 3.11+ y Docker.

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### 1. Base de datos

PostgreSQL vive en un contenedor; la API y el seeder corren en tu maquina y se
conectan por `localhost`.

```bash
docker compose up -d          # levantar
docker compose ps             # ver el estado
docker compose logs -f db     # ver los logs
docker compose down           # parar, conservando los datos
docker compose down -v        # parar y BORRAR los datos
```

El contenedor publica el **puerto 5435** del host (el 5432 y los siguientes suelen
estar ocupados por otros proyectos). Dentro del contenedor sigue siendo el 5432.
Si quieres otro, cambia `POSTGRES_PORT` en tu `.env` y afecta a las dos cosas a la vez.

Los datos viven en el volumen `pokemon_postgres_data`, asi que sobreviven a un
`docker compose down`. Solo `-v` los borra.

Una consola SQL contra el contenedor:

```bash
docker exec -it pokemon_db psql -U postgres -d newmonoliopokemon
```

### 2. Ingesta

```bash
.venv/bin/python -m seeder.seed               # 151 pokemon (generacion 1)
.venv/bin/python -m seeder.seed --limit 1025  # las 9 generaciones (~4 min)
.venv/bin/python -m seeder.seed --drop        # recrea las tablas desde cero
.venv/bin/python -m seeder.seed -v            # logging en DEBUG
```

#### Generaciones

`--limit` corta por la Pokedex nacional, y cada generacion es un tramo contiguo de
ella, asi que el limite decide hasta donde llegas:

| Gen | Region | Ids | Especies | `--limit` |
|---|---|---|---|---|
| 1 | Kanto | 1 – 151 | 151 | `151` |
| 2 | Johto | 152 – 251 | 100 | `251` |
| 3 | Hoenn | 252 – 386 | 135 | `386` |
| 4 | Sinnoh | 387 – 493 | 107 | `493` |
| 5 | Unova | 494 – 649 | 156 | `649` |
| 6 | Kalos | 650 – 721 | 72 | `721` |
| 7 | Alola | 722 – 809 | 88 | `809` |
| 8 | Galar | 810 – 905 | 96 | `905` |
| 9 | Paldea | 906 – 1025 | 120 | `1025` |

**No pases de 1025.** A partir de ahi la PokeAPI devuelve formas alternativas con
ids 10001+ (`deoxys-attack`, `charizard-mega-x`...), que no son especies nuevas.

Como la ingesta es idempotente, puedes ampliar cuando quieras: lanzarlo con
`--limit 1025` sobre los 151 que ya tienes completa el resto sin duplicar nada.

El script crea las tablas si no existen, así que es también el inicializador de la BD.

Salida:

```
12:20:16 | INFO    | [10/18] Descargando tipo fire...
12:20:27 | INFO    | Guardando tipo fire...
12:20:27 | INFO    | Guardando la matriz de efectividad (18x18)...
12:20:49 | INFO    | Guardando Bulbasaur...
12:20:49 | INFO    | Listo: 18 tipos, 324 relaciones, 151 pokemon
```

Detalles:

- **Idempotente.** Usa el id de la PokéAPI como clave primaria y hace `merge`, así que
  reejecutarlo actualiza en vez de duplicar.
- **Una sola transacción.** Si algo falla a mitad no queda una carga parcial.
- **Amable con la API.** `time.sleep(0.2)` entre peticiones, más reintentos con backoff
  exponencial ante 429/5xx.
- **Tolerante a fallos puntuales.** Un pokemon con formato inesperado se omite con un
  warning en vez de tumbar la ingesta.

### 3. API

```bash
.venv/bin/uvicorn app.main:app --reload
```

Documentación interactiva en http://localhost:8000/docs

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/health/ready` | Readiness (comprueba la BD) |
| GET | `/api/v1/generations` | Las 9 generaciones y cuantos hay cargados de cada una |
| GET | `/api/v1/pokemon` | Listado paginado, filtrable con `?generation=N` |
| GET | `/api/v1/pokemon/top` | Ranking por puntuación combinada de stats |
| GET | `/api/v1/pokemon/by-type/{type}` | Pokémon de un tipo (primario o secundario) |
| GET | `/api/v1/pokemon/{id}` | Detalle con ambos tipos y `stat_total` |
| GET | `/api/v1/pokemon/{id}/percentile` | Percentil de su puntuación |
| GET | `/api/v1/pokemon/{id}/matchup/{tipo}` | Efectividad de un tipo atacante contra él |

El matchup multiplica los dos tipos del defensor, como en el juego: fuego contra
planta/veneno es `2.0 × 1.0 = 2.0`; contra planta/acero, `2.0 × 2.0 = 4.0`.

### Selector de generacion

`GET /api/v1/generations` devuelve el catalogo con `loaded`, cuantos pokemon de esa
generacion hay ahora mismo en la base de datos:

```json
[{"number": 1, "region": "kanto", "first_id": 1, "last_id": 151,
  "total_species": 151, "loaded": 151},
 {"number": 4, "region": "sinnoh", "first_id": 387, "last_id": 493,
  "total_species": 107, "loaded": 0}]
```

Asi el frontend puede desactivar las generaciones que el seeder aun no ha traido en
vez de ofrecer un filtro que devuelve una lista vacia. Filtrar es
`GET /api/v1/pokemon?generation=2`.

## Dónde va cada cosa

| Quieres… | Toca… |
|---|---|
| Cambiar de API de origen | `seeder/pokeapi_client.py::_parse_pokemon` |
| Ajustar el retardo o los reintentos | `seeder/pokeapi_client.py` (`REQUEST_DELAY`) |
| Añadir un algoritmo | `app/services/algorithms.py` — funciones puras |
| Una consulta SQL nueva | `app/repositories/pokemon.py` |
| Una columna nueva | `seeder/models.py` + `app/schemas/pokemon.py` |

## Configuración

Todo sale de `.env` (ver `.env.example`). El seeder es síncrono (`psycopg2`) y la API
asíncrona (`asyncpg`); defines **un solo** DSN con `+asyncpg` y `Settings.sync_dsn`
lo convierte para el seeder.

## Tests

```bash
.venv/bin/pytest
```

No necesitan PostgreSQL ni salir a internet: SQLite en memoria con un dataset mínimo, y
el parseo de la PokéAPI se prueba con payloads de ejemplo.

## Nota sobre migraciones

Las tablas se crean con `Base.metadata.create_all` desde el seeder. Cuando el esquema
empiece a cambiar en un entorno con datos que no puedes perder, mete Alembic.
