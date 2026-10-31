"""Modelos de Teachable Machine: preprocesamiento, capas numpy y carga de los modelos del proyecto."""
import os
import tempfile
import unittest

import numpy as np

from services import teachable_service as tm


class PruebasOperaciones(unittest.TestCase):
    def test_convolucion_igual_a_implementacion_directa(self):
        rng = np.random.default_rng(0)
        x = rng.standard_normal((6, 9, 2)).astype(np.float32)
        kernel = rng.standard_normal((2, 3, 2, 4)).astype(np.float32)
        bias = rng.standard_normal(4).astype(np.float32)
        esperado = np.zeros((5, 7, 4), np.float32)
        for i in range(5):
            for j in range(7):
                esperado[i, j] = np.tensordot(x[i:i + 2, j:j + 3, :], kernel, axes=3) + bias
        np.testing.assert_allclose(tm._conv2d_valida(x, kernel, bias), esperado, rtol=1e-5, atol=1e-5)

    def test_maxpool_con_pasos_distintos(self):
        x = np.arange(3 * 22, dtype=np.float32).reshape(3, 22, 1)
        self.assertEqual(tm._maxpool(x, [2, 2], [1, 2]).shape, (2, 11, 1))
        self.assertEqual(tm._maxpool(np.zeros((9, 51, 1)), [2, 2], [2, 2]).shape, (4, 25, 1))

    def test_espectrograma(self):
        audio = np.sin(2 * np.pi * 1000 * np.arange(44100) / 44100).astype(np.float32)
        espectro = tm.espectrograma_tm(audio)
        self.assertEqual(espectro.shape, (43, 232))
        self.assertAlmostEqual(float(espectro.mean()), 0.0, places=4)
        self.assertAlmostEqual(float(espectro.std()), 1.0, places=3)
        # La energía del tono de 1 kHz cae en la banda 1000 / (44100 / 1024) ≈ 23
        self.assertEqual(int(np.argmax(espectro.mean(axis=0))), 23)
        # Audio más corto que 1 s se completa con silencio al inicio
        self.assertEqual(tm.espectrograma_tm(audio[:1000]).shape, (43, 232))

    def test_etiquetas_txt(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("0 burbano\n1 kevin\n2 otros \n\n")
        try:
            self.assertEqual(tm.leer_etiquetas_txt(f.name), ["burbano", "kevin", "otros"])
        finally:
            os.remove(f.name)


@unittest.skipUnless(tm.audio_disponible(), "No hay modelo de audio en models/teachable/audio")
class PruebasModeloAudio(unittest.TestCase):
    def test_clasifica_y_suma_uno(self):
        clasificador = tm.ClasificadorAudioTM()
        resultado = clasificador.clasificar(0.01 * np.random.default_rng(1).standard_normal(44100).astype(np.float32))
        self.assertEqual(len(resultado), len(clasificador.etiquetas))
        self.assertAlmostEqual(sum(p for _, p in resultado), 1.0, places=4)
        self.assertGreaterEqual(resultado[0][1], resultado[-1][1])


@unittest.skipUnless(tm.imagen_disponible(), "No hay modelo de imagen en models/teachable/imagen")
class PruebasModeloImagen(unittest.TestCase):
    def test_clasifica_y_suma_uno(self):
        clasificador = tm.ClasificadorImagenTM()
        frame = np.random.default_rng(2).integers(0, 255, (480, 640, 3), dtype=np.uint8)
        resultado = clasificador.clasificar(frame)
        self.assertEqual(len(resultado), len(clasificador.etiquetas))
        self.assertAlmostEqual(sum(p for _, p in resultado), 1.0, places=4)

    def test_preprocesamiento(self):
        entrada = tm.ClasificadorImagenTM.preprocesar(np.full((480, 640, 3), 255, np.uint8))
        self.assertEqual(entrada.shape, (1, 3, 224, 224))
        self.assertAlmostEqual(float(entrada.max()), 1.0, places=5)
