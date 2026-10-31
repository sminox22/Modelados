import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

from controllers.problem_controller import ProblemController
from services.ai_service import AIService
from utils.exceptions import AppException
from interfaces.wifi_photo_dialog import DialogoFotoWifi


class HiloResolucionTexto(QThread):
    exito = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, controller, usuario, problema):
        super().__init__()
        self.controller = controller
        self.usuario = usuario
        self.problema = problema

    def run(self):
        try:
            resultado = self.controller.resolver(self.usuario, self.problema)
            self.exito.emit(resultado)
        except AppException as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(f"Error inesperado: {e}")


class HiloResolucionImagen(QThread):
    exito = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, controller, usuario, ruta_imagen):
        super().__init__()
        self.controller = controller
        self.usuario = usuario
        self.ruta_imagen = ruta_imagen

    def run(self):
        try:
            resultado = self.controller.resolver_desde_imagen(self.usuario, self.ruta_imagen)
            self.exito.emit(resultado)
        except AppException as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(f"Error inesperado: {e}")


class IAPanel(QWidget):
    """Resolver un problema escribiéndolo, cargando una imagen del
    computador, o tomando una foto en el momento escaneando un código QR
    (foto por WiFi)."""

    def __init__(self, usuario_actual):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.controller = ProblemController()
        self.hilo = None
        self.ruta_imagen_seleccionada = None
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Escriba el problema, cargue una imagen, o tómela con un código QR:"))

        aviso_privacidad = QLabel(
            f"Aviso: el texto o la imagen se envían por Internet al proveedor de IA configurado "
            f"({AIService.PROVEEDOR}) para resolver el problema. No incluya datos personales.")
        aviso_privacidad.setObjectName("nota")
        aviso_privacidad.setWordWrap(True)
        layout.addWidget(aviso_privacidad)

        self.input_problema = QTextEdit()
        self.input_problema.setPlaceholderText("Ingrese el problema matemático...")
        self.input_problema.setFixedHeight(70)
        self.input_problema.textChanged.connect(self._on_texto_cambiado)

        fila_imagen = QHBoxLayout()
        self.boton_imagen = QPushButton("Seleccionar imagen")
        self.boton_imagen.setObjectName("secundario")
        self.boton_imagen.clicked.connect(self._seleccionar_imagen)

        self.boton_wifi = QPushButton("Tomar foto por WiFi (QR)")
        self.boton_wifi.setObjectName("secundario")
        self.boton_wifi.clicked.connect(self._tomar_foto_wifi)

        self.boton_quitar_imagen = QPushButton("Quitar imagen")
        self.boton_quitar_imagen.setObjectName("secundario")
        self.boton_quitar_imagen.clicked.connect(self._quitar_imagen)
        self.boton_quitar_imagen.setVisible(False)

        fila_imagen.addWidget(self.boton_imagen)
        fila_imagen.addWidget(self.boton_wifi)
        fila_imagen.addWidget(self.boton_quitar_imagen)

        self.label_nombre_imagen = QLabel("")
        self.label_nombre_imagen.setObjectName("subtitulo")

        self.preview_imagen = QLabel()
        self.preview_imagen.setFixedHeight(120)
        self.preview_imagen.setAlignment(Qt.AlignCenter)
        self.preview_imagen.setVisible(False)

        self.boton_resolver = QPushButton("Resolver")
        self.boton_resolver.clicked.connect(self._resolver)

        self.label_estado = QLabel("")
        self.label_estado.setObjectName("error")
        self.label_estado.setWordWrap(True)

        self.label_problema_detectado_titulo = QLabel("Problema detectado en la imagen")
        self.label_problema_detectado_titulo.setVisible(False)
        self.problema_detectado_area = QTextEdit()
        self.problema_detectado_area.setReadOnly(True)
        self.problema_detectado_area.setFixedHeight(40)
        self.problema_detectado_area.setVisible(False)

        self.label_procedimiento_titulo = QLabel("Procedimiento")
        self.procedimiento_area = QTextEdit()
        self.procedimiento_area.setReadOnly(True)

        self.label_resultado_titulo = QLabel("Resultado")
        self.resultado_area = QTextEdit()
        self.resultado_area.setReadOnly(True)
        self.resultado_area.setFixedHeight(50)

        layout.addWidget(self.input_problema)
        layout.addLayout(fila_imagen)
        layout.addWidget(self.label_nombre_imagen)
        layout.addWidget(self.preview_imagen)
        layout.addWidget(self.boton_resolver)
        layout.addWidget(self.label_estado)
        layout.addWidget(self.label_problema_detectado_titulo)
        layout.addWidget(self.problema_detectado_area)
        layout.addWidget(self.label_procedimiento_titulo)
        layout.addWidget(self.procedimiento_area)
        layout.addWidget(self.label_resultado_titulo)
        layout.addWidget(self.resultado_area)

    # ---------------- Imagen desde archivo ----------------
    def _seleccionar_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar foto de la operación matemática", "",
            "Imágenes (*.png *.jpg *.jpeg *.webp)",
        )
        if not ruta:
            return
        self._cargar_imagen(ruta)

    def _cargar_imagen(self, ruta: str):
        self.ruta_imagen_seleccionada = ruta
        self.label_nombre_imagen.setText(os.path.basename(ruta))
        self.boton_quitar_imagen.setVisible(True)

        pixmap = QPixmap(ruta).scaledToHeight(120, Qt.SmoothTransformation)
        self.preview_imagen.setPixmap(pixmap)
        self.preview_imagen.setVisible(True)

        self.input_problema.setEnabled(False)
        self.input_problema.setPlaceholderText("Se usará la imagen seleccionada como problema.")

    def _quitar_imagen(self):
        self.ruta_imagen_seleccionada = None
        self.label_nombre_imagen.setText("")
        self.boton_quitar_imagen.setVisible(False)
        self.preview_imagen.clear()
        self.preview_imagen.setVisible(False)
        self.input_problema.setEnabled(True)
        self.input_problema.setPlaceholderText("Ingrese el problema matemático...")

    def _on_texto_cambiado(self):
        if self.input_problema.toPlainText().strip() and self.ruta_imagen_seleccionada:
            self._quitar_imagen()

    # ---------------- Foto por WiFi (código QR) ----------------
    def _tomar_foto_wifi(self):
        self.label_estado.setText("")
        dialogo = DialogoFotoWifi(self)
        if dialogo.exec_() == DialogoFotoWifi.Accepted and dialogo.ruta_resultado:
            self._cargar_imagen(dialogo.ruta_resultado)

    # ---------------- Resolver ----------------
    def _resolver(self):
        self.label_estado.setText("")
        self.boton_resolver.setEnabled(False)
        self.boton_resolver.setText("Resolviendo...")

        if self.ruta_imagen_seleccionada:
            self.hilo = HiloResolucionImagen(
                self.controller, self.usuario_actual["usuario"], self.ruta_imagen_seleccionada
            )
            self.hilo.exito.connect(self._mostrar_resultado_imagen)
        else:
            problema = self.input_problema.toPlainText()
            self.hilo = HiloResolucionTexto(
                self.controller, self.usuario_actual["usuario"], problema
            )
            self.hilo.exito.connect(self._mostrar_resultado_texto)

        self.hilo.error.connect(self._mostrar_error)
        self.hilo.finished.connect(self._restaurar_boton_resolver)
        self.hilo.start()

    def _mostrar_resultado_texto(self, resultado: dict):
        self.label_problema_detectado_titulo.setVisible(False)
        self.problema_detectado_area.setVisible(False)
        self.procedimiento_area.setPlainText(resultado.get("procedimiento", ""))
        self.resultado_area.setPlainText(resultado.get("resultado", ""))

    def _mostrar_resultado_imagen(self, resultado: dict):
        self.label_problema_detectado_titulo.setVisible(True)
        self.problema_detectado_area.setVisible(True)
        self.problema_detectado_area.setPlainText(resultado.get("problema_detectado", ""))
        self.procedimiento_area.setPlainText(resultado.get("procedimiento", ""))
        self.resultado_area.setPlainText(resultado.get("resultado", ""))

    def _mostrar_error(self, mensaje: str):
        self.label_estado.setText(mensaje)

    def _restaurar_boton_resolver(self):
        self.boton_resolver.setEnabled(True)
        self.boton_resolver.setText("Resolver")
