from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit

from interfaces.widgets import EncabezadoPagina


class InfoScreen(QWidget):
    def __init__(self, on_volver=None):
        super().__init__()
        self._construir_ui(on_volver)

    def _construir_ui(self, on_volver):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        encabezado = EncabezadoPagina("Información del sistema", "Versión 2.0")

        texto = QTextEdit()
        texto.setReadOnly(True)
        texto.setPlainText(
            "Software Matemático Inteligente con Inteligencia Artificial\n"
            "Versión: 2.0\n\n"
            "Programa de Formación: Análisis y Desarrollo de Software (ADSO)\n"
            "SENA - Centro de Gestión y Desarrollo Sostenible Surcolombiano\n\n"
            "Descripción:\n"
            "Aplicación de escritorio que permite a los aprendices registrar una "
            "cuenta, iniciar sesión y resolver problemas matemáticos apoyándose "
            "en un servicio de Inteligencia Artificial, ya sea escribiendo el problema o "
            "cargando una foto de la operación. Cada consulta (problema, "
            "procedimiento, resultado, fecha y hora) se almacena en un historial "
            "personal guardado en una base de datos SQLite local.\n\n"
            "Módulos de visión por computador y biometría (procesamiento local):\n"
            "- Reconocimiento facial: registro y verificación de identidad (YuNet + SFace).\n"
            "- Verificación de voz: registro y verificación del hablante (CAM++ con sherpa-onnx).\n"
            "- Posturas corporales: puntos del cuerpo, esqueleto y ángulos (MediaPipe Pose).\n"
            "Los datos biométricos se guardan cifrados y pueden eliminarse en cualquier momento.\n\n"
            "Tecnologías utilizadas:\n"
            "- Python 3.10\n"
            "- PyQt5 (interfaz gráfica)\n"
            "- SQLite (base de datos)\n"
            "- API de Inteligencia Artificial (configurable)\n"
            "- OpenCV, MediaPipe, sherpa-onnx y sounddevice (visión y audio)\n"
            "- cryptography (cifrado de datos biométricos)\n"
            "- PyInstaller (generación del ejecutable .exe)\n"
        )

        layout.addWidget(encabezado)
        layout.addWidget(texto)

        if on_volver is not None:
            boton_volver = QPushButton("Volver al menú")
            boton_volver.setObjectName("secundario")
            boton_volver.clicked.connect(on_volver)
            layout.addWidget(boton_volver)
