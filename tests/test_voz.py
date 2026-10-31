"""Verificación biométrica de voz: validación de muestras y modelo real (CAM++)."""
import unittest

import numpy as np

from core.secure_storage import dpapi_disponible
from services.audio_recorder import GrabadorAudio, remuestrear
from services.voice_service import ServicioVoz, validar_audio
from storage.biometric_repository import RepositorioBiometrico
from tests.utilidades import EntornoAislado, dato, hay_dato, hay_modelo, leer_wav
from utils.exceptions import BiometriaError, MicrofonoNoDisponibleError

SR = 16000


def voz_sintetica(segundos=4.0, amplitud=0.3, ruido=0.002, semilla=0):
    """Tonos modulados con pausas: imita la energía de una voz (no es voz real)."""
    rng = np.random.default_rng(semilla)
    t = np.arange(int(segundos * SR)) / SR
    envolvente = (np.sin(2 * np.pi * 2.5 * t) > -0.3).astype(np.float32)
    senal = amplitud * envolvente * np.sin(2 * np.pi * 180 * t) * (1 + 0.3 * np.sin(2 * np.pi * 5 * t))
    return (senal + ruido * rng.standard_normal(t.size)).astype(np.float32)


class PruebasValidacionAudio(unittest.TestCase):
    def test_muestra_valida(self):
        validacion = validar_audio(voz_sintetica())
        self.assertTrue(validacion.valida, validacion.mensaje)

    def test_rechazos(self):
        casos = {
            "corta": voz_sintetica(segundos=1.0),
            "silencio_absoluto": np.zeros(4 * SR, np.float32),
            "volumen_bajo": voz_sintetica(amplitud=0.003, ruido=0.0005),
            "saturada": np.clip(voz_sintetica(amplitud=3.0), -1, 1),
            "ruidosa": voz_sintetica(ruido=0.15),
        }
        for nombre, audio in casos.items():
            with self.subTest(nombre):
                self.assertFalse(validar_audio(audio).valida, nombre)

    def test_remuestreo(self):
        audio = np.sin(2 * np.pi * 440 * np.arange(48000) / 48000).astype(np.float32)
        salida = remuestrear(audio, 48000, 16000)
        self.assertEqual(len(salida), 16000)
        self.assertEqual(salida.dtype, np.float32)

    def test_microfono_inexistente(self):
        with self.assertRaises(MicrofonoNoDisponibleError):
            GrabadorAudio(dispositivo=999).iniciar()


ARCHIVOS = ["voz/fangjun-sr-2.wav", "voz/fangjun-sr-3.wav", "voz/fangjun-test-sr-1.wav", "voz/leijun-test-sr-1.wav"]


@unittest.skipUnless(hay_modelo("voz") and hay_dato(*ARCHIVOS),
                     "Faltan el modelo de voz o los datos de prueba (tools/descargar_datos_prueba.py)")
@unittest.skipUnless(dpapi_disponible(), "DPAPI solo existe en Windows")
class PruebasVerificacionVoz(EntornoAislado):
    def test_registro_y_verificacion(self):
        servicio = ServicioVoz(RepositorioBiometrico())
        a1, a2, a_prueba, b_prueba = (leer_wav(dato(n)) for n in ARCHIVOS)
        registro = [servicio.procesar_muestra(a) for a in (a1, a2, a1 * 0.7)]
        servicio.registrar("ana", registro, consentimiento=True)

        mismo = servicio.verificar("ana", servicio.procesar_muestra(a_prueba))
        self.assertTrue(mismo.coincide, mismo.similitud)
        otro = servicio.verificar("ana", servicio.procesar_muestra(b_prueba))
        self.assertFalse(otro.coincide, otro.similitud)

    def test_muestra_invalida_no_llega_al_modelo(self):
        servicio = ServicioVoz(RepositorioBiometrico())
        with self.assertRaises(BiometriaError):
            servicio.procesar_muestra(np.zeros(4 * SR, np.float32))
