"""Estado compartido por las pantallas de la sesión iniciada."""
from dataclasses import dataclass, field

from core.settings import Ajustes, guardar_ajustes


@dataclass
class ContextoSesion:
    usuario: dict                     # {"id", "nombre", "usuario"}
    ajustes: Ajustes
    biometria: object                 # BiometricController
    # Permisos concedidos durante esta sesión (no se recuerdan entre sesiones)
    permisos: set = field(default_factory=set)

    @property
    def nombre_usuario(self) -> str:
        return self.usuario["usuario"]

    def guardar_ajustes(self):
        guardar_ajustes(self.ajustes)
