"""
Pruebas de la interfaz sin hardware: navegación, temas, permisos denegados,
cámara inexistente y liberación de recursos con una cámara simulada.
"""
import os
import sys
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PyQt5.QtCore import QCoreApplication  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import interfaces.permisos as permisos  # noqa: E402
import interfaces.workers as workers  # noqa: E402
from tests.utilidades import EntornoAislado  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)


def esperar(condicion, segundos=5.0):
    limite = time.time() + segundos
    while time.time() < limite:
        QCoreApplication.processEvents()
        if condicion():
            return True
        time.sleep(0.01)
    return False


class CamaraFalsa:
    """Sustituye a CamaraLocal: entrega fotogramas sintéticos y registra si fue liberada."""
    instancias = []

    def __init__(self, indice=0, *args, **kwargs):
        self.abierta = False
        self.liberada = False
        CamaraFalsa.instancias.append(self)

    def abrir(self):
        self.abierta = True

    def leer(self):
        time.sleep(0.01)
        return np.full((480, 640, 3), 120, np.uint8)

    def liberar(self):
        self.liberada = True


class PruebasInterfaz(EntornoAislado):
    def setUp(self):
        super().setUp()
        import main
        from controllers.auth_controller import AuthController
        AuthController().registrar("Ana María", "ana", "clave1234")
        self.ventana = main.MainWindow()
        self.ventana._on_login_exitoso(AuthController().iniciar_sesion("ana", "clave1234"))
        self._camara_original = workers.CamaraLocal
        self._confirmar_original = permisos.confirmar
        CamaraFalsa.instancias = []

    def tearDown(self):
        workers.CamaraLocal = self._camara_original
        permisos.confirmar = self._confirmar_original
        self.ventana.close()
        self.ventana.deleteLater()
        QCoreApplication.processEvents()
        super().tearDown()

    def test_navegacion_por_todas_las_secciones(self):
        shell = self.ventana.shell
        for clave in ("inicio", "resolver", "historial", "rostro", "voz", "postura", "ajustes", "info", "inicio"):
            shell.navegar(clave)
            self.assertIs(shell.stack.currentWidget(), shell.paginas[clave])
            self.assertTrue(shell.botones[clave].isChecked())

    def test_cambio_de_tema_se_guarda(self):
        from core.settings import cargar_ajustes
        self.ventana.shell.navegar("ajustes")
        pagina = self.ventana.shell.paginas["ajustes"]
        pagina.combo_tema.setCurrentIndex(pagina.combo_tema.findData("oscuro"))
        self.assertEqual(cargar_ajustes().tema, "oscuro")
        self.assertIn("#17181A", app.styleSheet())

    def test_camara_no_se_activa_sin_permiso(self):
        permisos.confirmar = lambda *a, **k: False
        self.ventana.shell.navegar("rostro")
        pagina = self.ventana.shell.paginas["rostro"]
        self.assertIsNone(pagina.hilo)
        self.assertFalse(pagina.activar_camara())
        self.assertIsNone(pagina.hilo)

    def test_camara_inexistente_muestra_error(self):
        permisos.confirmar = lambda *a, **k: True
        self.ventana.ajustes.indice_camara = 9
        self.ventana.shell.navegar("postura")
        pagina = self.ventana.shell.paginas["postura"]
        pagina.activar_camara()
        self.assertTrue(esperar(lambda: pagina.hilo is None, 20))
        self.assertFalse(pagina.banner.isHidden())
        self.assertIn("cámara", pagina.banner.text().lower())

    def test_salir_de_la_pantalla_libera_la_camara(self):
        permisos.confirmar = lambda *a, **k: True
        workers.CamaraLocal = CamaraFalsa
        shell = self.ventana.shell
        shell.navegar("rostro")
        pagina = shell.paginas["rostro"]
        self.assertTrue(pagina.activar_camara())
        hilo = pagina.hilo
        self.assertTrue(esperar(lambda: pagina.video.pixmap() is not None and not pagina.video.pixmap().isNull()))
        shell.navegar("inicio")
        self.assertIsNone(pagina.hilo)
        self.assertTrue(hilo.isFinished())
        self.assertTrue(CamaraFalsa.instancias[-1].liberada)

    def test_cerrar_la_ventana_libera_la_camara(self):
        permisos.confirmar = lambda *a, **k: True
        workers.CamaraLocal = CamaraFalsa
        self.ventana.shell.navegar("postura")
        pagina = self.ventana.shell.paginas["postura"]
        pagina.activar_camara()
        hilo = pagina.hilo
        self.assertTrue(esperar(lambda: len(CamaraFalsa.instancias) == 1 and CamaraFalsa.instancias[0].abierta))
        self.ventana.close()
        self.assertTrue(hilo.isFinished())
        self.assertTrue(CamaraFalsa.instancias[0].liberada)

    def test_reconocimiento_con_modelo_teachable(self):
        from services import teachable_service
        if not teachable_service.imagen_disponible():
            self.skipTest("No hay modelo de imagen de Teachable Machine")
        permisos.confirmar = lambda *a, **k: True
        workers.CamaraLocal = CamaraFalsa
        self.ventana.shell.navegar("rostro")
        pagina = self.ventana.shell.paginas["rostro"]
        self.assertTrue(pagina.casilla_tm.isChecked())       # activo por defecto
        pagina.activar_camara()
        textos_espera = ("Active la cámara para reconocer", "Analizando…")
        self.assertTrue(esperar(lambda: len(pagina._historial_tm) >= 2, 15))
        self.assertNotIn(pagina.label_persona.text(), textos_espera)
        self.ventana.shell.navegar("inicio")
        self.assertEqual(pagina.label_persona.text(), "Active la cámara para reconocer")

    def test_interfaz_responde_durante_tarea(self):
        resultados = []
        hilo = workers.HiloTarea(lambda: time.sleep(0.5) or 42)
        hilo.exito.connect(resultados.append)
        inicio = time.time()
        hilo.start()
        # El hilo principal sigue procesando eventos mientras la tarea corre
        self.assertLess(time.time() - inicio, 0.1)
        self.assertTrue(esperar(lambda: resultados == [42]))
        hilo.wait()


if __name__ == "__main__":
    unittest.main()
