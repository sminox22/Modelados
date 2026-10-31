from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt

from controllers.auth_controller import AuthController
from interfaces.widgets import Tarjeta
from utils.exceptions import AppException


class RegisterScreen(QWidget):
    def __init__(self, on_registro_exitoso, on_ir_login):
        super().__init__()
        self.on_registro_exitoso = on_registro_exitoso
        self.on_ir_login = on_ir_login
        self.controller = AuthController()
        self._construir_ui()

    def _construir_ui(self):
        externo = QVBoxLayout(self)
        externo.setAlignment(Qt.AlignCenter)
        tarjeta = Tarjeta(margen=32)
        tarjeta.setFixedWidth(400)
        externo.addWidget(tarjeta, alignment=Qt.AlignCenter)
        layout = tarjeta.cuerpo
        layout.setSpacing(12)

        titulo = QLabel("Registro de usuario")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)

        subtitulo = QLabel("Cree una cuenta para guardar su historial.")
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignCenter)

        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Nombre completo")

        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario (3-20 caracteres)")

        self.input_contrasena = QLineEdit()
        self.input_contrasena.setPlaceholderText("Contraseña (mínimo 4 caracteres)")
        self.input_contrasena.setEchoMode(QLineEdit.Password)

        self.label_error = QLabel("")
        self.label_error.setObjectName("error")
        self.label_error.setWordWrap(True)
        self.label_error.setAlignment(Qt.AlignCenter)

        boton_registrar = QPushButton("Registrarme")
        boton_registrar.clicked.connect(self._registrar)

        boton_volver = QPushButton("Ya tengo una cuenta")
        boton_volver.setObjectName("secundario")
        boton_volver.clicked.connect(self.on_ir_login)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addSpacing(8)
        layout.addWidget(self.input_nombre)
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_contrasena)
        layout.addWidget(self.label_error)
        layout.addWidget(boton_registrar)
        layout.addWidget(boton_volver)

    def _registrar(self):
        self.label_error.setText("")
        try:
            self.controller.registrar(
                self.input_nombre.text(),
                self.input_usuario.text(),
                self.input_contrasena.text(),
            )
            usuario = self.input_usuario.text()
            self.input_nombre.clear()
            self.input_usuario.clear()
            self.input_contrasena.clear()
            self.on_registro_exitoso(usuario)
        except AppException as e:
            self.label_error.setText(e.message)
        except Exception as e:
            self.label_error.setText(f"Error inesperado: {e}")
