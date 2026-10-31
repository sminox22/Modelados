"""
Acceso a la cámara con OpenCV, independiente de la interfaz gráfica.

En Windows se intenta primero DirectShow (abre más rápido y libera bien el
dispositivo) y luego Media Foundation. Si Windows bloquea la cámara por
privacidad, OpenCV la abre pero no entrega fotogramas: ese caso también se
reporta como CamaraNoDisponibleError.
"""
import sys

import cv2
import numpy as np

from utils.exceptions import CamaraNoDisponibleError


def brillo_medio(frame: np.ndarray) -> float:
    gris = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
    return float(gris.mean())


class CamaraLocal:
    FALLOS_MAXIMOS = 30

    def __init__(self, indice: int = 0, ancho: int = 640, alto: int = 480):
        self.indice = indice
        self.ancho = ancho
        self.alto = alto
        self._captura = None
        self._fallos = 0

    @property
    def abierta(self) -> bool:
        return self._captura is not None and self._captura.isOpened()

    def abrir(self):
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF] if sys.platform == "win32" else [cv2.CAP_ANY]
        for backend in backends:
            captura = cv2.VideoCapture(self.indice, backend)
            if captura.isOpened():
                captura.set(cv2.CAP_PROP_FRAME_WIDTH, self.ancho)
                captura.set(cv2.CAP_PROP_FRAME_HEIGHT, self.alto)
                ok, frame = captura.read()
                if ok and frame is not None:
                    self._captura = captura
                    self._fallos = 0
                    return
            captura.release()
        raise CamaraNoDisponibleError(
            f"No se encontró una cámara disponible en el índice {self.indice}. Verifique que "
            "esté conectada, que ninguna otra aplicación la esté usando y que el acceso esté "
            "permitido en Configuración de Windows > Privacidad y seguridad > Cámara.")

    def leer(self) -> np.ndarray:
        """Devuelve un fotograma BGR, o None si falló. Lanza error si falla de forma continua."""
        if not self.abierta:
            raise CamaraNoDisponibleError("La cámara no está abierta.")
        ok, frame = self._captura.read()
        if not ok or frame is None:
            self._fallos += 1
            if self._fallos >= self.FALLOS_MAXIMOS:
                raise CamaraNoDisponibleError(
                    "La cámara dejó de enviar imágenes (¿se desconectó o la tomó otra aplicación?).")
            return None
        self._fallos = 0
        return frame

    def liberar(self):
        if self._captura is not None:
            self._captura.release()
            self._captura = None
