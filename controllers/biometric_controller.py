"""
Controlador de biometría: crea (una sola vez) el repositorio cifrado y los
servicios de rostro y voz. Si el almacenamiento seguro no está disponible,
lo informa en lugar de permitir registros sin protección.
"""
from core import settings
from services.biometric_login import identificar
from storage.biometric_repository import RepositorioBiometrico
from services.face_service import ServicioFacial
from services.voice_service import ServicioVoz
from utils.exceptions import AlmacenamientoInseguroError, AppException


class BiometricController:
    def __init__(self, repositorio: RepositorioBiometrico = None):
        self.error_almacenamiento = None
        self.repositorio = repositorio
        if self.repositorio is None:
            try:
                self.repositorio = RepositorioBiometrico()
            except AppException as e:
                self.error_almacenamiento = e.message
        self.facial = ServicioFacial(self.repositorio) if self.repositorio else None
        self.voz = ServicioVoz(self.repositorio) if self.repositorio else None

    @property
    def almacenamiento_seguro(self) -> bool:
        return self.repositorio is not None

    def exigir_almacenamiento(self):
        if not self.almacenamiento_seguro:
            raise AlmacenamientoInseguroError(self.error_almacenamiento or AlmacenamientoInseguroError().message)

    def resumen(self, usuario: str):
        if not self.almacenamiento_seguro:
            return []
        return self.repositorio.listar(usuario)

    def tiene_registro(self, usuario: str, tipo: str) -> bool:
        return self.almacenamiento_seguro and self.repositorio.existe(usuario, tipo)

    def eliminar(self, usuario: str, tipo: str = None) -> int:
        self.exigir_almacenamiento()
        return self.repositorio.eliminar(usuario, tipo)

    # ---------- Inicio de sesión biométrico ----------
    def hay_registros(self, tipo: str) -> bool:
        return self.almacenamiento_seguro and bool(self.repositorio.obtener_todos(tipo))

    def identificar_rostro(self, vectores, usuario: str = None):
        """Cuenta a la que pertenece el rostro (Identificacion) o None."""
        self.exigir_almacenamiento()
        return identificar(self.repositorio.obtener_todos("rostro"), vectores,
                           settings.UMBRAL_ROSTRO_ACCESO, usuario=usuario or None)

    def identificar_voz(self, vector, usuario: str = None):
        """Cuenta a la que pertenece la voz (Identificacion) o None."""
        self.exigir_almacenamiento()
        return identificar(self.repositorio.obtener_todos("voz"), [vector],
                           settings.UMBRAL_VOZ_ACCESO, usuario=usuario or None)

    @staticmethod
    def modelos_rostro_disponibles() -> bool:
        return settings.modelo_disponible("detector_rostro") and settings.modelo_disponible("reconocedor_rostro")

    @staticmethod
    def modelo_voz_disponible() -> bool:
        return settings.modelo_disponible("voz")

    @staticmethod
    def modelo_postura_disponible() -> bool:
        return settings.modelo_disponible("postura")
