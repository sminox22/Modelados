"""Modelo de datos para la entidad Historial (registro de consultas)."""
from dataclasses import dataclass


@dataclass
class RegistroHistorial:
    problema: str
    respuesta: str
    fecha: str
    hora: str
