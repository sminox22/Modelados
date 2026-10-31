"""
Pantalla de bienvenida.
Si existe un archivo de video en images/splash_video.mp4 lo reproduce
automáticamente; si no existe, muestra directamente la bienvenida con logo.
Ver instrucciones al final de este archivo para agregar tu propio video.
"""
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPixmap

from utils.resources import resource_path

try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_DISPONIBLE = True
except ImportError:
    MULTIMEDIA_DISPONIBLE = False


class WelcomeScreen(QWidget):
    def __init__(self, on_continuar):
        super().__init__()
        self.on_continuar = on_continuar
        self.video_widget = None
        self.player = None
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        video_path = resource_path(os.path.join("images", "splash_video.mp4"))

        if MULTIMEDIA_DISPONIBLE and os.path.exists(video_path):
            self.video_widget = QVideoWidget()
            self.video_widget.setMinimumSize(480, 270)
            self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
            self.player.setVideoOutput(self.video_widget)
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
            self.player.mediaStatusChanged.connect(self._on_estado_video)
            layout.addWidget(self.video_widget)
            self.player.play()
        else:
            # Sin video: mostrar logo/ícono estático si existe, o solo texto
            icon_path = resource_path(os.path.join("images", "icon.png"))
            if os.path.exists(icon_path):
                logo = QLabel()
                logo.setPixmap(QPixmap(icon_path).scaled(
                    140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo.setAlignment(Qt.AlignCenter)
                layout.addWidget(logo)

        titulo = QLabel("Software Matemático IA")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignCenter)

        subtitulo = QLabel("Resuelve problemas matemáticos con ayuda de Inteligencia Artificial")
        subtitulo.setObjectName("subtitulo")
        subtitulo.setAlignment(Qt.AlignCenter)
        subtitulo.setWordWrap(True)

        boton = QPushButton("Comenzar")
        boton.setFixedWidth(200)
        boton.clicked.connect(self._continuar)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addWidget(boton, alignment=Qt.AlignCenter)

    def _on_estado_video(self, estado):
        # Cuando el video termina, lo dejamos pausado en el último cuadro
        if MULTIMEDIA_DISPONIBLE and estado == QMediaPlayer.EndOfMedia:
            self.player.stop()

    def _continuar(self):
        if self.player:
            self.player.stop()
        self.on_continuar()


# ===========================================================================
# QUÉ DEBES HACER TÚ para agregar el video de apertura:
# 1. Consigue un archivo de video corto (recomendado .mp4, pocos segundos).
# 2. Cópialo dentro de la carpeta:  images/splash_video.mp4
#    (debe llamarse exactamente "splash_video.mp4" o cambia el nombre en
#    este archivo, línea "video_path = ...").
# 3. Instala el soporte multimedia si no lo tienes:
#       pip install PyQtWebEngine PyQt5
#    En Windows generalmente basta con PyQt5; si el video no reproduce,
#    instala los códecs de "K-Lite Codec Pack" o usa un .mp4 en H.264.
# 4. Si no agregas ningún video, la pantalla de bienvenida se ve igual,
#    solo que sin reproducir nada (usa el ícono estático si lo agregaste).
# ===========================================================================
