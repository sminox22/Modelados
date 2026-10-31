from PyQt5.QtWidgets import QFrame, QHBoxLayout, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from interfaces.panels.calculator_panel import CalculatorPanel
from interfaces.panels.ia_panel import IAPanel
from interfaces.panels.graph_panel import GraphPanel
from interfaces.widgets import EncabezadoPagina


class SolveScreen(QWidget):
    """
    Pantalla "Resolver problema": permite elegir entre tres modos:
    Calculadora (cálculo directo, sin IA), Inteligencia Artificial
    (texto/imagen/foto de iPhone), y Graficar (dibuja una función f(x)).
    """

    def __init__(self, usuario_actual, on_volver=None):
        super().__init__()
        self.usuario_actual = usuario_actual
        self._construir_ui(on_volver)

    def _construir_ui(self, on_volver):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 20)
        layout.setSpacing(14)

        layout.addWidget(EncabezadoPagina(
            "Resolver problema matemático",
            "Elija un modo: calculadora sin conexión, resolución con Inteligencia Artificial o graficador."))

        # ---------------- Selector de modo (control segmentado) ----------------
        barra_modos = QFrame()
        barra_modos.setObjectName("barra_segmentos")
        fila_modos = QHBoxLayout(barra_modos)
        fila_modos.setContentsMargins(4, 4, 4, 4)
        fila_modos.setSpacing(4)
        self.boton_calculadora = QPushButton("Calculadora")
        self.boton_ia = QPushButton("Inteligencia Artificial")
        self.boton_graficar = QPushButton("Graficar")

        for boton in (self.boton_calculadora, self.boton_ia, self.boton_graficar):
            boton.setCheckable(True)
            boton.setObjectName("segmento")
            fila_modos.addWidget(boton)
        fila_selector = QHBoxLayout()
        fila_selector.addWidget(barra_modos)
        fila_selector.addStretch()
        layout.addLayout(fila_selector)

        self.boton_calculadora.clicked.connect(lambda: self._cambiar_modo(0))
        self.boton_ia.clicked.connect(lambda: self._cambiar_modo(1))
        self.boton_graficar.clicked.connect(lambda: self._cambiar_modo(2))

        # ---------------- Paneles ----------------
        self.stack = QStackedWidget()
        self.panel_calculadora = CalculatorPanel()
        self.panel_ia = IAPanel(self.usuario_actual)
        self.panel_graficar = GraphPanel()

        self.stack.addWidget(self.panel_calculadora)  # índice 0
        self.stack.addWidget(self.panel_ia)             # índice 1
        self.stack.addWidget(self.panel_graficar)        # índice 2
        layout.addWidget(self.stack, 1)

        if on_volver is not None:
            boton_volver = QPushButton("Volver al menú")
            boton_volver.setObjectName("secundario")
            boton_volver.clicked.connect(on_volver)
            layout.addWidget(boton_volver)

        # Modo inicial: Inteligencia Artificial (el más usado)
        self._cambiar_modo(1)

    def _cambiar_modo(self, indice: int):
        self.stack.setCurrentIndex(indice)
        self.boton_calculadora.setChecked(indice == 0)
        self.boton_ia.setChecked(indice == 1)
        self.boton_graficar.setChecked(indice == 2)

    def al_cambiar_tema(self):
        self.panel_graficar.al_cambiar_tema()
