"""
Contenedor principal tras iniciar sesión: barra lateral de navegación y área
de trabajo. Las pantallas se crean al visitarlas por primera vez y se
conservan; al salir de una pantalla se llama a su método 'al_ocultar' (si
existe) para detener cámara o micrófono.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from interfaces.face_screen import FaceScreen
from interfaces.history_screen import HistoryScreen
from interfaces.home_screen import HomeScreen
from interfaces.info_screen import InfoScreen
from interfaces.pose_screen import PoseScreen
from interfaces.settings_screen import SettingsScreen
from interfaces.solve_screen import SolveScreen
from interfaces.voice_screen import VoiceScreen
from interfaces.widgets import Separador, icono_nav

NAVEGACION = [
    (None, [("inicio", "Inicio")]),
    ("MATEMÁTICAS", [("resolver", "Resolver problema"), ("historial", "Historial")]),
    ("BIOMETRÍA Y VISIÓN", [("rostro", "Reconocimiento facial"), ("voz", "Verificación de voz"),
                            ("postura", "Posturas corporales")]),
    ("SISTEMA", [("ajustes", "Configuración y privacidad"), ("info", "Información")]),
]


class AppShell(QWidget):
    def __init__(self, contexto, on_cerrar_sesion, on_salir, on_cambiar_tema):
        super().__init__()
        self.setObjectName("raiz")
        self.contexto = contexto
        self.on_cerrar_sesion = on_cerrar_sesion
        self.on_salir = on_salir
        self.on_cambiar_tema = on_cambiar_tema
        self.paginas = {}
        self.botones = {}
        self.actual = None
        self._construir_ui()
        self.navegar("inicio")

    def _construir_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        barra = QFrame()
        barra.setObjectName("barra_lateral")
        barra.setFixedWidth(250)
        lateral = QVBoxLayout(barra)
        lateral.setContentsMargins(12, 18, 12, 14)
        lateral.setSpacing(2)

        marca = QLabel("Software Matemático IA")
        marca.setObjectName("marca")
        marca.setContentsMargins(12, 0, 0, 8)
        lateral.addWidget(marca)

        self.grupo = QButtonGroup(self)
        self.grupo.setExclusive(True)
        for titulo_grupo, elementos in NAVEGACION:
            if titulo_grupo:
                etiqueta = QLabel(titulo_grupo)
                etiqueta.setObjectName("grupo_nav")
                lateral.addWidget(etiqueta)
            for clave, texto in elementos:
                b = self._boton_nav(clave, texto, checkable=True)
                b.clicked.connect(lambda _, c=clave: self.navegar(c))
                self.grupo.addButton(b)
                self.botones[clave] = b
                lateral.addWidget(b)
        lateral.addStretch()

        lateral.addWidget(Separador())
        usuario = QLabel(f"{self.contexto.usuario.get('nombre', '')}\n@{self.contexto.nombre_usuario}")
        usuario.setObjectName("nota")
        usuario.setContentsMargins(12, 8, 0, 6)
        lateral.addWidget(usuario)
        self.boton_cerrar_sesion = self._boton_nav("cerrar_sesion", "Cerrar sesión")
        self.boton_cerrar_sesion.clicked.connect(self.on_cerrar_sesion)
        self.boton_salir = self._boton_nav("salir", "Salir")
        self.boton_salir.clicked.connect(self.on_salir)
        lateral.addWidget(self.boton_cerrar_sesion)
        lateral.addWidget(self.boton_salir)

        self.stack = QStackedWidget()
        layout.addWidget(barra)
        layout.addWidget(self.stack, 1)

    def _boton_nav(self, clave, texto, checkable=False) -> QPushButton:
        b = QPushButton(texto)
        b.setObjectName("nav")
        b.setCheckable(checkable)
        b.setCursor(Qt.PointingHandCursor)
        b.setProperty("clave_icono", clave)
        b.setIcon(icono_nav(clave))
        return b

    def _crear_pagina(self, clave):
        c = self.contexto
        fabricas = {
            "inicio": lambda: HomeScreen(c, self.navegar),
            "resolver": lambda: SolveScreen(c.usuario, on_volver=None),
            "historial": lambda: HistoryScreen(c.usuario, on_volver=None),
            "rostro": lambda: FaceScreen(c),
            "voz": lambda: VoiceScreen(c),
            "postura": lambda: PoseScreen(c),
            "ajustes": lambda: SettingsScreen(c, self.on_cambiar_tema),
            "info": lambda: InfoScreen(on_volver=None),
        }
        return fabricas[clave]()

    def navegar(self, clave):
        if clave == self.actual:
            return
        anterior = self.paginas.get(self.actual)
        if anterior is not None and hasattr(anterior, "al_ocultar"):
            anterior.al_ocultar()
        if clave not in self.paginas:
            pagina = self._crear_pagina(clave)
            self.paginas[clave] = pagina
            self.stack.addWidget(pagina)
        pagina = self.paginas[clave]
        self.stack.setCurrentWidget(pagina)
        self.actual = clave
        self.botones[clave].setChecked(True)
        if hasattr(pagina, "al_mostrar"):
            pagina.al_mostrar()

    def actualizar_tema(self):
        """Repinta iconos y gráficos que no dependen solo de la hoja de estilos."""
        for b in list(self.botones.values()) + [self.boton_cerrar_sesion, self.boton_salir]:
            b.setIcon(icono_nav(b.property("clave_icono")))
        for pagina in self.paginas.values():
            if hasattr(pagina, "al_cambiar_tema"):
                pagina.al_cambiar_tema()
        # La página de inicio dibuja iconos con el color de acento: se recrea si existe
        if "inicio" in self.paginas and self.actual != "inicio":
            vieja = self.paginas.pop("inicio")
            self.stack.removeWidget(vieja)
            vieja.deleteLater()

    def cerrar(self):
        """Detiene cámara y micrófono de todas las pantallas (al cerrar sesión o salir)."""
        for pagina in self.paginas.values():
            if hasattr(pagina, "al_ocultar"):
                pagina.al_ocultar()
