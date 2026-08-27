"""Configuracion de la aplicacion, cargada desde variables de entorno."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    PROJECT_NAME: str = "NewMonolioPokemon API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["local", "test", "staging", "production"] = "local"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # --- CORS ---
    # NoDecode desactiva el parseo JSON del .env para que lo haga el validador de abajo
    CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Base de datos ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "newmonoliopokemon"
    DATABASE_URL: str | None = None

    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Permite definir CORS_ORIGINS como lista separada por comas en el .env."""
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def sync_dsn(self) -> str:
        """DSN sincrono (psycopg2), que es lo que usa el seeder."""
        return self.sqlalchemy_dsn.replace("+asyncpg", "+psycopg2")

    @property
    def sqlalchemy_dsn(self) -> str:
        """DSN async efectivo: DATABASE_URL tiene prioridad sobre las piezas POSTGRES_*."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )


@lru_cache
def get_settings() -> Settings:
    """Instancia unica de configuracion (cacheada para no releer el entorno)."""
    return Settings()


settings = get_settings()
