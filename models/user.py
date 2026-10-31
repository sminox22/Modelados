"""Modelo de datos para la entidad Usuario."""
from dataclasses import dataclass


@dataclass
class Usuario:
    id: int
    nombre: str
    usuario: str
    contrasena_hash: str
