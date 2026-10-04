"""Respuestas de error para la documentacion OpenAPI.

Todas usan `ErrorResponse`, el formato que emiten los handlers de
`app/core/exceptions.py`. Sin declarar el 422, Swagger mostraria el
`HTTPValidationError` por defecto de FastAPI, que esta API nunca devuelve.
"""

from typing import Any

from app.schemas.common import ErrorResponse

Responses = dict[int | str, dict[str, Any]]


def error(description: str) -> dict[str, Any]:
    return {"model": ErrorResponse, "description": description}


VALIDATION_ERROR: Responses = {
    422: error("Parametros invalidos (`validation_error`); `details.fields` dice cuales"),
}

INTERNAL_ERROR: Responses = {
    500: error("Error inesperado (`internal_error`)"),
}
