import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
)

from interfaces.styles import paleta
from utils.grapher import evaluar_funcion
from utils.exceptions import CalculoError


class GraphPanel(QWidget):
    """Grafica una función f(x) en distintas formas: línea, puntos o barras."""

    def __init__(self):
        super().__init__()
        self._ultimo_dibujo = None
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        nota = QLabel("Graficar función  —  use 'x' como variable (ej: x^2 - 3*x + 2, sin(x))")
        nota.setObjectName("subtitulo")
        layout.addWidget(nota)

        fila_entrada = QHBoxLayout()
        self.input_funcion = QLineEdit()
        self.input_funcion.setPlaceholderText("f(x) = x^2 - 3*x + 2")
        self.input_funcion.returnPressed.connect(self._graficar)

        self.selector_tipo = QComboBox()
        self.selector_tipo.addItems(["Línea", "Puntos (dispersión)", "Barras"])

        fila_entrada.addWidget(self.input_funcion, 3)
        fila_entrada.addWidget(self.selector_tipo, 1)
        layout.addLayout(fila_entrada)

        fila_rango = QHBoxLayout()
        self.input_min = QLineEdit("-10")
        self.input_min.setPlaceholderText("x mínimo")
        self.input_max = QLineEdit("10")
        self.input_max.setPlaceholderText("x máximo")
        fila_rango.addWidget(QLabel("Rango de x:"))
        fila_rango.addWidget(self.input_min)
        fila_rango.addWidget(QLabel("a"))
        fila_rango.addWidget(self.input_max)
        layout.addLayout(fila_rango)

        boton_graficar = QPushButton("Graficar")
        boton_graficar.clicked.connect(self._graficar)
        layout.addWidget(boton_graficar)

        self.label_error = QLabel("")
        self.label_error.setObjectName("error")
        self.label_error.setWordWrap(True)
        layout.addWidget(self.label_error)

        # Área de la gráfica (matplotlib embebido, con la paleta del tema activo)
        self.figura = Figure(figsize=(5, 4), facecolor=paleta()["superficie"])
        self.canvas = FigureCanvas(self.figura)
        layout.addWidget(self.canvas)

    def _graficar(self):
        self.label_error.setText("")
        try:
            x_min = float(self.input_min.text().replace(",", "."))
            x_max = float(self.input_max.text().replace(",", "."))
            if x_min >= x_max:
                raise CalculoError("El valor mínimo de x debe ser menor que el máximo.")

            tipo_grafico = self.selector_tipo.currentText()
            cantidad_puntos = 60 if "Barras" in tipo_grafico or "Puntos" in tipo_grafico else 400
            valores_x = np.linspace(x_min, x_max, cantidad_puntos)
            valores_y = evaluar_funcion(self.input_funcion.text(), valores_x)

            self._dibujar(valores_x, valores_y, tipo_grafico)
        except CalculoError as e:
            self.label_error.setText(e.message)
        except ValueError:
            self.label_error.setText("El rango de x debe ser numérico (ej: -10 y 10).")
        except Exception as e:
            self.label_error.setText(f"Error inesperado: {e}")

    def _dibujar(self, valores_x, valores_y, tipo_grafico):
        self._ultimo_dibujo = (valores_x, valores_y, tipo_grafico)
        colores = paleta()
        self.figura.clear()
        self.figura.set_facecolor(colores["superficie"])
        ejes = self.figura.add_subplot(111)
        ejes.set_facecolor(colores["superficie"])

        color_linea = colores["acento"]
        if "Línea" in tipo_grafico:
            ejes.plot(valores_x, valores_y, color=color_linea, linewidth=2)
        elif "Puntos" in tipo_grafico:
            ejes.scatter(valores_x, valores_y, color=color_linea, s=18)
        elif "Barras" in tipo_grafico:
            ancho_barra = (valores_x[-1] - valores_x[0]) / max(len(valores_x), 1) * 0.8
            ejes.bar(valores_x, valores_y, width=ancho_barra, color=color_linea)

        ejes.axhline(0, color=colores["texto_ter"], linewidth=0.8)
        ejes.axvline(0, color=colores["texto_ter"], linewidth=0.8)
        ejes.tick_params(colors=colores["texto_sec"])
        for spine in ejes.spines.values():
            spine.set_color(colores["borde"])
        ejes.grid(True, color=colores["borde"], linewidth=0.5, alpha=0.8)

        self.canvas.draw()

    def al_cambiar_tema(self):
        if self._ultimo_dibujo is not None:
            self._dibujar(*self._ultimo_dibujo)
        else:
            self.figura.set_facecolor(paleta()["superficie"])
            self.canvas.draw()
