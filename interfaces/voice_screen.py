"""Pantalla de verificación biométrica de voz (identidad del hablante, no transcripción)."""
import math

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from core import settings
from interfaces.permisos import solicitar_permiso
from interfaces.teachable_widgets import PanelClasificacion
from interfaces.widgets import (
    Banner, DialogoConsentimiento, EncabezadoPagina, Pastilla, Tarjeta, boton, confirmar, pagina_desplazable,
)
from interfaces.workers import HiloTarea
from services import teachable_service
from services.audio_recorder import GrabadorAudio, listar_microfonos
from utils.exceptions import AppException

PUNTOS_CONSENTIMIENTO = [
    "Se grabará su voz desde el micrófono mientras la grabación esté activa.",
    f"Con {settings.MUESTRAS_REGISTRO_VOZ} muestras se calcula una <b>representación numérica</b> (512 valores) "
    "de características de su voz. <b>No se guardan las grabaciones</b> ni se transcribe lo que dice.",
    "La representación se guarda <b>cifrada</b> en este computador, protegida con su cuenta de Windows, "
    "y no se envía a ningún servicio externo.",
    "Se utiliza únicamente para la opción «Verificar mi voz» de esta aplicación.",
    "Puede eliminar el registro en cualquier momento desde esta pantalla o desde Configuración y privacidad.",
    "La comparación puede fallar (ruido, resfriado, otro micrófono) y <b>no detecta grabaciones "
    "reproducidas</b>: no debe usarse como único mecanismo de seguridad.",
]

FRASE_SUGERIDA = ("«Las matemáticas nos ayudan a describir el mundo: medimos, contamos, comparamos "
                  "y resolvemos problemas paso a paso.»")


class VoiceScreen(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        self.grabador = None
        self.modo = None                 # "registro" | "verificacion"
        self.muestras_registro = []
        self.hilo = None
        self._procesando = False
        self._consentimiento = False
        self._reloj = QTimer(self)
        self._reloj.setInterval(80)
        self._reloj.timeout.connect(self._actualizar_grabacion)
        # Escucha en vivo con el modelo de audio de Teachable Machine
        self.escucha = None
        self.clasificador_tm = None
        self._reloj_tm = QTimer(self)
        self._reloj_tm.setInterval(500)
        self._reloj_tm.timeout.connect(self._clasificar_escucha)
        self._construir_ui()
        self._actualizar_estado()

    # ------------------------------------------------------------------ UI
    def _construir_ui(self):
        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        layout.addWidget(EncabezadoPagina(
            "Verificación de voz",
            "Compara características de su voz con un registro previo para estimar si la muestra "
            "corresponde a la misma persona. No transcribe ni interpreta las palabras."))

        fila = QHBoxLayout()
        fila.setSpacing(18)

        # ------- Grabación
        tarjeta_grabacion = Tarjeta("Grabación")
        self.label_microfono = QLabel("")
        self.label_microfono.setObjectName("nota")
        self.label_microfono.setWordWrap(True)
        tarjeta_grabacion.cuerpo.addWidget(self.label_microfono)

        fila_estado = QHBoxLayout()
        self.label_estado = QLabel("Micrófono inactivo")
        self.label_estado.setObjectName("metrica")
        self.pastilla_mic = Pastilla("Inactivo", "neutra")
        fila_estado.addWidget(self.label_estado)
        fila_estado.addStretch()
        fila_estado.addWidget(self.pastilla_mic)
        tarjeta_grabacion.cuerpo.addLayout(fila_estado)

        etiqueta_nivel = QLabel("NIVEL DE ENTRADA")
        etiqueta_nivel.setObjectName("etiqueta")
        tarjeta_grabacion.cuerpo.addWidget(etiqueta_nivel)
        self.nivel = QProgressBar()
        self.nivel.setRange(0, 100)
        self.nivel.setTextVisible(False)
        tarjeta_grabacion.cuerpo.addWidget(self.nivel)
        self.label_duracion = QLabel(f"0,0 s de {settings.DURACION_MAX_GRABACION:.0f} s máximo")
        self.label_duracion.setObjectName("nota")
        tarjeta_grabacion.cuerpo.addWidget(self.label_duracion)

        sugerencia = QLabel("Lea en voz alta durante 4 a 8 segundos, por ejemplo:<br><i>" + FRASE_SUGERIDA + "</i>"
                            "<br>Puede decir cualquier frase: el sistema no depende del texto.")
        sugerencia.setTextFormat(Qt.RichText)
        sugerencia.setWordWrap(True)
        sugerencia.setObjectName("nota")
        tarjeta_grabacion.cuerpo.addWidget(sugerencia)

        self.boton_detener = boton("Detener grabación", None, self._detener_grabacion)
        self.boton_detener.setEnabled(False)
        tarjeta_grabacion.cuerpo.addWidget(self.boton_detener)
        tarjeta_grabacion.cuerpo.addStretch()
        fila.addWidget(tarjeta_grabacion, 3)

        # ------- Registro y verificación
        lateral = QVBoxLayout()
        lateral.setContentsMargins(0, 0, 0, 0)
        lateral.setSpacing(14)
        tarjeta_registro = Tarjeta("Registro de voz")
        fila_reg = QHBoxLayout()
        etiqueta = QLabel("Estado")
        etiqueta.setObjectName("nota")
        self.pastilla_registro = Pastilla("", "neutra")
        fila_reg.addWidget(etiqueta)
        fila_reg.addStretch()
        fila_reg.addWidget(self.pastilla_registro)
        tarjeta_registro.cuerpo.addLayout(fila_reg)
        self.label_muestras = QLabel("")
        self.label_muestras.setObjectName("nota")
        tarjeta_registro.cuerpo.addWidget(self.label_muestras)
        self.boton_grabar_registro = boton("Grabar muestra de registro", None, self._grabar_registro)
        self.boton_descartar = boton("Descartar muestras", "secundario", self._descartar_muestras)
        self.boton_eliminar = boton("Eliminar registro de voz", "peligro", self._eliminar)
        for b in (self.boton_grabar_registro, self.boton_descartar, self.boton_eliminar):
            tarjeta_registro.cuerpo.addWidget(b)
        lateral.addWidget(tarjeta_registro)

        tarjeta_verificar = Tarjeta("Verificación")
        texto = QLabel("Grabe una nueva muestra para compararla con su registro.")
        texto.setObjectName("nota")
        texto.setWordWrap(True)
        tarjeta_verificar.cuerpo.addWidget(texto)
        self.boton_verificar = boton("Grabar y verificar mi voz", "secundario", self._grabar_verificacion)
        tarjeta_verificar.cuerpo.addWidget(self.boton_verificar)
        lateral.addWidget(tarjeta_verificar)

        self.banner = Banner()
        lateral.addWidget(self.banner)
        lateral.addStretch()
        contenedor = QWidget()
        contenedor.setLayout(lateral)
        contenedor.setFixedWidth(340)
        fila.addWidget(contenedor)
        layout.addLayout(fila)

        tarjeta_tm = Tarjeta("Mi modelo de audio (Teachable Machine)")
        texto_tm = QLabel(
            "Clasificador entrenado con sus propias clases. Escucha el micrófono y, cada medio segundo, "
            "indica a qué clase se parece el último segundo de audio. No es verificación biométrica: "
            "cualquier voz o sonido se asignará a alguna de las clases entrenadas.")
        texto_tm.setObjectName("nota")
        texto_tm.setWordWrap(True)
        tarjeta_tm.cuerpo.addWidget(texto_tm)
        fila_tm = QHBoxLayout()
        self.boton_escuchar = boton("Iniciar escucha", None, self._iniciar_escucha)
        self.boton_dejar_escuchar = boton("Detener escucha", "secundario", self._detener_escucha)
        self.boton_dejar_escuchar.setEnabled(False)
        self.pastilla_tm = Pastilla("Inactivo", "neutra")
        fila_tm.addWidget(self.boton_escuchar)
        fila_tm.addWidget(self.boton_dejar_escuchar)
        fila_tm.addStretch()
        fila_tm.addWidget(self.pastilla_tm)
        tarjeta_tm.cuerpo.addLayout(fila_tm)
        self.panel_tm = PanelClasificacion()
        tarjeta_tm.cuerpo.addWidget(self.panel_tm)
        if teachable_service.audio_disponible():
            try:
                self.clasificador_tm = teachable_service.ClasificadorAudioTM()
                self.panel_tm.establecer_etiquetas(self.clasificador_tm.etiquetas)
            except AppException as e:
                self.panel_tm.limpiar(e.message)
        else:
            self.panel_tm.limpiar("No hay modelo en models/teachable/audio")
        layout.addWidget(tarjeta_tm)

        alcance = Tarjeta("Alcance y limitaciones")
        texto_alcance = QLabel(
            "• <b>Reconocimiento de voz</b> (qué palabras se dicen) y <b>verificación biométrica</b> (quién habla) "
            "son tareas distintas. Esta pantalla solo hace la segunda.<br>"
            "• Modelo: CAM++ (3D-Speaker) ejecutado localmente con sherpa-onnx. Se acepta la identidad si la "
            f"similitud coseno es ≥ {settings.UMBRAL_VOZ:.2f}; este umbral es una estimación inicial y conviene "
            "calibrarlo con su micrófono.<br>"
            "• Antes de comparar se valida la duración, el volumen, la saturación y el ruido de fondo de la muestra.<br>"
            "• No detecta grabaciones reproducidas ni voces sintéticas; pueden ocurrir falsos rechazos y falsas aceptaciones.")
        texto_alcance.setTextFormat(Qt.RichText)
        texto_alcance.setWordWrap(True)
        texto_alcance.setObjectName("nota")
        alcance.cuerpo.addWidget(texto_alcance)
        layout.addWidget(alcance)
        layout.addStretch()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(pagina_desplazable(contenido))

    # ------------------------------------------------------------- Estado
    def _nombre_microfono(self) -> str:
        indice = self.contexto.ajustes.dispositivo_microfono
        for i, nombre in listar_microfonos():
            if i == indice:
                return nombre
        return "Predeterminado del sistema"

    def _actualizar_estado(self):
        biometria = self.contexto.biometria
        self.label_microfono.setText(f"Micrófono: {self._nombre_microfono()} (cámbielo en Configuración).")
        if not biometria.almacenamiento_seguro:
            self.pastilla_registro.establecer("Deshabilitado", "neutra")
            self.banner.mostrar("advertencia", biometria.error_almacenamiento)
        elif biometria.tiene_registro(self.contexto.nombre_usuario, "voz"):
            self.pastilla_registro.establecer("Registrado", "ok")
        else:
            self.pastilla_registro.establecer("No registrado", "neutra")
        self.label_muestras.setText(
            f"Muestras válidas en este registro: {len(self.muestras_registro)} de {settings.MUESTRAS_REGISTRO_VOZ}")
        self._actualizar_botones()

    def _actualizar_botones(self):
        ocupado = self.grabador is not None or self._procesando or self.escucha is not None
        self.boton_escuchar.setEnabled(self.clasificador_tm is not None and not ocupado)
        self.boton_dejar_escuchar.setEnabled(self.escucha is not None)
        biometria = self.contexto.biometria
        registrado = biometria.tiene_registro(self.contexto.nombre_usuario, "voz")
        self.boton_detener.setEnabled(self.grabador is not None)
        self.boton_grabar_registro.setEnabled(biometria.almacenamiento_seguro and not ocupado)
        self.boton_descartar.setEnabled(bool(self.muestras_registro) and not ocupado)
        self.boton_verificar.setEnabled(registrado and not ocupado)
        self.boton_eliminar.setEnabled(registrado and not ocupado)

    # ------------------------------------------------------------- Grabación
    def _iniciar_grabacion(self, modo):
        if not self.contexto.biometria.modelo_voz_disponible():
            self.banner.mostrar("error", "Falta el modelo de voz. Ejecute 'python tools/descargar_modelos.py'.")
            return
        if not solicitar_permiso(self, self.contexto, "microfono"):
            self.banner.mostrar("info", "No se activó el micrófono porque no se concedió el permiso.")
            return
        grabador = GrabadorAudio(self.contexto.ajustes.dispositivo_microfono, settings.DURACION_MAX_GRABACION)
        try:
            grabador.iniciar()
        except AppException as e:
            self.banner.mostrar("error", e.message)
            return
        self.grabador = grabador
        self.modo = modo
        self.banner.ocultar()
        self.label_estado.setText("Grabando…")
        self.pastilla_mic.establecer("● Micrófono activo", "activa")
        self._reloj.start()
        self._actualizar_botones()

    def _actualizar_grabacion(self):
        if self.grabador is None:
            return
        # Escala logarítmica aproximada: -60 dBFS = 0 %, 0 dBFS = 100 %
        nivel = self.grabador.nivel
        porcentaje = 0 if nivel <= 0 else max(0, min(100, int((20 * math.log10(nivel) + 60) / 60 * 100)))
        self.nivel.setValue(porcentaje)
        self.label_duracion.setText(
            f"{self.grabador.duracion:.1f} s de {settings.DURACION_MAX_GRABACION:.0f} s máximo".replace(".", ","))
        if self.grabador.limite_alcanzado:
            self._detener_grabacion()

    def _detener_grabacion(self):
        if self.grabador is None:
            return
        self._reloj.stop()
        grabador, self.grabador = self.grabador, None
        audio = grabador.detener()
        self.nivel.setValue(0)
        self.pastilla_mic.establecer("Inactivo", "neutra")
        self.label_estado.setText("Analizando muestra…")
        self._procesando = True
        self.hilo = HiloTarea(self.contexto.biometria.voz.procesar_muestra, audio)
        self.hilo.exito.connect(self._on_muestra_procesada)
        self.hilo.error.connect(self._on_error_muestra)
        self.hilo.finished.connect(self._on_hilo_terminado)
        self.hilo.start()
        self._actualizar_botones()

    def _on_hilo_terminado(self):
        self._procesando = False
        if self.grabador is None:
            self.label_estado.setText("Micrófono inactivo")
        self._actualizar_botones()

    def _on_error_muestra(self, mensaje):
        self.banner.mostrar("advertencia", f"Muestra no válida: {mensaje}")

    def _on_muestra_procesada(self, vector):
        usuario = self.contexto.nombre_usuario
        if self.modo == "registro":
            self.muestras_registro.append(vector)
            faltan = settings.MUESTRAS_REGISTRO_VOZ - len(self.muestras_registro)
            if faltan > 0:
                self.banner.mostrar("info", f"Muestra {len(self.muestras_registro)} válida. Grabe {faltan} más "
                                    "para completar el registro.")
            else:
                try:
                    self.contexto.biometria.voz.registrar(usuario, self.muestras_registro, self._consentimiento)
                    self.banner.mostrar("exito", "Voz registrada correctamente. No se guardó ninguna grabación.")
                except AppException as e:
                    self.banner.mostrar("error", e.message)
                self.muestras_registro = []
        else:
            try:
                resultado = self.contexto.biometria.voz.verificar(usuario, vector)
            except AppException as e:
                self.banner.mostrar("error", e.message)
                return
            detalle = f"Similitud: {resultado.similitud:.2f} (umbral {resultado.umbral:.2f})."
            if resultado.coincide:
                self.banner.mostrar("exito", f"{resultado.mensaje} {detalle}")
            else:
                self.banner.mostrar("advertencia", f"{resultado.mensaje} {detalle}\nSi es usted, hable de forma "
                                    "natural en un lugar silencioso e inténtelo de nuevo.")
        self._actualizar_estado()

    # ------------------------------------------------------------ Acciones
    def _grabar_registro(self):
        biometria = self.contexto.biometria
        if not biometria.almacenamiento_seguro:
            self.banner.mostrar("error", biometria.error_almacenamiento)
            return
        if not self._consentimiento:
            if biometria.tiene_registro(self.contexto.nombre_usuario, "voz") and not confirmar(
                    self, "Reemplazar registro", "Ya existe un registro de voz. ¿Desea reemplazarlo por uno nuevo?",
                    "Reemplazar"):
                return
            dialogo = DialogoConsentimiento(self, "Registro biométrico de la voz", PUNTOS_CONSENTIMIENTO)
            if dialogo.exec_() != DialogoConsentimiento.Accepted:
                self.banner.mostrar("info", "Registro cancelado: no se otorgó el consentimiento.")
                return
            self._consentimiento = True
        self._iniciar_grabacion("registro")

    def _descartar_muestras(self):
        self.muestras_registro = []
        self.banner.mostrar("info", "Se descartaron las muestras de registro en curso.")
        self._actualizar_estado()

    def _grabar_verificacion(self):
        self._iniciar_grabacion("verificacion")

    def _eliminar(self):
        if not confirmar(self, "Eliminar registro de voz",
                         "Se eliminará de forma permanente la representación biométrica de su voz. "
                         "¿Desea continuar?", "Eliminar", peligroso=True):
            return
        try:
            self.contexto.biometria.voz.eliminar(self.contexto.nombre_usuario)
            self.banner.mostrar("exito", "Registro de voz eliminado.")
        except AppException as e:
            self.banner.mostrar("error", e.message)
        self._consentimiento = False
        self._actualizar_estado()

    # ------------------------------------------------------- Ciclo de vida
    def al_mostrar(self):
        self._actualizar_estado()

    # ------------------------------------------------------ Teachable Machine
    def _iniciar_escucha(self):
        if self.clasificador_tm is None:
            return
        if not solicitar_permiso(self, self.contexto, "microfono"):
            self.banner.mostrar("info", "No se activó el micrófono porque no se concedió el permiso.")
            return
        escucha = GrabadorAudio(self.contexto.ajustes.dispositivo_microfono, max_segundos=2.0,
                                frecuencia_objetivo=teachable_service.FRECUENCIA_AUDIO_TM, continuo=True)
        try:
            escucha.iniciar()
        except AppException as e:
            self.banner.mostrar("error", e.message)
            return
        self.escucha = escucha
        self.pastilla_tm.establecer("● Escuchando", "activa")
        self.panel_tm.limpiar("Escuchando…")
        self._reloj_tm.start()
        self._actualizar_botones()

    def _clasificar_escucha(self):
        if self.escucha is None or self.escucha.duracion < 1.0:
            return
        try:
            audio = self.escucha.ventana(1.0)
            self.panel_tm.mostrar(self.clasificador_tm.clasificar(audio))
        except AppException as e:
            self._detener_escucha()
            self.banner.mostrar("error", e.message)

    def _detener_escucha(self):
        self._reloj_tm.stop()
        if self.escucha is not None:
            escucha, self.escucha = self.escucha, None
            escucha.detener()
        self.pastilla_tm.establecer("Inactivo", "neutra")
        self._actualizar_botones()

    def al_ocultar(self):
        """Detiene el micrófono al salir de la pantalla (se descarta la grabación en curso)."""
        self._detener_escucha()
        self._reloj.stop()
        if self.grabador is not None:
            grabador, self.grabador = self.grabador, None
            grabador.detener()
            self.pastilla_mic.establecer("Inactivo", "neutra")
            self.label_estado.setText("Micrófono inactivo")
            self.nivel.setValue(0)
        if self.hilo is not None:
            self.hilo.wait(5000)
        self._actualizar_botones()
