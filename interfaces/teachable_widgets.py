"""Visualización de resultados de los modelos de Teachable Machine (clase principal y barras por clase)."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

CONFIANZA_MINIMA = 0.75     # mismo umbral que usa Teachable Machine por defecto


class PanelClasificacion(QWidget):
    def __init__(self, etiquetas=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.label_clase = QLabel("—")
        self.label_clase.setObjectName("metrica")
        self.label_detalle = QLabel("")
        self.label_detalle.setObjectName("nota")
        self.label_detalle.setWordWrap(True)
        layout.addWidget(self.label_clase)
        layout.addWidget(self.label_detalle)
        self._rejilla = QGridLayout()
        self._rejilla.setHorizontalSpacing(10)
        self._rejilla.setVerticalSpacing(6)
        layout.addLayout(self._rejilla)
        self._filas = {}
        if etiquetas:
            self.establecer_etiquetas(etiquetas)

    def establecer_etiquetas(self, etiquetas):
        for nombre, (etiqueta, barra, valor) in self._filas.items():
            for w in (etiqueta, barra, valor):
                w.deleteLater()
        self._filas = {}
        for i, nombre in enumerate(etiquetas):
            etiqueta = QLabel(nombre)
            etiqueta.setObjectName("nota")
            barra = QProgressBar()
            barra.setRange(0, 100)
            barra.setTextVisible(False)
            valor = QLabel("0 %")
            valor.setObjectName("nota")
            valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            valor.setMinimumWidth(40)
            self._rejilla.addWidget(etiqueta, i, 0)
            self._rejilla.addWidget(barra, i, 1)
            self._rejilla.addWidget(valor, i, 2)
            self._filas[nombre] = (etiqueta, barra, valor)
        self._rejilla.setColumnStretch(1, 1)

    def mostrar(self, resultados):
        """resultados: [(etiqueta, probabilidad)] ordenados de mayor a menor."""
        if not resultados:
            return self.limpiar()
        clase, probabilidad = resultados[0]
        self.label_clase.setText(f"{clase}  ·  {probabilidad * 100:.0f} %")
        self.label_detalle.setText(
            "" if probabilidad >= CONFIANZA_MINIMA else
            f"Confianza baja (menor al {CONFIANZA_MINIMA * 100:.0f} %): el resultado no es fiable.")
        for nombre, prob in resultados:
            if nombre in self._filas:
                _, barra, valor = self._filas[nombre]
                barra.setValue(int(round(prob * 100)))
                valor.setText(f"{prob * 100:.0f} %")

    def limpiar(self, texto: str = "—"):
        self.label_clase.setText(texto)
        self.label_detalle.setText("")
        for _, barra, valor in self._filas.values():
            barra.setValue(0)
            valor.setText("0 %")
