"""Componentes visuales reutilizables: encabezados, tarjetas, mensajes, video, iconos y diálogos."""
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from interfaces.styles import paleta

# Glifos de la fuente de iconos de Windows (Segoe Fluent Icons / Segoe MDL2 Assets)
ICONOS = {
    "inicio": "",
    "resolver": "",
    "historial": "",
    "rostro": "",
    "voz": "",
    "postura": "",
    "ajustes": "",
    "info": "",
    "salir": "",
    "cerrar_sesion": "",
    "camara": "",
    "escudo": "",
}

_fuente_iconos = None


def _familia_iconos():
    global _fuente_iconos
    if _fuente_iconos is None:
        familias = set(QFontDatabase().families())
        _fuente_iconos = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in familias), "")
    return _fuente_iconos


def icono(nombre: str, color: str = None, tamano: int = 18) -> QIcon:
    """Dibuja un icono uniforme a partir de la fuente de iconos del sistema (vacío si no existe)."""
    if not _familia_iconos() or nombre not in ICONOS:
        return QIcon()
    return QIcon(_pixmap_icono(nombre, color or paleta()["texto_sec"], tamano))


def _pixmap_icono(nombre: str, color: str, tamano: int) -> QPixmap:
    pixmap = QPixmap(tamano * 2, tamano * 2)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.TextAntialiasing)
    fuente = QFont(_familia_iconos())
    fuente.setPixelSize(int(tamano * 1.6))
    painter.setFont(fuente)
    painter.setPen(QColor(color))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, ICONOS[nombre])
    painter.end()
    return pixmap


def icono_nav(nombre: str, tamano: int = 18) -> QIcon:
    """Icono con color secundario y color de acento cuando el botón está seleccionado."""
    if not _familia_iconos() or nombre not in ICONOS:
        return QIcon()
    colores = paleta()
    resultado = QIcon()
    resultado.addPixmap(_pixmap_icono(nombre, colores["texto_sec"], tamano), QIcon.Normal, QIcon.Off)
    resultado.addPixmap(_pixmap_icono(nombre, colores["acento"], tamano), QIcon.Normal, QIcon.On)
    return resultado


class EncabezadoPagina(QWidget):
    def __init__(self, titulo: str, subtitulo: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("titulo")
        layout.addWidget(self.titulo)
        if subtitulo:
            self.subtitulo = QLabel(subtitulo)
            self.subtitulo.setObjectName("subtitulo")
            self.subtitulo.setWordWrap(True)
            layout.addWidget(self.subtitulo)


class Tarjeta(QFrame):
    def __init__(self, titulo: str = "", parent=None, margen: int = 18):
        super().__init__(parent)
        self.setObjectName("tarjeta")
        self.cuerpo = QVBoxLayout(self)
        self.cuerpo.setContentsMargins(margen, margen, margen, margen)
        self.cuerpo.setSpacing(10)
        if titulo:
            etiqueta = QLabel(titulo)
            etiqueta.setObjectName("seccion")
            self.cuerpo.addWidget(etiqueta)


class Separador(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("separador")


class Banner(QLabel):
    """Mensaje de estado: info, exito, advertencia o error."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setVisible(False)

    def mostrar(self, tipo: str, texto: str):
        self.setObjectName(f"banner_{tipo}")
        self.setText(texto)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setVisible(True)

    def ocultar(self):
        self.setVisible(False)
        self.clear()


class Pastilla(QLabel):
    """Indicador compacto de estado (ok, neutra, activa)."""

    def __init__(self, texto: str = "", tipo: str = "neutra", parent=None):
        super().__init__(texto, parent)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.establecer(texto, tipo)

    def establecer(self, texto: str, tipo: str = "neutra"):
        self.setText(texto)
        self.setObjectName(f"pastilla_{tipo}")
        self.style().unpolish(self)
        self.style().polish(self)


class VistaVideo(QLabel):
    """Muestra fotogramas escalados conservando la proporción."""

    def __init__(self, texto_vacio: str = "Cámara apagada", parent=None):
        super().__init__(parent)
        self.setObjectName("video")
        self.texto_vacio = texto_vacio
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(360, 270))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._imagen = None
        self.limpiar()

    def mostrar_imagen(self, imagen):
        self._imagen = imagen
        self._redibujar()

    def limpiar(self, texto: str = None):
        self._imagen = None
        self.setPixmap(QPixmap())
        self.setText(texto or self.texto_vacio)

    def _redibujar(self):
        if self._imagen is None:
            return
        pixmap = QPixmap.fromImage(self._imagen).scaled(
            self.width() - 2, self.height() - 2, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._redibujar()


def pagina_desplazable(contenido: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.NoFrame)
    area.setWidget(contenido)
    return area


def boton(texto: str, estilo: str = None, al_pulsar=None) -> QPushButton:
    b = QPushButton(texto)
    if estilo:
        b.setObjectName(estilo)
    if al_pulsar:
        b.clicked.connect(al_pulsar)
    b.setCursor(Qt.PointingHandCursor)
    return b


def confirmar(parent, titulo: str, texto: str, texto_aceptar: str = "Aceptar", peligroso: bool = False) -> bool:
    caja = QMessageBox(parent)
    caja.setWindowTitle(titulo)
    caja.setText(texto)
    caja.setIcon(QMessageBox.Warning if peligroso else QMessageBox.Question)
    aceptar = caja.addButton(texto_aceptar, QMessageBox.AcceptRole)
    cancelar = caja.addButton("Cancelar", QMessageBox.RejectRole)
    cancelar.setObjectName("secundario")
    if peligroso:
        aceptar.setObjectName("peligro")
    caja.setDefaultButton(cancelar)
    caja.exec_()
    return caja.clickedButton() is aceptar


class DialogoConsentimiento(QDialog):
    """Consentimiento explícito antes de capturar datos biométricos."""

    def __init__(self, parent, titulo: str, puntos: list):
        super().__init__(parent)
        self.setWindowTitle("Consentimiento para datos biométricos")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        encabezado = QLabel(titulo)
        encabezado.setObjectName("seccion")
        encabezado.setWordWrap(True)
        layout.addWidget(encabezado)

        texto = QLabel("<ul style='margin-left:-20px'>" + "".join(f"<li style='margin-bottom:6px'>{p}</li>"
                                                                  for p in puntos) + "</ul>")
        texto.setWordWrap(True)
        texto.setTextFormat(Qt.RichText)
        layout.addWidget(texto)

        self.casilla = QCheckBox("He leído la información y doy mi consentimiento explícito.")
        layout.addWidget(self.casilla)

        fila = QHBoxLayout()
        fila.addStretch()
        cancelar = boton("Cancelar", "secundario", self.reject)
        self.aceptar = boton("Continuar", None, self.accept)
        self.aceptar.setEnabled(False)
        self.casilla.toggled.connect(self.aceptar.setEnabled)
        fila.addWidget(cancelar)
        fila.addWidget(self.aceptar)
        layout.addLayout(fila)
