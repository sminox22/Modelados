from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)

from controllers.problem_controller import ProblemController
from interfaces.widgets import EncabezadoPagina
from utils.exceptions import AppException


class HistoryScreen(QWidget):
    def __init__(self, usuario_actual, on_volver=None):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.controller = ProblemController()
        self._construir_ui(on_volver)
        self._cargar_historial()

    def _construir_ui(self, on_volver):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        encabezado = EncabezadoPagina("Historial de consultas",
                                      "Problemas resueltos con la Inteligencia Artificial, del más reciente al más antiguo.")

        fila_busqueda = QHBoxLayout()
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar por texto del problema...")
        self.input_buscar.setClearButtonEnabled(True)
        self.input_buscar.textChanged.connect(self._cargar_historial)
        fila_busqueda.addWidget(self.input_buscar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Problema", "Respuesta"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setWordWrap(True)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(encabezado)
        layout.addLayout(fila_busqueda)
        layout.addWidget(self.tabla)

        if on_volver is not None:
            boton_volver = QPushButton("Volver al menú")
            boton_volver.setObjectName("secundario")
            boton_volver.clicked.connect(on_volver)
            layout.addWidget(boton_volver)

    def _cargar_historial(self):
        try:
            filtro = self.input_buscar.text().strip() or None
            registros = self.controller.obtener_historial(self.usuario_actual["usuario"], filtro)
        except AppException:
            registros = []

        self.tabla.setRowCount(len(registros))
        for fila, (problema, respuesta, fecha, hora) in enumerate(registros):
            self.tabla.setItem(fila, 0, QTableWidgetItem(f"{fecha} {hora}"))
            self.tabla.setItem(fila, 1, QTableWidgetItem(problema))
            self.tabla.setItem(fila, 2, QTableWidgetItem(respuesta))

    def al_mostrar(self):
        # Recarga al volver a la pantalla para incluir consultas recientes
        self._cargar_historial()
