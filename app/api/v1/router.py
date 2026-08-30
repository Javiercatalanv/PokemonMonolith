"""Agregador de routers de la version 1 de la API."""

from fastapi import APIRouter

from app.api.v1.endpoints import generations, health, pokemon, team

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(pokemon.router, prefix="/pokemon", tags=["pokemon"])
api_router.include_router(generations.router, prefix="/generations", tags=["generations"])
api_router.include_router(team.router, prefix="/team", tags=["team"])
