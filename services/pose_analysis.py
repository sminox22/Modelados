"""
Interpretación de la postura a partir de puntos corporales ya detectados.

Este módulo no usa la cámara ni el modelo: recibe puntos (x, y en píxeles
y su visibilidad) y calcula ángulos articulares y una clasificación simple
basada en reglas geométricas explícitas. No evalúa lesiones, enfermedades
ni ningún estado médico.

Posturas reconocidas (reglas):
- De pie:            rodillas >= 160° y caderas >= 160° (lado visible).
- Piernas flexionadas: rodillas entre 60° y 130° y caderas entre 60° y 130°.
- Brazos levantados: ambas muñecas por encima de la nariz (o de los
                     hombros si la nariz no es visible).
- Brazos en cruz:    codos >= 150°, hombros entre 70° y 110° y muñecas a la
                     altura aproximada de los hombros.
"""
import math
from dataclasses import dataclass

VISIBILIDAD_MINIMA = 0.6

# Índices del modelo MediaPipe Pose (33 puntos)
NARIZ = 0
HOMBRO_IZQ, HOMBRO_DER = 11, 12
CODO_IZQ, CODO_DER = 13, 14
MUNECA_IZQ, MUNECA_DER = 15, 16
CADERA_IZQ, CADERA_DER = 23, 24
RODILLA_IZQ, RODILLA_DER = 25, 26
TOBILLO_IZQ, TOBILLO_DER = 27, 28

PUNTOS_RELEVANTES = {
    "Hombros": (HOMBRO_IZQ, HOMBRO_DER),
    "Codos": (CODO_IZQ, CODO_DER),
    "Muñecas": (MUNECA_IZQ, MUNECA_DER),
    "Caderas": (CADERA_IZQ, CADERA_DER),
    "Rodillas": (RODILLA_IZQ, RODILLA_DER),
    "Tobillos": (TOBILLO_IZQ, TOBILLO_DER),
}

# Ángulo en el vértice central (a, vértice, c). "Izquierdo" = lado izquierdo de la persona.
ARTICULACIONES = {
    "Codo izquierdo": (HOMBRO_IZQ, CODO_IZQ, MUNECA_IZQ),
    "Codo derecho": (HOMBRO_DER, CODO_DER, MUNECA_DER),
    "Hombro izquierdo": (CODO_IZQ, HOMBRO_IZQ, CADERA_IZQ),
    "Hombro derecho": (CODO_DER, HOMBRO_DER, CADERA_DER),
    "Cadera izquierda": (HOMBRO_IZQ, CADERA_IZQ, RODILLA_IZQ),
    "Cadera derecha": (HOMBRO_DER, CADERA_DER, RODILLA_DER),
    "Rodilla izquierda": (CADERA_IZQ, RODILLA_IZQ, TOBILLO_IZQ),
    "Rodilla derecha": (CADERA_DER, RODILLA_DER, TOBILLO_DER),
}


@dataclass
class Punto:
    x: float
    y: float
    visibilidad: float

    @property
    def fiable(self) -> bool:
        return self.visibilidad >= VISIBILIDAD_MINIMA


@dataclass
class Encuadre:
    estado: str          # sin_persona | parcial | completo
    mensaje: str
    faltantes: list


def angulo(a: Punto, b: Punto, c: Punto) -> float:
    """Ángulo ABC en grados (0-180)."""
    v1 = (a.x - b.x, a.y - b.y)
    v2 = (c.x - b.x, c.y - b.y)
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 == 0 or n2 == 0:
        return float("nan")
    coseno = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(coseno))


def _fiables(puntos, *indices) -> bool:
    return all(i < len(puntos) and puntos[i].fiable for i in indices)


def calcular_angulos(puntos) -> dict:
    """Devuelve {articulación: grados o None si algún punto no es fiable}."""
    resultado = {}
    for nombre, (a, b, c) in ARTICULACIONES.items():
        if puntos and _fiables(puntos, a, b, c):
            valor = angulo(puntos[a], puntos[b], puntos[c])
            resultado[nombre] = None if math.isnan(valor) else valor
        else:
            resultado[nombre] = None
    return resultado


def evaluar_encuadre(puntos) -> Encuadre:
    if not puntos:
        return Encuadre("sin_persona", "No se detecta ninguna persona en el encuadre.", list(PUNTOS_RELEVANTES))
    faltantes = [nombre for nombre, indices in PUNTOS_RELEVANTES.items() if not _fiables(puntos, *indices)]
    if not faltantes:
        return Encuadre("completo", "Cuerpo completo dentro del encuadre.", [])
    if len(faltantes) == len(PUNTOS_RELEVANTES):
        return Encuadre("sin_persona", "La detección es insuficiente. Colóquese frente a la cámara.", faltantes)
    return Encuadre("parcial", "Partes fuera del encuadre o poco visibles: " + ", ".join(faltantes).lower() + ".",
                    faltantes)


def confianza_media(puntos) -> float:
    indices = [i for par in PUNTOS_RELEVANTES.values() for i in par]
    if not puntos:
        return 0.0
    return sum(puntos[i].visibilidad for i in indices) / len(indices)


def inclinacion_hombros(puntos):
    """Grados de inclinación de la línea de hombros respecto a la horizontal (None si no es fiable)."""
    if not puntos or not _fiables(puntos, HOMBRO_IZQ, HOMBRO_DER):
        return None
    a, b = puntos[HOMBRO_IZQ], puntos[HOMBRO_DER]
    grados = math.degrees(math.atan2(a.y - b.y, a.x - b.x))
    # Normaliza a [-90, 90] sin importar el orden izquierda/derecha
    if grados > 90:
        grados -= 180
    elif grados < -90:
        grados += 180
    return grados


def mano_levantada(puntos, lado: str) -> bool:
    """
    lado: "derecha", "izquierda" o "ambas" (lado de la persona). La muñeca debe
    estar por encima del hombro del mismo lado al menos un 20 % del ancho de hombros.
    """
    if not puntos or not _fiables(puntos, HOMBRO_IZQ, HOMBRO_DER):
        return False
    hi, hd = puntos[HOMBRO_IZQ], puntos[HOMBRO_DER]
    ancho = max(math.hypot(hi.x - hd.x, hi.y - hd.y), 1.0)

    def arriba(muneca, hombro):
        return _fiables(puntos, muneca) and puntos[muneca].y < puntos[hombro].y - 0.2 * ancho

    derecha = arriba(MUNECA_DER, HOMBRO_DER)
    izquierda = arriba(MUNECA_IZQ, HOMBRO_IZQ)
    if lado == "derecha":
        return derecha and not izquierda
    if lado == "izquierda":
        return izquierda and not derecha
    return derecha and izquierda


def _promedio(*valores):
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else None


def clasificar_postura(puntos, angulos: dict):
    """Devuelve (lista de etiquetas, explicación). Lista vacía si no se puede clasificar."""
    etiquetas, motivos = [], []
    if not puntos:
        return etiquetas, "Sin puntos corporales."

    rodilla = _promedio(angulos.get("Rodilla izquierda"), angulos.get("Rodilla derecha"))
    cadera = _promedio(angulos.get("Cadera izquierda"), angulos.get("Cadera derecha"))
    if rodilla is not None and cadera is not None:
        if rodilla >= 160 and cadera >= 160:
            etiquetas.append("De pie")
            motivos.append(f"rodillas {rodilla:.0f}° y caderas {cadera:.0f}° casi extendidas")
        elif 60 <= rodilla <= 130 and 60 <= cadera <= 130:
            etiquetas.append("Piernas flexionadas (p. ej., sentado)")
            motivos.append(f"rodillas {rodilla:.0f}° y caderas {cadera:.0f}° flexionadas")

    if _fiables(puntos, HOMBRO_IZQ, HOMBRO_DER, MUNECA_IZQ, MUNECA_DER):
        hi, hd = puntos[HOMBRO_IZQ], puntos[HOMBRO_DER]
        mi, md = puntos[MUNECA_IZQ], puntos[MUNECA_DER]
        ancho_hombros = max(math.hypot(hi.x - hd.x, hi.y - hd.y), 1.0)
        referencia = puntos[NARIZ].y if _fiables(puntos, NARIZ) else min(hi.y, hd.y) - 0.5 * ancho_hombros
        codo = _promedio(angulos.get("Codo izquierdo"), angulos.get("Codo derecho"))
        hombro_i, hombro_d = angulos.get("Hombro izquierdo"), angulos.get("Hombro derecho")
        if mi.y < referencia and md.y < referencia:
            etiquetas.append("Brazos levantados")
            motivos.append("ambas muñecas por encima de la cabeza")
        elif (codo is not None and codo >= 150 and hombro_i is not None and hombro_d is not None
              and 70 <= hombro_i <= 110 and 70 <= hombro_d <= 110
              and abs(mi.y - hi.y) < 0.35 * ancho_hombros and abs(md.y - hd.y) < 0.35 * ancho_hombros):
            etiquetas.append("Brazos en cruz")
            motivos.append("brazos extendidos a la altura de los hombros")

    if not etiquetas:
        return [], "La posición no coincide con ninguna de las posturas definidas."
    return etiquetas, "Criterio: " + "; ".join(motivos) + "."
