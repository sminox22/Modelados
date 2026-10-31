"""
Hilos de trabajo para no bloquear la interfaz: captura de cámara con
procesamiento por fotograma, y tareas puntuales (p. ej., inferencia de voz).

Los hilos nunca tocan widgets: comunican resultados mediante señales, que
Qt entrega en el hilo principal.
"""
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from services.camera import CamaraLocal
from utils.exceptions import AppException


def frame_a_qimage(frame_bgr, espejo: bool = True) -> QImage:
    if espejo:
        frame_bgr = cv2.flip(frame_bgr, 1)
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    alto, ancho = rgb.shape[:2]
    return QImage(rgb.data, ancho, alto, 3 * ancho, QImage.Format_RGB888).copy()


class HiloCamara(QThread):
    """
    Abre la cámara, aplica 'procesador.procesar(frame) -> (frame, info)' a cada
    fotograma y emite la imagen y la información. El procesador se prepara y
    se cierra dentro de este hilo (los modelos no se comparten entre hilos).
    """
    camara_lista = pyqtSignal()
    fotograma = pyqtSignal(QImage)
    resultado = pyqtSignal(object)
    error = pyqtSignal(str)

    # Hilos que no terminaron dentro del tiempo de espera: se conservan hasta
    # que finalicen para que Qt no destruya un hilo en ejecución.
    _pendientes = set()

    def __init__(self, indice_camara: int, procesador=None, parent=None):
        super().__init__(parent)
        self.indice_camara = indice_camara
        self.procesador = procesador
        self._detener = False

    def detener(self, espera_ms: int = 3000) -> bool:
        """Solicita la detención y espera. Devuelve False si el hilo sigue ocupado (p. ej., abriendo la cámara)."""
        self._detener = True
        if self.wait(espera_ms):
            return True
        HiloCamara._pendientes.add(self)
        self.finished.connect(lambda: HiloCamara._pendientes.discard(self))
        return False

    def run(self):
        camara = CamaraLocal(self.indice_camara)
        try:
            if self.procesador is not None and hasattr(self.procesador, "preparar"):
                self.procesador.preparar()
            camara.abrir()
            self.camara_lista.emit()
            while not self._detener:
                frame = camara.leer()
                if frame is None:
                    self.msleep(15)
                    continue
                info = None
                if self.procesador is not None:
                    frame, info = self.procesador.procesar(frame)
                self.fotograma.emit(frame_a_qimage(frame))
                if info is not None:
                    self.resultado.emit(info)
                self.msleep(10)
        except AppException as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(f"Error procesando la cámara: {e}")
        finally:
            camara.liberar()
            if self.procesador is not None and hasattr(self.procesador, "cerrar"):
                try:
                    self.procesador.cerrar()
                except Exception:
                    pass


class HiloTarea(QThread):
    """Ejecuta una función en segundo plano y emite su resultado o el mensaje de error."""
    exito = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, funcion, *args, parent=None):
        super().__init__(parent)
        self.funcion = funcion
        self.args = args

    def run(self):
        try:
            self.exito.emit(self.funcion(*self.args))
        except AppException as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(f"Error inesperado: {e}")
