"""
Reconocimiento facial: detección (YuNet) y comparación de identidad (SFace).

Distinción importante:
- Detectar un rostro solo indica que en la imagen hay una cara.
- Comparar identidad estima si esa cara se parece a la plantilla registrada.
- Este módulo NO comprueba presencia real (no tiene detección de vida): una
  fotografía, un video o una pantalla con la cara de la persona registrada
  podrían ser aceptados. Por eso no se usa como mecanismo de acceso.
"""
import threading
from dataclasses import dataclass, field
from datetime import datetime

import cv2
import numpy as np

from core import settings
from services.biometria_comun import (
    ResultadoVerificacion, combinar_muestras, normalizar, verificar_contra_plantilla,
)
from services import teachable_service
from services.camera import brillo_medio
from utils.exceptions import BiometriaError, ConsentimientoRequeridoError, ModeloNoDisponibleError

MODELO_ID = "opencv-sface-2021dec"

BRILLO_MINIMO = 45.0
BRILLO_MAXIMO = 225.0
ANCHO_MINIMO_ROSTRO = 90       # píxeles; más pequeño = persona demasiado lejos
PUNTUACION_MINIMA = 0.80


@dataclass
class DeteccionRostro:
    fila: np.ndarray               # salida cruda de YuNet (caja, 5 puntos, puntuación)

    @property
    def caja(self):
        x, y, w, h = self.fila[:4]
        return int(x), int(y), int(w), int(h)

    @property
    def puntuacion(self) -> float:
        return float(self.fila[14])


@dataclass
class AnalisisRostro:
    estado: str                    # ok | sin_rostro | varios_rostros | poca_luz | sobreexpuesta | lejos | dudoso
    mensaje: str
    brillo: float
    detecciones: list = field(default_factory=list)

    @property
    def valido(self) -> bool:
        return self.estado == "ok"


def _leer_modelo(clave: str) -> np.ndarray:
    ruta = settings.ruta_modelo(clave)
    try:
        with open(ruta, "rb") as f:
            return np.frombuffer(f.read(), dtype=np.uint8)
    except OSError:
        info = settings.MODELOS[clave]
        raise ModeloNoDisponibleError(
            f"Falta el modelo '{info.archivo}' ({info.descripcion}). Ejecute "
            "'python tools/descargar_modelos.py' para descargarlo.")


class AnalizadorFacial:
    """Detección y extracción de representaciones. Debe usarse desde un solo hilo."""

    def __init__(self):
        self._detector = cv2.FaceDetectorYN.create(
            "onnx", _leer_modelo("detector_rostro"), np.array([], dtype=np.uint8),
            (320, 320), 0.7, 0.3, 5000)
        self._reconocedor = cv2.FaceRecognizerSF.create(
            "onnx", _leer_modelo("reconocedor_rostro"), np.array([], dtype=np.uint8))
        self._tamano = None

    def analizar(self, frame: np.ndarray) -> AnalisisRostro:
        brillo = brillo_medio(frame)
        if brillo < BRILLO_MINIMO:
            return AnalisisRostro("poca_luz", "Iluminación insuficiente. Busque una fuente de luz frontal.", brillo)
        if brillo > BRILLO_MAXIMO:
            return AnalisisRostro("sobreexpuesta", "La imagen está sobreexpuesta. Evite la luz directa.", brillo)

        alto, ancho = frame.shape[:2]
        if self._tamano != (ancho, alto):
            self._detector.setInputSize((ancho, alto))
            self._tamano = (ancho, alto)
        _, filas = self._detector.detect(frame)
        detecciones = [DeteccionRostro(f) for f in filas] if filas is not None else []

        if not detecciones:
            return AnalisisRostro("sin_rostro", "No se detecta ningún rostro.", brillo)
        if len(detecciones) > 1:
            return AnalisisRostro("varios_rostros", "Hay más de un rostro. Solo debe aparecer una persona.",
                                  brillo, detecciones)
        rostro = detecciones[0]
        if rostro.caja[2] < ANCHO_MINIMO_ROSTRO:
            return AnalisisRostro("lejos", "El rostro está demasiado lejos. Acérquese a la cámara.",
                                  brillo, detecciones)
        if rostro.puntuacion < PUNTUACION_MINIMA:
            return AnalisisRostro("dudoso", "Rostro poco claro. Mire de frente y no se mueva.",
                                  brillo, detecciones)
        return AnalisisRostro("ok", "Rostro detectado correctamente.", brillo, detecciones)

    def extraer(self, frame: np.ndarray, deteccion: DeteccionRostro) -> np.ndarray:
        alineado = self._reconocedor.alignCrop(frame, deteccion.fila)
        return normalizar(self._reconocedor.feature(alineado))


class ProcesadorCamaraRostro:
    """
    Procesa los fotogramas en el hilo de la cámara: analiza la calidad, dibuja
    la caja del rostro y, cuando se le solicita, reúne N representaciones de
    fotogramas válidos (para registro o verificación).
    """

    COLOR_OK = (140, 107, 61)       # BGR del color de acento
    COLOR_AVISO = (60, 140, 200)

    def __init__(self):
        self._analizador = None
        self._lock = threading.Lock()
        self._solicitud = None      # (modo, cantidad)
        self._capturas = []
        self._contador_frames = 0
        # Clasificador opcional de Teachable Machine (se activa desde la interfaz)
        self.clasificar_teachable = False
        self._clasificador_tm = None
        self.error_teachable = None

    def preparar(self):
        self._analizador = AnalizadorFacial()
        if teachable_service.imagen_disponible():
            try:
                self._clasificador_tm = teachable_service.ClasificadorImagenTM()
            except Exception as e:      # el módulo facial sigue funcionando sin él
                self.error_teachable = str(getattr(e, "message", e))

    def cerrar(self):
        self._analizador = None
        self._clasificador_tm = None

    def solicitar_capturas(self, modo: str, cantidad: int):
        with self._lock:
            self._solicitud = (modo, cantidad)
            self._capturas = []

    def cancelar_capturas(self):
        with self._lock:
            self._solicitud = None
            self._capturas = []

    def procesar(self, frame: np.ndarray):
        analisis = self._analizador.analizar(frame)
        info = {"estado": analisis.estado, "mensaje": analisis.mensaje, "brillo": analisis.brillo}

        # La representación y la clasificación se calculan antes de dibujar sobre el fotograma
        self._contador_frames += 1
        if self.clasificar_teachable and self._clasificador_tm is not None and self._contador_frames % 3 == 0:
            info["teachable"] = self._clasificador_tm.clasificar(frame)
        with self._lock:
            solicitud = self._solicitud
        # Se toma una muestra cada 4 fotogramas para que haya variación natural
        if solicitud and analisis.valido and self._contador_frames % 4 == 0:
            modo, cantidad = solicitud
            vector = self._analizador.extraer(frame, analisis.detecciones[0])
            with self._lock:
                if self._solicitud == solicitud:
                    self._capturas.append(vector)
                    info["progreso"] = (modo, len(self._capturas), cantidad)
                    if len(self._capturas) >= cantidad:
                        info["capturas"] = (modo, list(self._capturas))
                        self._solicitud = None
                        self._capturas = []

        for deteccion in analisis.detecciones:
            x, y, w, h = deteccion.caja
            color = self.COLOR_OK if analisis.valido else self.COLOR_AVISO
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        return frame, info


class ServicioFacial:
    """Lógica de negocio: registrar, verificar y eliminar la plantilla facial."""

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def tiene_registro(self, usuario: str) -> bool:
        return self.repositorio.existe(usuario, "rostro")

    def registrar(self, usuario: str, vectores, consentimiento: bool):
        if not consentimiento:
            raise ConsentimientoRequeridoError()
        if len(vectores) < settings.MUESTRAS_REGISTRO_ROSTRO:
            raise BiometriaError("No se reunieron suficientes muestras del rostro.")
        plantilla = combinar_muestras(vectores, settings.UMBRAL_ROSTRO)
        self.repositorio.guardar(usuario, "rostro", MODELO_ID, plantilla, len(vectores),
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def verificar(self, usuario: str, vectores) -> ResultadoVerificacion:
        plantilla = self.repositorio.obtener(usuario, "rostro")
        if plantilla is None:
            raise BiometriaError("No tiene un rostro registrado. Regístrelo primero.")
        if plantilla.modelo != MODELO_ID:
            raise BiometriaError("El registro se hizo con otro modelo. Elimínelo y vuelva a registrarse.")
        return verificar_contra_plantilla(plantilla.vector, vectores, settings.UMBRAL_ROSTRO)

    def eliminar(self, usuario: str) -> bool:
        return self.repositorio.eliminar(usuario, "rostro") > 0
