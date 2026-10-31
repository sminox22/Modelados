import io

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from services.wifi_photo_server import ServidorFotoWifi

try:
    import qrcode
except ImportError:
    qrcode = None


class DialogoFotoWifi(QDialog):
    """
    Muestra un código QR para que el usuario lo escanee con el iPhone
    (misma red WiFi) y espera a que suba una foto. Al recibirla, cierra el
    diálogo y entrega la ruta del archivo mediante 'ruta_resultado'.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tomar foto por WiFi")
        self.setMinimumSize(360, 460)
        self.ruta_resultado = None
        self.servidor = ServidorFotoWifi()

        self._construir_ui()
        self._iniciar_servidor()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._revisar_foto)
        self._timer.start()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        titulo = QLabel("Escanea este código con la cámara de tu iPhone")
        titulo.setObjectName("titulo")
        titulo.setWordWrap(True)
        titulo.setAlignment(Qt.AlignCenter)

        self.label_qr = QLabel()
        self.label_qr.setAlignment(Qt.AlignCenter)
        self.label_qr.setFixedSize(260, 260)

        self.label_url = QLabel("")
        self.label_url.setObjectName("subtitulo")
        self.label_url.setAlignment(Qt.AlignCenter)
        self.label_url.setWordWrap(True)

        self.label_estado = QLabel("Esperando foto...")
        self.label_estado.setObjectName("subtitulo")
        self.label_estado.setAlignment(Qt.AlignCenter)

        nota = QLabel(
            "Tu iPhone y este computador deben estar conectados a la "
            "MISMA red WiFi. Safari mostrará una advertencia de "
            "\"conexión no privada\": toca \"Mostrar detalles\" y luego "
            "\"visitar este sitio web\" (es normal, es tu propio "
            "computador, no un sitio externo)."
        )
        nota.setObjectName("nota")
        nota.setWordWrap(True)
        nota.setAlignment(Qt.AlignCenter)

        boton_cancelar = QPushButton("Cancelar")
        boton_cancelar.setObjectName("secundario")
        boton_cancelar.clicked.connect(self.reject)

        layout.addWidget(titulo)
        layout.addWidget(self.label_qr)
        layout.addWidget(self.label_url)
        layout.addWidget(nota)
        layout.addWidget(self.label_estado)
        layout.addWidget(boton_cancelar)

    def _iniciar_servidor(self):
        if qrcode is None:
            self.label_estado.setText(
                "Falta instalar el paquete 'qrcode' (pip install qrcode)."
            )
            return

        try:
            url = self.servidor.iniciar()
        except OSError as e:
            self.label_estado.setText(f"No se pudo iniciar el servidor local: {e}")
            return

        self.label_url.setText(url)

        imagen_qr = qrcode.make(url)
        buffer = io.BytesIO()
        imagen_qr.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue())
        self.label_qr.setPixmap(pixmap.scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _revisar_foto(self):
        ruta = self.servidor.obtener_foto_recibida()
        if ruta:
            self._timer.stop()
            self.ruta_resultado = ruta
            self.accept()

    def closeEvent(self, event):
        self._timer.stop()
        self.servidor.detener()
        super().closeEvent(event)

    def reject(self):
        self._timer.stop()
        self.servidor.detener()
        super().reject()
