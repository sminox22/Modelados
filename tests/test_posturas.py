"""Posturas: geometría y reglas (sin modelo) y detección con MediaPipe (con modelo)."""
import unittest

import cv2
import numpy as np

from services import pose_analysis as pa
from tests.utilidades import dato, hay_dato, hay_modelo


def esqueleto():
    """Persona de pie, brazos en cruz, vista de frente (coordenadas de imagen)."""
    puntos = [pa.Punto(320, 100, 0.99) for _ in range(33)]
    base = {
        pa.NARIZ: (320, 80),
        pa.HOMBRO_IZQ: (360, 150), pa.HOMBRO_DER: (280, 150),
        pa.CODO_IZQ: (430, 150), pa.CODO_DER: (210, 150),
        pa.MUNECA_IZQ: (500, 150), pa.MUNECA_DER: (140, 150),
        pa.CADERA_IZQ: (345, 300), pa.CADERA_DER: (295, 300),
        pa.RODILLA_IZQ: (345, 400), pa.RODILLA_DER: (295, 400),
        pa.TOBILLO_IZQ: (345, 500), pa.TOBILLO_DER: (295, 500),
    }
    for indice, (x, y) in base.items():
        puntos[indice] = pa.Punto(x, y, 0.99)
    return puntos


class PruebasAnalisis(unittest.TestCase):
    def test_angulo(self):
        self.assertAlmostEqual(pa.angulo(pa.Punto(1, 0, 1), pa.Punto(0, 0, 1), pa.Punto(0, 1, 1)), 90.0)
        self.assertAlmostEqual(pa.angulo(pa.Punto(-1, 0, 1), pa.Punto(0, 0, 1), pa.Punto(1, 0, 1)), 180.0)

    def test_de_pie_brazos_en_cruz(self):
        puntos = esqueleto()
        etiquetas, _ = pa.clasificar_postura(puntos, pa.calcular_angulos(puntos))
        self.assertIn("De pie", etiquetas)
        self.assertIn("Brazos en cruz", etiquetas)
        self.assertEqual(pa.evaluar_encuadre(puntos).estado, "completo")
        self.assertAlmostEqual(pa.inclinacion_hombros(puntos), 0.0)

    def test_brazos_levantados(self):
        puntos = esqueleto()
        puntos[pa.MUNECA_IZQ] = pa.Punto(380, 40, 0.99)
        puntos[pa.MUNECA_DER] = pa.Punto(260, 40, 0.99)
        puntos[pa.CODO_IZQ] = pa.Punto(375, 90, 0.99)
        puntos[pa.CODO_DER] = pa.Punto(265, 90, 0.99)
        etiquetas, _ = pa.clasificar_postura(puntos, pa.calcular_angulos(puntos))
        self.assertIn("Brazos levantados", etiquetas)

    def test_piernas_flexionadas(self):
        puntos = esqueleto()
        # Muslos horizontales y piernas verticales: cadera y rodilla a ~90°
        puntos[pa.RODILLA_IZQ] = pa.Punto(445, 300, 0.99)
        puntos[pa.RODILLA_DER] = pa.Punto(395, 300, 0.99)
        puntos[pa.TOBILLO_IZQ] = pa.Punto(445, 400, 0.99)
        puntos[pa.TOBILLO_DER] = pa.Punto(395, 400, 0.99)
        etiquetas, _ = pa.clasificar_postura(puntos, pa.calcular_angulos(puntos))
        self.assertIn("Piernas flexionadas (p. ej., sentado)", etiquetas)

    def test_puntos_poco_visibles(self):
        puntos = esqueleto()
        for i in (pa.RODILLA_IZQ, pa.RODILLA_DER, pa.TOBILLO_IZQ, pa.TOBILLO_DER):
            puntos[i] = pa.Punto(puntos[i].x, puntos[i].y, 0.1)
        angulos = pa.calcular_angulos(puntos)
        self.assertIsNone(angulos["Rodilla izquierda"])
        encuadre = pa.evaluar_encuadre(puntos)
        self.assertEqual(encuadre.estado, "parcial")
        self.assertIn("Rodillas", encuadre.faltantes)
        self.assertNotIn("De pie", pa.clasificar_postura(puntos, angulos)[0])

    def test_sin_persona(self):
        self.assertEqual(pa.evaluar_encuadre([]).estado, "sin_persona")
        self.assertEqual(pa.clasificar_postura([], {})[0], [])


@unittest.skipUnless(hay_modelo("postura") and hay_dato("pose.jpg"),
                     "Faltan el modelo de posturas o los datos de prueba")
class PruebasDetectorPostura(unittest.TestCase):
    def procesar(self, imagen):
        from services.pose_service import ProcesadorCamaraPostura
        procesador = ProcesadorCamaraPostura()
        procesador.preparar()
        try:
            return procesador.procesar(imagen)[1]
        finally:
            procesador.cerrar()

    def test_detecta_esqueleto(self):
        info = self.procesar(cv2.imread(dato("pose.jpg")))
        self.assertEqual(info["encuadre"].estado, "completo")
        self.assertGreater(info["confianza"], 0.8)
        self.assertIn("Brazos en cruz", info["posturas"])
        self.assertGreater(info["angulos"]["Codo izquierdo"], 150)

    def test_imagen_sin_persona(self):
        info = self.procesar(np.full((480, 640, 3), 128, np.uint8))
        self.assertEqual(info["encuadre"].estado, "sin_persona")
