"""Registro biométrico al crear la cuenta e inicio de sesión con rostro (+ gesto) y voz."""
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PyQt5.QtCore import QCoreApplication  # noqa: E402
from PyQt5.QtWidgets import QApplication, QDialog  # noqa: E402

from core.secure_storage import dpapi_disponible  # noqa: E402
from services import pose_analysis as pa  # noqa: E402
from services.biometric_login import identificar  # noqa: E402
from storage.biometric_repository import PlantillaBiometrica  # noqa: E402
from tests.test_posturas import esqueleto  # noqa: E402
from tests.utilidades import EntornoAislado  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)


def vector(semilla, dim=128):
    return np.random.default_rng(semilla).standard_normal(dim).astype(np.float32)


def plantilla(usuario, v):
    return PlantillaBiometrica(usuario, "rostro", "m", v / np.linalg.norm(v), 5, "f", "c")


class PruebasIdentificacion(unittest.TestCase):
    def setUp(self):
        self.a, self.b = vector(1), vector(2)
        self.plantillas = [plantilla("ana", self.a), plantilla("luis", self.b)]

    def test_identifica_la_cuenta_correcta(self):
        muestra = self.a + 0.3 * vector(3)
        resultado = identificar(self.plantillas, [muestra], 0.45)
        self.assertEqual(resultado.usuario, "ana")

    def test_rechaza_rostro_desconocido(self):
        self.assertIsNone(identificar(self.plantillas, [vector(9)], 0.45))

    def test_rechaza_ambiguedad(self):
        mezcla = self.a / np.linalg.norm(self.a) + self.b / np.linalg.norm(self.b)
        self.assertIsNone(identificar(self.plantillas, [mezcla], 0.3, margen=0.05))

    def test_filtro_por_usuario(self):
        self.assertIsNone(identificar(self.plantillas, [self.a], 0.45, usuario="luis"))
        self.assertEqual(identificar(self.plantillas, [self.a], 0.45, usuario="ana").usuario, "ana")


class PruebasGesto(unittest.TestCase):
    def levantar(self, puntos, muneca, codo, x):
        puntos[codo] = pa.Punto(x, 110, 0.99)
        puntos[muneca] = pa.Punto(x, 60, 0.99)

    def test_manos(self):
        puntos = esqueleto()
        puntos[pa.MUNECA_IZQ] = pa.Punto(370, 280, 0.99)     # brazos abajo
        puntos[pa.MUNECA_DER] = pa.Punto(270, 280, 0.99)
        self.assertFalse(pa.mano_levantada(puntos, "derecha"))
        self.levantar(puntos, pa.MUNECA_DER, pa.CODO_DER, 270)
        self.assertTrue(pa.mano_levantada(puntos, "derecha"))
        self.assertFalse(pa.mano_levantada(puntos, "izquierda"))
        self.assertFalse(pa.mano_levantada(puntos, "ambas"))
        self.levantar(puntos, pa.MUNECA_IZQ, pa.CODO_IZQ, 370)
        self.assertTrue(pa.mano_levantada(puntos, "ambas"))
        self.assertFalse(pa.mano_levantada(puntos, "derecha"))   # pidió solo una mano

    def test_sin_hombros_visibles(self):
        puntos = esqueleto()
        puntos[pa.HOMBRO_DER] = pa.Punto(280, 150, 0.1)
        self.assertFalse(pa.mano_levantada(puntos, "derecha"))


class ProcesadorFalso:
    def __init__(self):
        self.gesto = None

    def pedir_gesto(self, gesto):
        self.gesto = gesto


@unittest.skipUnless(dpapi_disponible(), "DPAPI solo existe en Windows")
class PruebasFlujoAcceso(EntornoAislado):
    def setUp(self):
        super().setUp()
        import main
        from controllers.auth_controller import AuthController
        AuthController().registrar("Ana María", "ana", "clave1234")
        AuthController().registrar("Luis", "luis", "clave1234")
        self.ventana = main.MainWindow()
        self.biometria = self.ventana.biometria
        self.rostro_ana = vector(1)
        self.biometria.repositorio.guardar("ana", "rostro", "opencv-sface-2021dec",
                                           self.rostro_ana / np.linalg.norm(self.rostro_ana), 5, "f")
        self.biometria.repositorio.guardar("luis", "rostro", "opencv-sface-2021dec", vector(2), 5, "f")
        from interfaces.biometric_dialogs import DialogoAccesoFacial
        self._iniciar_camara_original = DialogoAccesoFacial.iniciar_camara

    def tearDown(self):
        from interfaces.biometric_dialogs import DialogoAccesoFacial
        DialogoAccesoFacial.iniciar_camara = self._iniciar_camara_original
        self.ventana.close()
        self.ventana.deleteLater()
        QCoreApplication.processEvents()
        super().tearDown()

    def test_registro_lleva_a_pantalla_biometrica(self):
        from interfaces.biometric_enroll_screen import BiometricEnrollScreen
        self.ventana._mostrar_registro()
        pantalla = self.ventana.stack.currentWidget()
        pantalla.input_nombre.setText("Nueva Persona")
        pantalla.input_usuario.setText("nueva")
        pantalla.input_contrasena.setText("clave1234")
        pantalla._registrar()
        actual = self.ventana.stack.currentWidget()
        self.assertIsInstance(actual, BiometricEnrollScreen)
        self.assertEqual(actual.usuario, "nueva")
        self.assertEqual(actual.pastilla_rostro.text(), "Sin registrar")
        actual.boton_continuar.click()
        self.assertTrue(hasattr(self.ventana.stack.currentWidget(), "boton_rostro"))

    def test_botones_de_acceso_en_login(self):
        self.ventana._mostrar_login()
        login = self.ventana.stack.currentWidget()
        self.assertTrue(login.boton_rostro.isEnabled())       # hay rostros registrados
        self.assertFalse(login.boton_voz.isEnabled())         # nadie registró su voz

    def _dialogo_facial(self, usuario=None):
        from interfaces.biometric_dialogs import DialogoAccesoFacial
        DialogoAccesoFacial.iniciar_camara = lambda self_: True    # sin cámara real
        dialogo = DialogoAccesoFacial(None, self.ventana.ajustes, self.ventana.permisos_acceso,
                                      self.biometria, usuario)
        dialogo.procesador = ProcesadorFalso()
        QCoreApplication.processEvents()
        return dialogo

    def test_acceso_facial_con_gesto(self):
        dialogo = self._dialogo_facial()
        muestra = self.rostro_ana + 0.2 * vector(5)
        for _ in range(3):
            dialogo.on_resultado({"estado": "ok", "mensaje": "", "vector": muestra})
        self.assertEqual(dialogo._identificado, "ana")
        self.assertIn(dialogo.procesador.gesto, ("derecha", "izquierda", "ambas"))
        for _ in range(3):
            dialogo.on_resultado({"estado": "ok", "mensaje": "", "vector": muestra, "gesto_ok": True})
        self.assertEqual(dialogo.result(), QDialog.Accepted)
        self.assertEqual(dialogo.datos_usuario["usuario"], "ana")

    def test_acceso_facial_falla_si_cambia_el_rostro(self):
        dialogo = self._dialogo_facial()
        for _ in range(3):
            dialogo.on_resultado({"estado": "ok", "mensaje": "", "vector": self.rostro_ana})
        for _ in range(3):
            dialogo.on_resultado({"estado": "ok", "mensaje": "", "vector": vector(77), "gesto_ok": True})
        self.assertIsNone(dialogo.datos_usuario)
        self.assertTrue(dialogo.boton_reintentar.isVisibleTo(dialogo))

    def test_acceso_facial_sin_gesto_no_entra(self):
        dialogo = self._dialogo_facial()
        for _ in range(3):
            dialogo.on_resultado({"estado": "ok", "mensaje": "", "vector": self.rostro_ana})
        for _ in range(10):
            dialogo.on_resultado({"estado": "ok", "mensaje": "", "vector": self.rostro_ana, "gesto_ok": False})
        self.assertIsNone(dialogo.datos_usuario)

    def test_acceso_por_voz(self):
        from interfaces.biometric_dialogs import DialogoAccesoVoz
        voz = vector(10, 512)
        self.biometria.repositorio.guardar("luis", "voz", "m", voz / np.linalg.norm(voz), 3, "f")
        dialogo = DialogoAccesoVoz(None, self.ventana.ajustes, self.ventana.permisos_acceso, self.biometria)
        dialogo._on_vector(vector(11, 512))
        self.assertIsNone(dialogo.datos_usuario)              # voz desconocida
        dialogo._on_vector(voz + 0.2 * vector(12, 512))
        self.assertEqual(dialogo.datos_usuario["usuario"], "luis")
