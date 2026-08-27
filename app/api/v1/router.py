"""Agregador de routers de la version 1 de la API."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, pokemon

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(pokemon.router, prefix="/pokemon", tags=["pokemon"])
