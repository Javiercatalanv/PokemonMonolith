from typing import Any

import pytest
from httpx import AsyncClient

from app.main import create_app

ERROR_REF = "#/components/schemas/ErrorResponse"


@pytest.fixture(scope="module")
def spec() -> dict[str, Any]:
    return create_app().openapi()


def _schema_ref(operation: dict[str, Any], status: str) -> str:
    return operation["responses"][status]["content"]["application/json"]["schema"]["$ref"]


def test_every_operation_is_documented(spec: dict[str, Any]) -> None:
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            assert operation.get("summary"), f"{method.upper()} {path} sin summary"
            assert operation.get("tags"), f"{method.upper()} {path} sin tag"
            ok = operation["responses"]["200"]["content"]["application/json"]["schema"]
            assert ok, f"{method.upper()} {path} sin schema de respuesta"


def test_errors_use_the_real_error_format(spec: dict[str, Any]) -> None:
    """El 422 debe documentar `ErrorResponse`, no el `HTTPValidationError` de FastAPI."""
    assert "HTTPValidationError" not in spec["components"]["schemas"]

    for path, methods in spec["paths"].items():
        for operation in methods.values():
            for status in operation["responses"]:
                if status.startswith(("4", "5")):
                    assert _schema_ref(operation, status) == ERROR_REF, f"{path} -> {status}"


def test_path_parameters_are_described(spec: dict[str, Any]) -> None:
    for path, methods in spec["paths"].items():
        for operation in methods.values():
            for param in operation.get("parameters", []):
                assert param.get("description"), f"{path}: '{param['name']}' sin descripcion"


async def test_validation_error_matches_the_documented_shape(client: AsyncClient) -> None:
    response = await client.get("/pokemon", params={"generation": 99})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
