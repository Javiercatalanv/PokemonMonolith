"""Schemas transversales: paginacion y respuestas de error."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Respuesta paginada estandar."""

    items: list[T]
    total: int = Field(description="Total de registros que cumplen el filtro")
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail
