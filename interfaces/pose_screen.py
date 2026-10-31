"""Pantalla de detección de posturas corporales (visualización de puntos y ángulos)."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from interfaces.permisos import solicitar_permiso
from interfaces.widgets import Banner, EncabezadoPagina, Pastilla, Tarjeta, VistaVideo, boton, pagina_desplazable
from interfaces.workers import HiloCamara
from services.pose_analysis import ARTICULACIONES
from services.pose_service import ProcesadorCamaraPostura


class PoseScreen(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        self.hilo = None
        self.procesador = None
        self._construir_ui()

    def _construir_ui(self):
        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        layout.addWidget(EncabezadoPagina(
            "Posturas corporales",
            "Detecta puntos del cuerpo con la cámara, dibuja el esqueleto y calcula ángulos articulares. "
            "El procesamiento es local y no se guarda ninguna imagen."))

        fila = QHBoxLayout()
        fila.setSpacing(18)

        columna_video = QVBoxLayout()
        columna_video.setSpacing(10)
        self.video = VistaVideo("Cámara apagada")
        columna_video.addWidget(self.video, 1)
        controles = QHBoxLayout()
        self.boton_activar = boton("Activar cámara", None, self.activar_camara)
        self.boton_detener = boton("Detener cámara", "secundario", self.detener_camara)
        self.boton_detener.setEnabled(False)
        self.casilla_esqueleto = QCheckBox("Mostrar esqueleto")
        self.casilla_esqueleto.setChecked(True)
        self.casilla_esqueleto.toggled.connect(self._cambiar_esqueleto)
        self.pastilla_camara = Pastilla("Cámara apagada", "neutra")
        controles.addWidget(self.boton_activar)
        controles.addWidget(self.boton_detener)
        controles.addStretch()
        controles.addWidget(self.pastilla_camara)
        columna_video.addLayout(controles)
        fila.addLayout(columna_video, 3)

        lateral = QVBoxLayout()
        lateral.setContentsMargins(0, 0, 0, 0)
        lateral.setSpacing(14)

        tarjeta_deteccion = Tarjeta("Detección")
        self.pastilla_encuadre = Pastilla("Sin datos", "neutra")
        tarjeta_deteccion.cuerpo.addWidget(self.pastilla_encuadre)
        self.label_encuadre = QLabel("Active la cámara y colóquese de cuerpo completo a 2-3 metros.")
        self.label_encuadre.setWordWrap(True)
        self.label_encuadre.setObjectName("nota")
        tarjeta_deteccion.cuerpo.addWidget(self.label_encuadre)
        etiqueta_conf = QLabel("VISIBILIDAD MEDIA DE LOS PUNTOS")
        etiqueta_conf.setObjectName("etiqueta")
        tarjeta_deteccion.cuerpo.addWidget(etiqueta_conf)
        self.barra_confianza = QProgressBar()
        self.barra_confianza.setRange(0, 100)
        self.barra_confianza.setTextVisible(False)
        tarjeta_deteccion.cuerpo.addWidget(self.barra_confianza)
        self.label_confianza = QLabel("—")
        self.label_confianza.setObjectName("nota")
        tarjeta_deteccion.cuerpo.addWidget(self.label_confianza)
        tarjeta_deteccion.cuerpo.addWidget(self.casilla_esqueleto)
        lateral.addWidget(tarjeta_deteccion)

        tarjeta_postura = Tarjeta("Postura")
        self.label_postura = QLabel("—")
        self.label_postura.setObjectName("metrica")
        self.label_postura.setWordWrap(True)
        self.label_explicacion = QLabel("")
        self.label_explicacion.setObjectName("nota")
        self.label_explicacion.setWordWrap(True)
        self.label_hombros = QLabel("")
        self.label_hombros.setObjectName("nota")
        tarjeta_postura.cuerpo.addWidget(self.label_postura)
        tarjeta_postura.cuerpo.addWidget(self.label_explicacion)
        tarjeta_postura.cuerpo.addWidget(self.label_hombros)
        lateral.addWidget(tarjeta_postura)

        tarjeta_angulos = Tarjeta("Ángulos articulares")
        rejilla = QGridLayout()
        rejilla.setVerticalSpacing(6)
        self.labels_angulos = {}
        for i, nombre in enumerate(ARTICULACIONES):
            etiqueta = QLabel(nombre)
            etiqueta.setObjectName("nota")
            valor = QLabel("—")
            valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            rejilla.addWidget(etiqueta, i, 0)
            rejilla.addWidget(valor, i, 1)
            self.labels_angulos[nombre] = valor
        tarjeta_angulos.cuerpo.addLayout(rejilla)
        nota = QLabel("Solo se muestran ángulos cuyos tres puntos tienen visibilidad suficiente (≥ 60 %).")
        nota.setObjectName("nota")
        nota.setWordWrap(True)
        tarjeta_angulos.cuerpo.addWidget(nota)
        lateral.addWidget(tarjeta_angulos)

        self.banner = Banner()
        lateral.addWidget(self.banner)
        lateral.addStretch()
        contenedor = QWidget()
        contenedor.setLayout(lateral)
        contenedor.setFixedWidth(320)
        fila.addWidget(contenedor)
        layout.addLayout(fila, 1)

        alcance = Tarjeta("Alcance y limitaciones")
        texto = QLabel(
            "• Modelo: MediaPipe Pose Landmarker (lite), 33 puntos; aquí se usan hombros, codos, muñecas, caderas, "
            "rodillas y tobillos.<br>"
            "• Posturas reconocidas por reglas geométricas: <b>De pie</b> (rodillas y caderas ≥ 160°), "
            "<b>Piernas flexionadas</b> (rodillas y caderas entre 60° y 130°), <b>Brazos levantados</b> "
            "(muñecas sobre la cabeza) y <b>Brazos en cruz</b> (codos ≥ 150°, hombros entre 70° y 110°).<br>"
            "• Los ángulos se miden en la imagen 2D y cambian con la orientación respecto a la cámara.<br>"
            "• <b>No es una herramienta médica</b>: no detecta lesiones, enfermedades ni evalúa la salud.")
        texto.setTextFormat(Qt.RichText)
        texto.setWordWrap(True)
        texto.setObjectName("nota")
        alcance.cuerpo.addWidget(texto)
        layout.addWidget(alcance)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(pagina_desplazable(contenido))

    # ------------------------------------------------------------- Cámara
    def activar_camara(self):
        if self.hilo is not None:
            return
        if not self.contexto.biometria.modelo_postura_disponible():
            self.banner.mostrar("error", "Falta el modelo de posturas. Ejecute 'python tools/descargar_modelos.py'.")
            return
        if not solicitar_permiso(self, self.contexto, "camara"):
            self.banner.mostrar("info", "No se activó la cámara porque no se concedió el permiso.")
            return
        self.banner.ocultar()
        self.procesador = ProcesadorCamaraPostura(self.casilla_esqueleto.isChecked())
        self.hilo = HiloCamara(self.contexto.ajustes.indice_camara, self.procesador)
        self.hilo.camara_lista.connect(lambda: self.pastilla_camara.establecer("● Cámara activa", "activa"))
        self.hilo.fotograma.connect(self._on_fotograma)
        self.hilo.resultado.connect(self._on_resultado)
        self.hilo.error.connect(self._on_error)
        self.hilo.finished.connect(self._on_hilo_terminado)
        self.pastilla_camara.establecer("Iniciando…", "neutra")
        self.video.limpiar("Iniciando cámara y modelo…")
        self.hilo.start()
        self.boton_activar.setEnabled(False)
        self.boton_detener.setEnabled(True)

    def detener_camara(self):
        if self.hilo is not None:
            hilo, self.hilo = self.hilo, None
            hilo.detener()
        self.procesador = None
        self.video.limpiar()
        self.pastilla_camara.establecer("Cámara apagada", "neutra")
        self.boton_activar.setEnabled(True)
        self.boton_detener.setEnabled(False)
        self._limpiar_resultados()

    def _cambiar_esqueleto(self, activo):
        if self.procesador is not None:
            self.procesador.dibujar_esqueleto = activo

    def _on_fotograma(self, imagen):
        if self.sender() is self.hilo:
            self.video.mostrar_imagen(imagen)

    def _on_error(self, mensaje):
        self.banner.mostrar("error", mensaje)
        self.detener_camara()

    def _on_hilo_terminado(self):
        if self.sender() is self.hilo:
            self.hilo = None
            self.detener_camara()

    def _limpiar_resultados(self):
        self.pastilla_encuadre.establecer("Sin datos", "neutra")
        self.label_encuadre.setText("Active la cámara y colóquese de cuerpo completo a 2-3 metros.")
        self.barra_confianza.setValue(0)
        self.label_confianza.setText("—")
        self.label_postura.setText("—")
        self.label_explicacion.setText("")
        self.label_hombros.setText("")
        for valor in self.labels_angulos.values():
            valor.setText("—")

    def _on_resultado(self, info):
        if self.sender() is not self.hilo:
            return
        encuadre = info["encuadre"]
        textos = {"completo": ("Cuerpo completo", "ok"), "parcial": ("Detección parcial", "neutra"),
                  "sin_persona": ("Sin persona", "neutra")}
        self.pastilla_encuadre.establecer(*textos[encuadre.estado])
        self.label_encuadre.setText(encuadre.mensaje)
        confianza = int(round(info["confianza"] * 100))
        self.barra_confianza.setValue(confianza)
        self.label_confianza.setText(f"{confianza} %" if encuadre.estado != "sin_persona" else "—")

        if encuadre.estado == "sin_persona":
            self.label_postura.setText("—")
            self.label_explicacion.setText("")
        elif info["posturas"]:
            self.label_postura.setText(" · ".join(info["posturas"]))
            self.label_explicacion.setText(info["explicacion"])
        else:
            self.label_postura.setText("Sin clasificar")
            self.label_explicacion.setText(info["explicacion"])

        inclinacion = info["inclinacion_hombros"]
        self.label_hombros.setText(
            f"Inclinación de la línea de hombros: {abs(inclinacion):.0f}°" if inclinacion is not None else "")
        for nombre, valor in info["angulos"].items():
            self.labels_angulos[nombre].setText(f"{valor:.0f}°" if valor is not None else "—")

    # ------------------------------------------------------- Ciclo de vida
    def al_ocultar(self):
        self.detener_camara()
