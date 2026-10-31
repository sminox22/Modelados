"""
Detección de puntos corporales con MediaPipe Pose Landmarker (procesamiento
local). La interpretación de la postura está separada en pose_analysis.py.
"""
import time

import cv2

from core import settings
from services import pose_analysis as analisis
from utils.exceptions import ModeloNoDisponibleError

COLOR_LINEA = (140, 107, 61)       # BGR del color de acento
COLOR_PUNTO = (240, 240, 240)
COLOR_DUDOSO = (130, 130, 130)


class DetectorPostura:
    """Envuelve el modelo de MediaPipe. Debe crearse, usarse y cerrarse en el mismo hilo."""

    def __init__(self):
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core.base_options import BaseOptions
        except ImportError:
            raise ModeloNoDisponibleError("No está instalado el paquete 'mediapipe'.")
        try:
            with open(settings.ruta_modelo("postura"), "rb") as f:
                modelo = f.read()
        except OSError:
            raise ModeloNoDisponibleError(
                f"Falta el modelo de posturas '{settings.MODELOS['postura'].archivo}'. Ejecute "
                "'python tools/descargar_modelos.py' para descargarlo.")

        self._mp = mp
        opciones = vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=modelo),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = vision.PoseLandmarker.create_from_options(opciones)
        self.conexiones = [(c.start, c.end) for c in vision.PoseLandmarksConnections.POSE_LANDMARKS
                           if c.start >= 11 and c.end >= 11]   # solo cuerpo (sin rostro)
        self._ultimo_ts = 0

    def detectar(self, frame_bgr):
        """Devuelve una lista de 33 analisis.Punto (en píxeles) o [] si no hay persona."""
        alto, ancho = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagen = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        # El modo VIDEO exige marcas de tiempo estrictamente crecientes
        ts = max(int(time.monotonic() * 1000), self._ultimo_ts + 1)
        self._ultimo_ts = ts
        resultado = self._landmarker.detect_for_video(imagen, ts)
        if not resultado.pose_landmarks:
            return []
        return [analisis.Punto(p.x * ancho, p.y * alto, float(p.visibility or 0.0))
                for p in resultado.pose_landmarks[0]]

    def cerrar(self):
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None


class ProcesadorCamaraPostura:
    """Se ejecuta en el hilo de la cámara: detecta, analiza y dibuja el esqueleto."""

    def __init__(self, dibujar_esqueleto: bool = True):
        self.dibujar_esqueleto = dibujar_esqueleto
        self._detector = None

    def preparar(self):
        self._detector = DetectorPostura()

    def cerrar(self):
        if self._detector is not None:
            self._detector.cerrar()
            self._detector = None

    def procesar(self, frame):
        puntos = self._detector.detectar(frame)
        encuadre = analisis.evaluar_encuadre(puntos)
        angulos = analisis.calcular_angulos(puntos)
        etiquetas, explicacion = analisis.clasificar_postura(puntos, angulos)
        if puntos and self.dibujar_esqueleto:
            self._dibujar(frame, puntos)
        info = {
            "encuadre": encuadre,
            "angulos": angulos,
            "confianza": analisis.confianza_media(puntos),
            "inclinacion_hombros": analisis.inclinacion_hombros(puntos),
            "posturas": etiquetas,
            "explicacion": explicacion,
        }
        return frame, info

    def _dibujar(self, frame, puntos):
        for a, b in self._detector.conexiones:
            if puntos[a].fiable and puntos[b].fiable:
                cv2.line(frame, (int(puntos[a].x), int(puntos[a].y)), (int(puntos[b].x), int(puntos[b].y)),
                         COLOR_LINEA, 3, cv2.LINE_AA)
        for indice, punto in enumerate(puntos):
            if indice < 11:
                continue
            color = COLOR_PUNTO if punto.fiable else COLOR_DUDOSO
            centro = (int(punto.x), int(punto.y))
            cv2.circle(frame, centro, 5, color, -1, cv2.LINE_AA)
            cv2.circle(frame, centro, 5, COLOR_LINEA, 1, cv2.LINE_AA)
