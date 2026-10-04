"""Schemas transversales: paginacion, salud y respuestas de error."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Respuesta paginada estandar."""

    items: list[T] = Field(description="Registros de esta pagina")
    total: int = Field(description="Total de registros que cumplen el filtro", examples=[151])
    limit: int = Field(description="Registros por pagina pedidos", examples=[50])
    offset: int = Field(description="Registros saltados", examples=[0])


class HealthRead(BaseModel):
    """El proceso esta vivo. No toca la base de datos."""

    status: str = Field(examples=["ok"])
    environment: str = Field(description="Valor de ENVIRONMENT", examples=["local"])
    version: str = Field(examples=["0.1.0"])


class ReadinessRead(BaseModel):
    """El proceso esta vivo y la base de datos contesta."""

    status: str = Field(examples=["ready"])
    database: str = Field(examples=["ok"])


class ErrorDetail(BaseModel):
    code: str = Field(
        description="Identificador estable del error, pensado para el cliente",
        examples=["not_found"],
    )
    message: str = Field(
        description="Explicacion legible", examples=["No existe el pokemon 'missingno'"]
    )
    details: dict[str, Any] = Field(
        default={},
        description="Contexto adicional. En `validation_error` trae `fields` con cada fallo",
    )


class ErrorResponse(BaseModel):
    """Formato unico de error de toda la API, sea 404, 409, 422 o 500."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "not_found",
                    "message": "No existe el pokemon 'missingno'",
                    "details": {},
                }
            }
        }
    )

    error: ErrorDetail
