# NewMonolioPokemon — Backend

Backend en Python que **ingesta datos de la PokéAPI**, los guarda en **PostgreSQL** y los
sirve vía **FastAPI**, aplicando algoritmos de dominio (puntuación de stats, efectividad
de tipos) sobre lo almacenado.

```
PokéAPI  ──>  seeder/     descarga + carga (script, sincrono)
                  │
                  v
             PostgreSQL
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

Requiere Python 3.11+ y un PostgreSQL accesible.

```bash
cp .env.example .env          # ajusta las credenciales de PostgreSQL
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### 1. Ingesta

```bash
.venv/bin/python -m seeder.seed              # 151 pokemon (primera generacion)
.venv/bin/python -m seeder.seed --limit 386  # hasta la tercera generacion
.venv/bin/python -m seeder.seed --drop       # recrea las tablas desde cero
.venv/bin/python -m seeder.seed -v           # logging en DEBUG
```

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

### 2. API

```bash
.venv/bin/uvicorn app.main:app --reload
```

Documentación interactiva en http://localhost:8000/docs

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/health` | Liveness |
| GET | `/api/v1/health/ready` | Readiness (comprueba la BD) |
| GET | `/api/v1/pokemon` | Listado paginado |
| GET | `/api/v1/pokemon/top` | Ranking por puntuación combinada de stats |
| GET | `/api/v1/pokemon/by-type/{type}` | Pokémon de un tipo (primario o secundario) |
| GET | `/api/v1/pokemon/{id}` | Detalle con ambos tipos y `stat_total` |
| GET | `/api/v1/pokemon/{id}/percentile` | Percentil de su puntuación |
| GET | `/api/v1/pokemon/{id}/matchup/{tipo}` | Efectividad de un tipo atacante contra él |

El matchup multiplica los dos tipos del defensor, como en el juego: fuego contra
planta/veneno es `2.0 × 1.0 = 2.0`; contra planta/acero, `2.0 × 2.0 = 4.0`.

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
