"""Punto de entrada de la aplicacion FastAPI."""

import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)

API_DESCRIPTION = """
API de solo lectura sobre los datos de la [PokeAPI](https://pokeapi.co) que carga el
seeder en PostgreSQL. La API nunca sale a internet: si falta algo, hay que volver a
pasar el seeder.

**Identificadores.** Donde se pide un `identifier` vale el numero de Pokedex, el id de
una forma alternativa (10001+) o el nombre, sin distinguir mayusculas.

**Errores.** Todas las respuestas de error comparten el formato `ErrorResponse`:

```json
{"error": {"code": "not_found", "message": "No existe el pokemon 'missingno'", "details": {}}}
```

| HTTP | `code` | Cuando |
|---|---|---|
| 404 | `not_found` | El pokemon, la forma o el tipo no existe |
| 409 | `insufficient_data` | La peticion es valida, pero no hay bastantes pokemon cargados |
| 422 | `validation_error` | Parametros invalidos; `details.fields` dice cuales |
| 500 | `internal_error` | Error inesperado |

**Cabeceras.** Cada respuesta trae `X-Request-ID` (se reutiliza el de la peticion si
viene) y `X-Process-Time-Ms`.
"""

OPENAPI_TAGS = [
    {"name": "health", "description": "Sondas de liveness y readiness para orquestadores."},
    {"name": "pokemon", "description": "Catalogo, busqueda, ranking, formas y efectividad."},
    {"name": "generations", "description": "Catalogo de generaciones para el selector."},
    {
        "name": "team",
        "description": "Generador de contraequipos a partir de la efectividad de tipos.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("Arrancando %s (env=%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield
    from app.db.session import dispose_engine

    await dispose_engine()
    logger.info("Aplicacion detenida")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        summary="Datos de la PokeAPI servidos desde PostgreSQL, con algoritmos de tipos y stats.",
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Asigna un request-id y registra latencia de cada peticion."""
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        logger.info(
            "%s %s -> %s (%.2f ms) request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"service": settings.PROJECT_NAME, "docs": "/docs"}

    return app


app = create_app()
