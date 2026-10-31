"""
Software Matemático Inteligente con Inteligencia Artificial
Punto de entrada de la aplicación.

Ejecutar en desarrollo:   python main.py
Generar ejecutable:       ver README.md (sección "Generar el .exe")
"""
import os
import sys
from types import SimpleNamespace

from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from controllers.biometric_controller import BiometricController
from core.settings import cargar_ajustes
from interfaces.app_shell import AppShell
from interfaces.biometric_enroll_screen import BiometricEnrollScreen
from interfaces.contexto import ContextoSesion
from interfaces.styles import construir_estilo, establecer_tema
from interfaces.welcome_screen import WelcomeScreen
from interfaces.login_screen import LoginScreen
from interfaces.register_screen import RegisterScreen
from utils.resources import resource_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Software Matemático IA")
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)
        self.usuario_actual = None
        self.ajustes = cargar_ajustes()
        self.shell = None
        self._biometria = None
        # Permisos de cámara/micrófono concedidos en las pantallas de acceso (por ejecución)
        self.permisos_acceso = SimpleNamespace(permisos=set())
        self.aplicar_tema(self.ajustes.tema)

        self._aplicar_icono()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._mostrar_bienvenida()

    # ---------------- Ícono ----------------
    def _aplicar_icono(self):
        """
        Busca images/icon.ico (Windows) o images/icon.png y lo aplica como
        ícono de la ventana y de la barra de tareas.
        """
        for nombre in ("icon.ico", "icon.png"):
            ruta = resource_path(os.path.join("images", nombre))
            if os.path.exists(ruta):
                self.setWindowIcon(QIcon(ruta))
                break

    # ---------------- Tema ----------------
    def aplicar_tema(self, nombre):
        establecer_tema(nombre)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(construir_estilo(nombre))
        if self.shell is not None:
            self.shell.actualizar_tema()

    # ---------------- Navegación entre pantallas ----------------
    def _cambiar_pantalla(self, widget):
        if self.shell is not None and widget is not self.shell:
            self.shell.cerrar()
            self.shell = None
        # Elimina la pantalla anterior del stack para liberar memoria/hilos
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.stack.addWidget(widget)
        self.stack.setCurrentWidget(widget)

    def _mostrar_bienvenida(self):
        pantalla = WelcomeScreen(on_continuar=self._mostrar_login)
        self._cambiar_pantalla(pantalla)

    def _mostrar_login(self):
        pantalla = LoginScreen(
            on_login_exitoso=self._on_login_exitoso,
            on_ir_registro=self._mostrar_registro,
            ajustes=self.ajustes,
            permisos=self.permisos_acceso,
            biometria=self.biometria,
        )
        self._cambiar_pantalla(pantalla)

    def _mostrar_registro(self):
        pantalla = RegisterScreen(
            on_registro_exitoso=self._on_registro_exitoso,
            on_ir_login=self._mostrar_login,
        )
        self._cambiar_pantalla(pantalla)

    def _on_registro_exitoso(self, usuario):
        # Tras crear la cuenta se ofrece registrar rostro y voz para el inicio de sesión
        pantalla = BiometricEnrollScreen(
            usuario=usuario.strip(),
            ajustes=self.ajustes,
            permisos=self.permisos_acceso,
            biometria=self.biometria,
            on_continuar=self._mostrar_login,
        )
        self._cambiar_pantalla(pantalla)

    def _on_login_exitoso(self, datos_usuario):
        self.usuario_actual = datos_usuario
        self._mostrar_menu()

    @property
    def biometria(self):
        # Se crea una sola vez: prepara el almacenamiento cifrado
        if self._biometria is None:
            self._biometria = BiometricController()
        return self._biometria

    def _mostrar_menu(self):
        contexto = ContextoSesion(usuario=self.usuario_actual, ajustes=self.ajustes, biometria=self.biometria,
                                  permisos=self.permisos_acceso.permisos)
        shell = AppShell(
            contexto,
            on_cerrar_sesion=self._cerrar_sesion,
            on_salir=self.close,
            on_cambiar_tema=self.aplicar_tema,
        )
        self._cambiar_pantalla(shell)
        self.shell = shell

    def _cerrar_sesion(self):
        self.usuario_actual = None
        self._mostrar_login()

    def closeEvent(self, event):
        # Libera cámara y micrófono antes de cerrar la aplicación
        if self.shell is not None:
            self.shell.cerrar()
        super().closeEvent(event)


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
