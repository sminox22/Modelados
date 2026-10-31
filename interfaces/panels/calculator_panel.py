from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt

from utils.calculator import evaluar_expresion
from utils.exceptions import CalculoError


class CalculatorPanel(QWidget):
    """Calculadora básica que funciona sin conexión a Internet ni IA."""

    BOTONES = [
        ("C", "peligro"), ("(", "secundario"), (")", "secundario"), ("÷", "secundario"),
        ("7", None), ("8", None), ("9", None), ("×", "secundario"),
        ("4", None), ("5", None), ("6", None), ("-", "secundario"),
        ("1", None), ("2", None), ("3", None), ("+", "secundario"),
        ("0", None), (".", None), ("⌫", "secundario"), ("=", None),
    ]

    def __init__(self):
        super().__init__()
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        self.pantalla = QLineEdit()
        self.pantalla.setPlaceholderText("0")
        self.pantalla.setAlignment(Qt.AlignRight)
        self.pantalla.setFixedHeight(60)
        self.pantalla.setStyleSheet("font-size: 26px; font-weight: 600;")
        self.pantalla.returnPressed.connect(self._calcular)

        self.label_resultado = QLabel("")
        self.label_resultado.setAlignment(Qt.AlignRight)
        self.label_resultado.setObjectName("subtitulo")

        self.label_error = QLabel("")
        self.label_error.setObjectName("error")

        cuadricula = QGridLayout()
        cuadricula.setSpacing(8)
        fila, columna = 0, 0
        for texto, estilo in self.BOTONES:
            boton = QPushButton(texto)
            boton.setFixedHeight(52)
            if estilo:
                boton.setObjectName(estilo)
            boton.clicked.connect(lambda _, t=texto: self._click_boton(t))
            cuadricula.addWidget(boton, fila, columna)
            columna += 1
            if columna > 3:
                columna = 0
                fila += 1

        nota = QLabel("Calculadora (funciona sin conexión a Internet)")
        nota.setObjectName("subtitulo")
        layout.addWidget(nota)
        layout.addWidget(self.pantalla)
        layout.addWidget(self.label_resultado)
        layout.addWidget(self.label_error)
        layout.addLayout(cuadricula)
        layout.addStretch()

    def _click_boton(self, texto):
        self.label_error.setText("")
        if texto == "C":
            self.pantalla.clear()
            self.label_resultado.setText("")
        elif texto == "⌫":
            self.pantalla.setText(self.pantalla.text()[:-1])
        elif texto == "=":
            self._calcular()
        else:
            self.pantalla.setText(self.pantalla.text() + texto)

    def _calcular(self):
        self.label_error.setText("")
        try:
            resultado = evaluar_expresion(self.pantalla.text())
            if isinstance(resultado, float) and resultado.is_integer():
                resultado = int(resultado)
            self.label_resultado.setText(f"= {resultado}")
        except CalculoError as e:
            self.label_error.setText(e.message)
        except Exception as e:
            self.label_error.setText(f"Error inesperado: {e}")
