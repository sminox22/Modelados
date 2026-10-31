"""
Inicio de sesión biométrico: identifica a qué cuenta pertenece un rostro o
una voz comparándolo con las plantillas de todas las cuentas registradas.

Para el rostro se añade una prueba de gesto (levantar una mano indicada al
azar), comprobada con detección de postura, para que una fotografía impresa
no baste para entrar. Un video de la persona haciendo el gesto correcto aún
podría engañarlo: no es una prueba de vida certificada.
"""
import random
import threading
from dataclasses import dataclass

import cv2
import numpy as np

from core import settings
from services import pose_analysis
from services.biometria_comun import normalizar
from services.face_service import AnalizadorFacial

GESTOS = {
    "derecha": "Levante la mano DERECHA por encima del hombro",
    "izquierda": "Levante la mano IZQUIERDA por encima del hombro",
    "ambas": "Levante AMBAS manos por encima de los hombros",
}


@dataclass
class Identificacion:
    usuario: str
    similitud: float
    segunda: float          # similitud de la segunda cuenta más parecida (0 si no hay)


def identificar(plantillas, vectores, umbral: float, margen: float = None, usuario: str = None):
    """
    Devuelve la Identificacion de la cuenta más parecida o None si ninguna
    supera el umbral o si la segunda es demasiado parecida (ambigüedad).
    Si se indica 'usuario', solo se compara con esa cuenta.
    """
    margen = settings.MARGEN_IDENTIFICACION if margen is None else margen
    if usuario:
        plantillas = [p for p in plantillas if p.usuario == usuario]
    if not plantillas or not vectores:
        return None
    vectores = [normalizar(v) for v in vectores]
    puntajes = sorted(
        ((float(np.mean([np.dot(normalizar(p.vector), v) for v in vectores])), p.usuario) for p in plantillas),
        reverse=True)
    mejor, cuenta = puntajes[0]
    segunda = puntajes[1][0] if len(puntajes) > 1 else 0.0
    if mejor < umbral or mejor - segunda < margen:
        return None
    return Identificacion(cuenta, mejor, segunda)


def gesto_aleatorio() -> str:
    return random.choice(list(GESTOS))


class ProcesadorAccesoFacial:
    """
    Hilo de cámara del inicio de sesión: emite la representación del rostro
    (una de cada 3 imágenes válidas) y, cuando se activa el reto, si la
    persona está haciendo el gesto pedido.
    """

    def __init__(self):
        self._analizador = None
        self._detector_postura = None
        self._lock = threading.Lock()
        self._gesto = None
        self._contador = 0

    def preparar(self):
        from services.pose_service import DetectorPostura
        self._analizador = AnalizadorFacial()
        self._detector_postura = DetectorPostura()

    def cerrar(self):
        self._analizador = None
        if self._detector_postura is not None:
            self._detector_postura.cerrar()
            self._detector_postura = None

    def pedir_gesto(self, gesto):
        with self._lock:
            self._gesto = gesto

    def procesar(self, frame):
        self._contador += 1
        analisis = self._analizador.analizar(frame)
        info = {"estado": analisis.estado, "mensaje": analisis.mensaje}
        if analisis.valido and self._contador % 3 == 0:
            info["vector"] = self._analizador.extraer(frame, analisis.detecciones[0])
        with self._lock:
            gesto = self._gesto
        if gesto is not None:
            puntos = self._detector_postura.detectar(frame)
            info["gesto_ok"] = pose_analysis.mano_levantada(puntos, gesto)
        for deteccion in analisis.detecciones:
            x, y, w, h = deteccion.caja
            cv2.rectangle(frame, (x, y), (x + w, y + h), (140, 107, 61), 2)
        return frame, info
