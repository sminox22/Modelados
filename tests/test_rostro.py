"""Reconocimiento facial con los modelos reales (YuNet + SFace)."""
import unittest

import cv2
import numpy as np

from core import settings
from core.secure_storage import dpapi_disponible
from services.face_service import AnalizadorFacial, ProcesadorCamaraRostro, ServicioFacial
from storage.biometric_repository import RepositorioBiometrico
from tests.utilidades import EntornoAislado, dato, hay_dato, hay_modelo
from utils.exceptions import BiometriaError, ConsentimientoRequeridoError

MODELOS = ("detector_rostro", "reconocedor_rostro")


@unittest.skipUnless(hay_modelo(*MODELOS), "Faltan los modelos de rostro (tools/descargar_modelos.py)")
class PruebasCalidadImagen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analizador = AnalizadorFacial()

    def test_imagen_oscura(self):
        self.assertEqual(self.analizador.analizar(np.full((480, 640, 3), 10, np.uint8)).estado, "poca_luz")

    def test_imagen_sobreexpuesta(self):
        self.assertEqual(self.analizador.analizar(np.full((480, 640, 3), 250, np.uint8)).estado, "sobreexpuesta")

    def test_sin_rostro(self):
        self.assertEqual(self.analizador.analizar(np.full((480, 640, 3), 128, np.uint8)).estado, "sin_rostro")


IMAGENES = ("portrait.jpg", "portrait_rotated.jpg", "business-person.png", "pose.jpg")


@unittest.skipUnless(hay_modelo(*MODELOS) and hay_dato(*IMAGENES),
                     "Faltan modelos o datos de prueba (tools/descargar_datos_prueba.py)")
@unittest.skipUnless(dpapi_disponible(), "DPAPI solo existe en Windows")
class PruebasIdentidadFacial(EntornoAislado):
    @classmethod
    def setUpClass(cls):
        cls.analizador = AnalizadorFacial()
        cls.persona_a = cv2.imread(dato("portrait.jpg"))
        # Misma persona, otra fotografía (guardada rotada 90° en el archivo original)
        cls.persona_a_otra = cv2.rotate(cv2.imread(dato("portrait_rotated.jpg")), cv2.ROTATE_90_COUNTERCLOCKWISE)
        cls.persona_b = cv2.imread(dato("business-person.png"))

    def vector(self, imagen):
        analisis = self.analizador.analizar(imagen)
        self.assertTrue(analisis.valido, analisis.mensaje)
        return self.analizador.extraer(imagen, analisis.detecciones[0])

    def test_rostro_lejano(self):
        self.assertEqual(self.analizador.analizar(cv2.imread(dato("pose.jpg"))).estado, "lejos")

    def test_registro_y_verificacion(self):
        servicio = ServicioFacial(RepositorioBiometrico())
        muestras = [self.vector(cv2.convertScaleAbs(self.persona_a, alpha=a, beta=b))
                    for a, b in ((1.0, 0), (1.05, 5), (0.95, -5), (1.1, 0), (0.9, 10))]
        with self.assertRaises(ConsentimientoRequeridoError):
            servicio.registrar("ana", muestras, consentimiento=False)
        servicio.registrar("ana", muestras, consentimiento=True)
        self.assertTrue(servicio.tiene_registro("ana"))

        mismo = servicio.verificar("ana", [self.vector(self.persona_a_otra)])
        self.assertTrue(mismo.coincide, mismo.similitud)
        otro = servicio.verificar("ana", [self.vector(self.persona_b)])
        self.assertFalse(otro.coincide, otro.similitud)
        self.assertLess(otro.similitud, settings.UMBRAL_ROSTRO)

        self.assertTrue(servicio.eliminar("ana"))
        with self.assertRaises(BiometriaError):
            servicio.verificar("ana", [self.vector(self.persona_a)])

    def test_registro_con_dos_personas_es_rechazado(self):
        servicio = ServicioFacial(RepositorioBiometrico())
        muestras = [self.vector(self.persona_a)] * 4 + [self.vector(self.persona_b)]
        with self.assertRaises(BiometriaError):
            servicio.registrar("ana", muestras, consentimiento=True)

    def test_procesador_reune_capturas(self):
        procesador = ProcesadorCamaraRostro()
        procesador.preparar()
        procesador.solicitar_capturas("registro", 3)
        info = {}
        for _ in range(20):
            _, info = procesador.procesar(self.persona_a.copy())
            if "capturas" in info:
                break
        self.assertIn("capturas", info)
        modo, vectores = info["capturas"]
        self.assertEqual((modo, len(vectores)), ("registro", 3))
        # Las capturas se extraen antes de dibujar el recuadro: deben coincidir con la imagen limpia
        self.assertGreater(float(np.dot(vectores[0], self.vector(self.persona_a))), 0.99)
