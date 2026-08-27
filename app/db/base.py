"""Clase base declarativa de SQLAlchemy.

Las tablas se definen en `seeder/models.py` sobre esta Base, de modo que la app
y el seeder compartan un unico `metadata`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
