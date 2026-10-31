"""Las operaciones matemáticas originales deben seguir funcionando."""
import unittest

import numpy as np

from utils.calculator import evaluar_expresion
from utils.exceptions import CalculoError
from utils.grapher import evaluar_funcion


class PruebasCalculadora(unittest.TestCase):
    def test_operaciones_basicas(self):
        self.assertEqual(evaluar_expresion("2+3*4"), 14)
        self.assertEqual(evaluar_expresion("(2+3)*4"), 20)
        self.assertEqual(evaluar_expresion("2^3"), 8)
        self.assertEqual(evaluar_expresion("6÷2"), 3)
        self.assertAlmostEqual(evaluar_expresion("sqrt(16)+sin(0)"), 4.0)
        self.assertAlmostEqual(evaluar_expresion("log(1000)"), 3.0)

    def test_simbolo_multiplicacion_de_la_calculadora(self):
        # Antes de la corrección, el botón "×" producía "Operación no válida"
        self.assertEqual(evaluar_expresion("2×3"), 6)
        self.assertEqual(evaluar_expresion("2x3"), 6)

    def test_errores(self):
        for expresion in ("", "1/0", "__import__('os')", "abc", "2+"):
            with self.subTest(expresion=expresion):
                with self.assertRaises(CalculoError):
                    evaluar_expresion(expresion)


class PruebasGraficador(unittest.TestCase):
    def test_evalua_funcion(self):
        x = np.array([0.0, 1.0, 2.0])
        np.testing.assert_allclose(evaluar_funcion("x^2 - 3*x + 2", x), [2, 0, 0])
        np.testing.assert_allclose(evaluar_funcion("5", x), [5, 5, 5])

    def test_rechaza_nombres_no_permitidos(self):
        with self.assertRaises(CalculoError):
            evaluar_funcion("y + 1", np.array([1.0]))
        with self.assertRaises(CalculoError):
            evaluar_funcion("open('x')", np.array([1.0]))
