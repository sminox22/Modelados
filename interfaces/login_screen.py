from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
)
from PyQt5.QtCore import Qt

from controllers.auth_controller import AuthController
from interfaces.widgets import Tarjeta, icono
from utils.exceptions import AppException


class LoginScreen(QWidget):
    def __init__(self, on_login_exitoso, on_ir_registro, ajustes=None, permisos=None, biometria=None):
        super().__init__()
        self.on_login_exitoso = on_login_exitoso
        self.on_ir_registro = on_ir_registro
        self.ajustes = ajustes
        self.permisos = permisos
        self.biometria = biometria
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

        marca = QLabel("Software Matemático IA")
        marca.setObjectName("subtitulo")
        marca.setAlignment(Qt.AlignCenter)

        titulo = QLabel("Iniciar sesión")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)

        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario")

        self.input_contrasena = QLineEdit()
        self.input_contrasena.setPlaceholderText("Contraseña")
        self.input_contrasena.setEchoMode(QLineEdit.Password)

        self.label_error = QLabel("")
        self.label_error.setObjectName("error")
        self.label_error.setWordWrap(True)
        self.label_error.setAlignment(Qt.AlignCenter)

        boton_entrar = QPushButton("Entrar")
        boton_entrar.clicked.connect(self._intentar_login)

        boton_registro = QPushButton("Crear una cuenta nueva")
        boton_registro.setObjectName("secundario")
        boton_registro.clicked.connect(self.on_ir_registro)

        layout.addWidget(marca)
        layout.addWidget(titulo)
        layout.addSpacing(8)
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_contrasena)
        layout.addWidget(self.label_error)
        layout.addWidget(boton_entrar)

        # ---------- Acceso biométrico
        if self.biometria is not None:
            separador = QLabel("o ingrese con")
            separador.setObjectName("nota")
            separador.setAlignment(Qt.AlignCenter)
            fila_bio = QHBoxLayout()
            self.boton_rostro = QPushButton("  Mi rostro")
            self.boton_rostro.setIcon(icono("rostro"))
            self.boton_rostro.setObjectName("secundario")
            self.boton_rostro.clicked.connect(self._entrar_con_rostro)
            self.boton_voz = QPushButton("  Mi voz")
            self.boton_voz.setIcon(icono("voz"))
            self.boton_voz.setObjectName("secundario")
            self.boton_voz.clicked.connect(self._entrar_con_voz)
            fila_bio.addWidget(self.boton_rostro)
            fila_bio.addWidget(self.boton_voz)
            ayuda = QLabel("Si escribe su usuario, solo se comparará con esa cuenta.")
            ayuda.setObjectName("nota")
            ayuda.setAlignment(Qt.AlignCenter)
            ayuda.setWordWrap(True)
            layout.addWidget(separador)
            layout.addLayout(fila_bio)
            layout.addWidget(ayuda)
            layout.addSpacing(6)
            self._actualizar_biometria()

        layout.addWidget(boton_registro)

        self.input_contrasena.returnPressed.connect(self._intentar_login)

    def _actualizar_biometria(self):
        b = self.biometria
        rostro_ok = b.almacenamiento_seguro and b.modelos_rostro_disponibles() and b.modelo_postura_disponible()
        voz_ok = b.almacenamiento_seguro and b.modelo_voz_disponible()
        self.boton_rostro.setEnabled(rostro_ok and b.hay_registros("rostro"))
        self.boton_voz.setEnabled(voz_ok and b.hay_registros("voz"))
        if not self.boton_rostro.isEnabled():
            self.boton_rostro.setToolTip("Ninguna cuenta tiene un rostro registrado (o faltan los modelos).")
        if not self.boton_voz.isEnabled():
            self.boton_voz.setToolTip("Ninguna cuenta tiene una voz registrada (o falta el modelo).")

    def _entrar_biometrico(self, clase_dialogo):
        self.label_error.setText("")
        dialogo = clase_dialogo(self, self.ajustes, self.permisos, self.biometria,
                                self.input_usuario.text().strip() or None)
        if dialogo.exec_() == clase_dialogo.Accepted and dialogo.datos_usuario:
            self.input_usuario.clear()
            self.input_contrasena.clear()
            self.on_login_exitoso(dialogo.datos_usuario)

    def _entrar_con_rostro(self):
        from interfaces.biometric_dialogs import DialogoAccesoFacial
        self._entrar_biometrico(DialogoAccesoFacial)

    def _entrar_con_voz(self):
        from interfaces.biometric_dialogs import DialogoAccesoVoz
        self._entrar_biometrico(DialogoAccesoVoz)

    def _intentar_login(self):
        self.label_error.setText("")
        usuario = self.input_usuario.text()
        contrasena = self.input_contrasena.text()
        try:
            datos_usuario = self.controller.iniciar_sesion(usuario, contrasena)
            self.input_usuario.clear()
            self.input_contrasena.clear()
            self.on_login_exitoso(datos_usuario)
        except AppException as e:
            self.label_error.setText(e.message)
        except Exception as e:
            self.label_error.setText(f"Error inesperado: {e}")
