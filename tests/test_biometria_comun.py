import unittest

import numpy as np

from services.biometria_comun import combinar_muestras, similitud_coseno, verificar_contra_plantilla
from utils.exceptions import BiometriaError


class PruebasBiometriaComun(unittest.TestCase):
    def test_similitud(self):
        self.assertAlmostEqual(similitud_coseno([1, 0], [2, 0]), 1.0)
        self.assertAlmostEqual(similitud_coseno([1, 0], [0, 3]), 0.0)
        with self.assertRaises(BiometriaError):
            similitud_coseno([0, 0], [1, 0])

    def test_combinar_rechaza_muestras_incoherentes(self):
        base = np.array([1.0, 0.1, 0.0])
        plantilla = combinar_muestras([base, base + 0.05, base - 0.05], 0.5)
        self.assertAlmostEqual(float(np.linalg.norm(plantilla)), 1.0, places=5)
        with self.assertRaises(BiometriaError):
            combinar_muestras([base, np.array([0.0, 0.0, 1.0])], 0.5)

    def test_verificacion_aplica_umbral(self):
        plantilla = np.array([1.0, 0.0])
        self.assertTrue(verificar_contra_plantilla(plantilla, [[1.0, 0.1]], 0.9).coincide)
        self.assertFalse(verificar_contra_plantilla(plantilla, [[0.2, 1.0]], 0.9).coincide)
