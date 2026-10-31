"""Operaciones numéricas compartidas por los módulos biométricos de rostro y voz."""
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from utils.exceptions import BiometriaError


@dataclass
class ResultadoVerificacion:
    coincide: bool
    similitud: float
    umbral: float
    mensaje: str


def normalizar(vector) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).ravel()
    norma = float(np.linalg.norm(vector))
    if norma == 0.0 or not np.isfinite(norma):
        raise BiometriaError("La representación biométrica obtenida no es válida.")
    return vector / norma


def similitud_coseno(a, b) -> float:
    return float(np.dot(normalizar(a), normalizar(b)))


def combinar_muestras(vectores, umbral_consistencia: float) -> np.ndarray:
    """
    Promedia varias muestras normalizadas en una sola plantilla. Exige que
    todas las parejas de muestras sean coherentes entre sí: si alguna pareja
    queda por debajo del umbral, probablemente hubo otra persona, ruido o una
    captura defectuosa, y el registro se rechaza.
    """
    vectores = [normalizar(v) for v in vectores]
    if len(vectores) < 2:
        raise BiometriaError("Se necesitan al menos dos muestras para el registro.")
    for a, b in combinations(vectores, 2):
        if float(np.dot(a, b)) < umbral_consistencia:
            raise BiometriaError(
                "Las muestras capturadas no son coherentes entre sí. Repita el registro "
                "asegurándose de que solo aparezca usted y de que las condiciones sean estables.")
    return normalizar(np.mean(vectores, axis=0))


def verificar_contra_plantilla(plantilla, vectores, umbral: float) -> ResultadoVerificacion:
    """Compara una o varias muestras nuevas con la plantilla registrada (promedio de similitudes)."""
    similitudes = [similitud_coseno(plantilla, v) for v in vectores]
    similitud = float(np.mean(similitudes))
    coincide = similitud >= umbral
    if coincide:
        mensaje = "La muestra es compatible con la identidad registrada."
    else:
        mensaje = "La muestra no coincide con la identidad registrada."
    return ResultadoVerificacion(coincide, similitud, umbral, mensaje)
