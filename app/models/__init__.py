"""Modelos ORM.

Las tablas se definen en `seeder/models.py` (el seeder es quien crea el esquema)
y se reexportan aqui para que el resto de la app las importe desde un solo sitio.
"""

from app.db.base import Base
from seeder.models import Pokemon, Type, TypeEffectiveness

__all__ = ["Base", "Pokemon", "Type", "TypeEffectiveness"]
