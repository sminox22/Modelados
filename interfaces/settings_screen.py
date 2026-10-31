"""Configuración (apariencia, dispositivos, modelos) y privacidad (datos biométricos)."""
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core import settings
from interfaces.widgets import Banner, EncabezadoPagina, Pastilla, Tarjeta, boton, confirmar, pagina_desplazable
from services import teachable_service
from services.ai_service import AIService
from services.audio_recorder import listar_microfonos
from utils.exceptions import AppException

NOMBRES_TIPO = {"rostro": "Rostro", "voz": "Voz"}


class SettingsScreen(QWidget):
    def __init__(self, contexto, on_cambiar_tema):
        super().__init__()
        self.contexto = contexto
        self.on_cambiar_tema = on_cambiar_tema
        self._construir_ui()
        self._cargar()

    def _construir_ui(self):
        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        layout.addWidget(EncabezadoPagina(
            "Configuración y privacidad",
            "Ajuste la apariencia y los dispositivos, revise los modelos instalados y gestione sus datos biométricos."))
        self.banner = Banner()
        layout.addWidget(self.banner)

        # ---------- Apariencia y dispositivos
        fila = QHBoxLayout()
        fila.setSpacing(18)
        apariencia = Tarjeta("Apariencia")
        etiqueta = QLabel("Tema")
        etiqueta.setObjectName("nota")
        self.combo_tema = QComboBox()
        self.combo_tema.addItem("Claro", "claro")
        self.combo_tema.addItem("Oscuro", "oscuro")
        self.combo_tema.currentIndexChanged.connect(self._cambiar_tema)
        apariencia.cuerpo.addWidget(etiqueta)
        apariencia.cuerpo.addWidget(self.combo_tema)
        apariencia.cuerpo.addStretch()
        fila.addWidget(apariencia, 1)

        dispositivos = Tarjeta("Dispositivos")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(12)
        rejilla.setVerticalSpacing(8)
        etiqueta_cam = QLabel("Cámara")
        etiqueta_cam.setObjectName("nota")
        self.combo_camara = QComboBox()
        self.combo_camara.addItem("Cámara 0 (normalmente la integrada)", 0)
        for indice in range(1, 5):
            self.combo_camara.addItem(f"Cámara {indice}", indice)
        self.combo_camara.setToolTip("Si la imagen no aparece, pruebe con otro número de cámara.")
        self.combo_camara.currentIndexChanged.connect(self._cambiar_camara)
        etiqueta_mic = QLabel("Micrófono")
        etiqueta_mic.setObjectName("nota")
        self.combo_mic = QComboBox()
        self.combo_mic.currentIndexChanged.connect(self._cambiar_microfono)
        actualizar = boton("Actualizar lista", "secundario", self._cargar_microfonos)
        rejilla.addWidget(etiqueta_cam, 0, 0)
        rejilla.addWidget(self.combo_camara, 0, 1)
        rejilla.addWidget(etiqueta_mic, 1, 0)
        rejilla.addWidget(self.combo_mic, 1, 1)
        rejilla.addWidget(actualizar, 2, 1, Qt.AlignLeft)
        rejilla.setColumnStretch(1, 1)
        dispositivos.cuerpo.addLayout(rejilla)
        fila.addWidget(dispositivos, 2)
        layout.addLayout(fila)

        # ---------- Privacidad
        privacidad = Tarjeta("Privacidad y datos biométricos")
        texto = QLabel(
            "Los datos faciales y de voz son información biométrica sensible. Esta aplicación:<br>"
            "• Solo los captura tras su consentimiento explícito y nunca activa la cámara o el micrófono sin que "
            "usted lo pida.<br>"
            "• No guarda fotografías ni grabaciones: solo una representación numérica cifrada (Fernet) cuya clave "
            "está protegida por su cuenta de Windows (DPAPI).<br>"
            "• Procesa todo localmente y no envía datos biométricos a Internet.")
        texto.setTextFormat(Qt.RichText)
        texto.setWordWrap(True)
        texto.setObjectName("nota")
        privacidad.cuerpo.addWidget(texto)
        fila_alm = QHBoxLayout()
        etiqueta_alm = QLabel("Almacenamiento protegido")
        etiqueta_alm.setObjectName("nota")
        self.pastilla_almacenamiento = Pastilla("", "neutra")
        fila_alm.addWidget(etiqueta_alm)
        fila_alm.addWidget(self.pastilla_almacenamiento)
        fila_alm.addStretch()
        privacidad.cuerpo.addLayout(fila_alm)

        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Tipo", "Modelo", "Muestras", "Consentimiento", ""])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionMode(QTableWidget.NoSelection)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setMinimumHeight(110)
        privacidad.cuerpo.addWidget(self.tabla)
        self.label_sin_registros = QLabel("No tiene datos biométricos registrados.")
        self.label_sin_registros.setObjectName("nota")
        privacidad.cuerpo.addWidget(self.label_sin_registros)
        self.boton_eliminar_todo = boton("Eliminar todos mis datos biométricos", "peligro", self._eliminar_todo)
        fila_boton = QHBoxLayout()
        fila_boton.addWidget(self.boton_eliminar_todo)
        fila_boton.addStretch()
        privacidad.cuerpo.addLayout(fila_boton)
        layout.addWidget(privacidad)

        # ---------- Servicio de IA externo
        ia = Tarjeta("Servicio externo de Inteligencia Artificial")
        texto_ia = QLabel(
            f"Las consultas de «Resolver problema › Inteligencia Artificial» (texto e imágenes de operaciones) se "
            f"envían al proveedor configurado (<b>{AIService.PROVEEDOR}</b>) a través de Internet para obtener la "
            "respuesta. La calculadora y el graficador funcionan sin conexión. Los módulos de rostro, voz y "
            "posturas nunca usan este servicio.")
        texto_ia.setTextFormat(Qt.RichText)
        texto_ia.setWordWrap(True)
        texto_ia.setObjectName("nota")
        ia.cuerpo.addWidget(texto_ia)
        layout.addWidget(ia)

        # ---------- Modelos
        modelos = Tarjeta("Modelos locales")
        rejilla_m = QGridLayout()
        rejilla_m.setHorizontalSpacing(14)
        rejilla_m.setVerticalSpacing(8)
        for col, titulo in enumerate(("Modelo", "Archivo", "Licencia", "Estado")):
            cab = QLabel(titulo.upper())
            cab.setObjectName("etiqueta")
            rejilla_m.addWidget(cab, 0, col)
        self.pastillas_modelos = {}
        for fila_i, info in enumerate(settings.MODELOS.values(), start=1):
            descripcion = QLabel(info.descripcion)
            descripcion.setWordWrap(True)
            archivo = QLabel(info.archivo)
            archivo.setObjectName("nota")
            archivo.setTextInteractionFlags(Qt.TextSelectableByMouse)
            licencia = QLabel(info.licencia)
            licencia.setObjectName("nota")
            pastilla = Pastilla("", "neutra")
            self.pastillas_modelos[info.clave] = pastilla
            rejilla_m.addWidget(descripcion, fila_i, 0)
            rejilla_m.addWidget(archivo, fila_i, 1)
            rejilla_m.addWidget(licencia, fila_i, 2)
            rejilla_m.addWidget(pastilla, fila_i, 3, Qt.AlignLeft)
        # Modelos personalizados de Teachable Machine (clasificadores del usuario)
        fila_tm = len(settings.MODELOS) + 1
        for clave, descripcion, archivos in (
                ("tm_imagen", "Mi modelo de imagen (Teachable Machine)", "models/teachable/imagen/model.onnx"),
                ("tm_audio", "Mi modelo de audio (Teachable Machine)", "models/teachable/audio/model.json")):
            etiqueta = QLabel(descripcion)
            etiqueta.setWordWrap(True)
            archivo = QLabel(archivos)
            archivo.setObjectName("nota")
            licencia = QLabel("Propio")
            licencia.setObjectName("nota")
            pastilla = Pastilla("", "neutra")
            self.pastillas_modelos[clave] = pastilla
            rejilla_m.addWidget(etiqueta, fila_tm, 0)
            rejilla_m.addWidget(archivo, fila_tm, 1)
            rejilla_m.addWidget(licencia, fila_tm, 2)
            rejilla_m.addWidget(pastilla, fila_tm, 3, Qt.AlignLeft)
            fila_tm += 1
        rejilla_m.setColumnStretch(0, 2)
        rejilla_m.setColumnStretch(1, 2)
        modelos.cuerpo.addLayout(rejilla_m)
        umbrales = QLabel(
            f"Umbrales de similitud: rostro ≥ {settings.UMBRAL_ROSTRO} · voz ≥ {settings.UMBRAL_VOZ:.2f}. "
            "Si falta un modelo, ejecute <code>python tools/descargar_modelos.py</code>.")
        umbrales.setTextFormat(Qt.RichText)
        umbrales.setWordWrap(True)
        umbrales.setObjectName("nota")
        modelos.cuerpo.addWidget(umbrales)
        fila_carpeta = QHBoxLayout()
        fila_carpeta.addWidget(boton("Abrir carpeta de modelos", "secundario", self._abrir_carpeta_modelos))
        fila_carpeta.addStretch()
        modelos.cuerpo.addLayout(fila_carpeta)
        layout.addWidget(modelos)
        layout.addStretch()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(pagina_desplazable(contenido))

    # ---------------------------------------------------------------- Datos
    def _cargar(self):
        ajustes = self.contexto.ajustes
        self.combo_tema.blockSignals(True)
        self.combo_tema.setCurrentIndex(max(0, self.combo_tema.findData(ajustes.tema)))
        self.combo_tema.blockSignals(False)
        self.combo_camara.blockSignals(True)
        if self.combo_camara.findData(ajustes.indice_camara) < 0:
            self.combo_camara.addItem(f"Cámara {ajustes.indice_camara}", ajustes.indice_camara)
        self.combo_camara.setCurrentIndex(self.combo_camara.findData(ajustes.indice_camara))
        self.combo_camara.blockSignals(False)
        self._cargar_microfonos()
        self._cargar_registros()
        disponibles_tm = {"tm_imagen": teachable_service.imagen_disponible(),
                          "tm_audio": teachable_service.audio_disponible()}
        for clave, pastilla in self.pastillas_modelos.items():
            if disponibles_tm.get(clave, False) or (clave in settings.MODELOS and settings.modelo_disponible(clave)):
                pastilla.establecer("Disponible", "ok")
            else:
                pastilla.establecer("No encontrado", "neutra")

    def _cargar_microfonos(self):
        self.combo_mic.blockSignals(True)
        self.combo_mic.clear()
        self.combo_mic.addItem("Predeterminado del sistema", -1)
        for indice, nombre in listar_microfonos():
            self.combo_mic.addItem(nombre, indice)
        posicion = self.combo_mic.findData(self.contexto.ajustes.dispositivo_microfono)
        self.combo_mic.setCurrentIndex(max(0, posicion))
        self.combo_mic.blockSignals(False)

    def _cargar_registros(self):
        biometria = self.contexto.biometria
        if biometria.almacenamiento_seguro:
            self.pastilla_almacenamiento.establecer("Activo (DPAPI + Fernet)", "ok")
        else:
            self.pastilla_almacenamiento.establecer("No disponible: registro deshabilitado", "neutra")
        registros = biometria.resumen(self.contexto.nombre_usuario)
        self.tabla.setRowCount(len(registros))
        for fila, registro in enumerate(registros):
            self.tabla.setItem(fila, 0, QTableWidgetItem(NOMBRES_TIPO.get(registro.tipo, registro.tipo)))
            self.tabla.setItem(fila, 1, QTableWidgetItem(registro.modelo))
            self.tabla.setItem(fila, 2, QTableWidgetItem(str(registro.n_muestras)))
            self.tabla.setItem(fila, 3, QTableWidgetItem(registro.consentimiento_fecha))
            eliminar = boton("Eliminar", "peligro", lambda _, t=registro.tipo: self._eliminar(t))
            self.tabla.setCellWidget(fila, 4, eliminar)
        self.tabla.resizeColumnToContents(4)
        self.tabla.setVisible(bool(registros))
        self.label_sin_registros.setVisible(not registros)
        self.boton_eliminar_todo.setEnabled(bool(registros))

    # ------------------------------------------------------------- Acciones
    def _cambiar_tema(self):
        self.contexto.ajustes.tema = self.combo_tema.currentData()
        self._guardar()
        self.on_cambiar_tema(self.contexto.ajustes.tema)

    def _cambiar_camara(self):
        self.contexto.ajustes.indice_camara = int(self.combo_camara.currentData())
        self._guardar()

    def _cambiar_microfono(self):
        dato = self.combo_mic.currentData()
        self.contexto.ajustes.dispositivo_microfono = -1 if dato is None else int(dato)
        self._guardar()

    def _guardar(self):
        try:
            self.contexto.guardar_ajustes()
        except OSError as e:
            self.banner.mostrar("error", f"No se pudieron guardar los ajustes: {e}")

    def _eliminar(self, tipo):
        nombre = NOMBRES_TIPO.get(tipo, tipo).lower()
        if not confirmar(self, "Eliminar dato biométrico",
                         f"Se eliminará de forma permanente su registro de {nombre}. ¿Desea continuar?",
                         "Eliminar", peligroso=True):
            return
        try:
            self.contexto.biometria.eliminar(self.contexto.nombre_usuario, tipo)
            self.banner.mostrar("exito", f"Registro de {nombre} eliminado.")
        except AppException as e:
            self.banner.mostrar("error", e.message)
        self._cargar_registros()

    def _eliminar_todo(self):
        if not confirmar(self, "Eliminar todos los datos biométricos",
                         "Se eliminarán de forma permanente todos sus registros biométricos (rostro y voz). "
                         "¿Desea continuar?", "Eliminar todo", peligroso=True):
            return
        try:
            cantidad = self.contexto.biometria.eliminar(self.contexto.nombre_usuario)
            self.banner.mostrar("exito", f"Se eliminaron {cantidad} registro(s) biométrico(s).")
        except AppException as e:
            self.banner.mostrar("error", e.message)
        self._cargar_registros()

    def _abrir_carpeta_modelos(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(settings.carpeta_modelos()))

    def al_mostrar(self):
        self._cargar_registros()
