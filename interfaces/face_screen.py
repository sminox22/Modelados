"""
Pantalla de reconocimiento facial: reconocimiento de personas con el modelo
propio de Teachable Machine, y registro/verificación/eliminación del rostro.
"""
from collections import deque

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from core import settings
from interfaces.permisos import solicitar_permiso
from interfaces.teachable_widgets import PanelClasificacion
from interfaces.widgets import (
    Banner, DialogoConsentimiento, EncabezadoPagina, Pastilla, Tarjeta, VistaVideo, boton, confirmar,
    pagina_desplazable,
)
from interfaces.workers import HiloCamara
from services import teachable_service
from services.face_service import ProcesadorCamaraRostro
from utils.exceptions import AppException

PUNTOS_CONSENTIMIENTO = [
    "Se encenderá la cámara y se analizarán varias imágenes de su rostro.",
    "Con ellas se calcula una <b>representación numérica</b> (128 valores) de sus rasgos faciales. "
    "No se guardan fotografías ni video.",
    "La representación se guarda <b>cifrada</b> en este computador, protegida con su cuenta de Windows, "
    "y no se envía a ningún servicio externo.",
    "Se utiliza únicamente para comparar su rostro en la opción «Verificar identidad» de esta aplicación.",
    "Puede eliminar el registro en cualquier momento desde esta pantalla o desde Configuración y privacidad.",
    "La comparación puede fallar (rechazarle a usted o aceptar a una persona parecida) y "
    "<b>no detecta fotografías ni videos</b>: no debe usarse como único mecanismo de seguridad.",
]

TIEMPO_MAXIMO_CAPTURA_MS = 20000
CLASIFICACIONES_PROMEDIADAS = 5          # suaviza el resultado para que no parpadee
CONFIANZA_RECONOCIMIENTO = 0.75         # para empezar a mostrar a una persona
CONFIANZA_MANTENER = 0.65                # para seguir mostrándola (evita parpadeos cerca del umbral)
# Clases del modelo que no corresponden a una persona
CLASES_SIN_PERSONA = {"otros", "otro", "nada", "fondo", "fondo oscuro", "ninguno", "nadie", "vacio", "vacío"}


class FaceScreen(QWidget):
    def __init__(self, contexto):
        super().__init__()
        self.contexto = contexto
        self.hilo = None
        self.procesador = None
        self._solicitud_pendiente = None
        self._ultimo_mensaje_calidad = ""
        self._historial_tm = deque(maxlen=CLASIFICACIONES_PROMEDIADAS)
        self._persona_actual = None
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.timeout.connect(self._captura_agotada)
        self._construir_ui()
        self._actualizar_estado_registro()

    # ------------------------------------------------------------------ UI
    def _construir_ui(self):
        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        layout.addWidget(EncabezadoPagina(
            "Reconocimiento facial",
            "Reconoce a las personas entrenadas en su modelo de Teachable Machine. También permite registrar "
            "su rostro y verificar si una nueva captura coincide. Todo el procesamiento ocurre en este equipo."))

        fila = QHBoxLayout()
        fila.setSpacing(18)

        # Columna de video
        columna_video = QVBoxLayout()
        columna_video.setSpacing(10)
        tarjeta_persona = Tarjeta(margen=14)
        etiqueta_persona = QLabel("PERSONA RECONOCIDA")
        etiqueta_persona.setObjectName("etiqueta")
        self.label_persona = QLabel("Active la cámara para reconocer")
        self.label_persona.setObjectName("titulo")
        self.label_persona_detalle = QLabel("")
        self.label_persona_detalle.setObjectName("nota")
        self.label_persona_detalle.setWordWrap(True)
        tarjeta_persona.cuerpo.setSpacing(4)
        tarjeta_persona.cuerpo.addWidget(etiqueta_persona)
        tarjeta_persona.cuerpo.addWidget(self.label_persona)
        tarjeta_persona.cuerpo.addWidget(self.label_persona_detalle)
        columna_video.addWidget(tarjeta_persona)
        self.video = VistaVideo("Cámara apagada")
        columna_video.addWidget(self.video, 1)
        controles = QHBoxLayout()
        self.boton_activar = boton("Activar cámara", None, self.activar_camara)
        self.boton_detener = boton("Detener cámara", "secundario", self.detener_camara)
        self.boton_detener.setEnabled(False)
        self.pastilla_camara = Pastilla("Cámara apagada", "neutra")
        controles.addWidget(self.boton_activar)
        controles.addWidget(self.boton_detener)
        controles.addStretch()
        controles.addWidget(self.pastilla_camara)
        columna_video.addLayout(controles)
        fila.addLayout(columna_video, 3)

        # Columna lateral
        lateral = QVBoxLayout()
        lateral.setContentsMargins(0, 0, 0, 0)
        lateral.setSpacing(14)

        tarjeta_estado = Tarjeta("Estado")
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(8)
        etiqueta_registro = QLabel("Registro facial")
        etiqueta_registro.setObjectName("nota")
        self.pastilla_registro = Pastilla("", "neutra")
        etiqueta_calidad = QLabel("Captura")
        etiqueta_calidad.setObjectName("nota")
        self.label_calidad = QLabel("—")
        self.label_calidad.setWordWrap(True)
        rejilla.addWidget(etiqueta_registro, 0, 0)
        rejilla.addWidget(self.pastilla_registro, 0, 1, Qt.AlignLeft)
        rejilla.addWidget(etiqueta_calidad, 1, 0, Qt.AlignTop)
        rejilla.addWidget(self.label_calidad, 1, 1)
        rejilla.setColumnStretch(1, 1)
        tarjeta_estado.cuerpo.addLayout(rejilla)
        self.progreso = QProgressBar()
        self.progreso.setTextVisible(False)
        self.progreso.setVisible(False)
        self.label_progreso = QLabel("")
        self.label_progreso.setObjectName("nota")
        self.label_progreso.setVisible(False)
        tarjeta_estado.cuerpo.addWidget(self.label_progreso)
        tarjeta_estado.cuerpo.addWidget(self.progreso)
        lateral.addWidget(tarjeta_estado)

        tarjeta_acciones = Tarjeta("Acciones")
        self.boton_registrar = boton("Registrar rostro", None, self._registrar)
        self.boton_verificar = boton("Verificar identidad", "secundario", self._verificar)
        self.boton_cancelar = boton("Cancelar captura", "secundario", self._cancelar_captura)
        self.boton_cancelar.setVisible(False)
        self.boton_eliminar = boton("Eliminar registro", "peligro", self._eliminar)
        for b in (self.boton_registrar, self.boton_verificar, self.boton_cancelar, self.boton_eliminar):
            tarjeta_acciones.cuerpo.addWidget(b)
        lateral.addWidget(tarjeta_acciones)

        # ---------- Modelo personalizado de Teachable Machine
        tarjeta_tm = Tarjeta("Reconocimiento con mi modelo")
        self.casilla_tm = QCheckBox("Reconocer personas con mi modelo (Teachable Machine)")
        self.casilla_tm.toggled.connect(self._cambiar_teachable)
        tarjeta_tm.cuerpo.addWidget(self.casilla_tm)
        self.panel_tm = PanelClasificacion()
        tarjeta_tm.cuerpo.addWidget(self.panel_tm)
        self.nota_tm = QLabel("")
        self.nota_tm.setObjectName("nota")
        self.nota_tm.setWordWrap(True)
        tarjeta_tm.cuerpo.addWidget(self.nota_tm)
        lateral.addWidget(tarjeta_tm)
        self._preparar_teachable()

        self.banner = Banner()
        lateral.addWidget(self.banner)
        lateral.addStretch()

        contenedor_lateral = QWidget()
        contenedor_lateral.setLayout(lateral)
        contenedor_lateral.setFixedWidth(330)
        fila.addWidget(contenedor_lateral)
        layout.addLayout(fila, 1)

        alcance = Tarjeta("Alcance y limitaciones")
        texto = QLabel(
            "• <b>Detección</b>: indica que hay un rostro en la imagen (recuadro sobre el video).<br>"
            "• <b>Comparación de identidad</b>: estima, con el modelo SFace, si el rostro se parece al registrado "
            f"(similitud coseno ≥ {settings.UMBRAL_ROSTRO}).<br>"
            "• <b>Sin detección de vida</b>: no distingue a una persona real de una fotografía, video o pantalla. "
            "Por eso esta verificación es informativa y no da acceso a la aplicación.<br>"
            "• Pueden ocurrir falsos rechazos (iluminación, ángulo, gafas) y falsas aceptaciones (personas muy parecidas).")
        texto.setWordWrap(True)
        texto.setTextFormat(Qt.RichText)
        texto.setObjectName("nota")
        alcance.cuerpo.addWidget(texto)
        layout.addWidget(alcance)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(pagina_desplazable(contenido))

    # ------------------------------------------------------ Teachable Machine
    def _preparar_teachable(self):
        if not teachable_service.imagen_disponible():
            self.casilla_tm.setEnabled(False)
            self.panel_tm.setVisible(False)
            self.nota_tm.setText("No hay modelo. Coloque model.onnx y labels.txt en models/teachable/imagen "
                                 "(ver README).")
            self.label_persona.setText("Sin modelo de reconocimiento")
            self.label_persona_detalle.setText("Falta el modelo de Teachable Machine en models/teachable/imagen.")
            return
        try:
            etiquetas = teachable_service.leer_etiquetas_txt(
                f"{teachable_service.carpeta_teachable('imagen')}/labels.txt")
        except OSError:
            etiquetas = []
        self.panel_tm.establecer_etiquetas(etiquetas)
        self.casilla_tm.setChecked(True)
        self.nota_tm.setText("Clasificador entrenado con sus propias clases: indica la clase más parecida, "
                             "no verifica identidad. Active la cámara para ver el resultado.")

    def _cambiar_teachable(self, activo):
        if self.procesador is not None:
            self.procesador.clasificar_teachable = activo
        self._historial_tm.clear()
        self._persona_actual = None
        if not activo:
            self.panel_tm.limpiar()
        self._mostrar_persona_inactiva()

    def _mostrar_persona_inactiva(self):
        if not self.casilla_tm.isChecked():
            self.label_persona.setText("Reconocimiento desactivado")
            self.label_persona_detalle.setText("Active «Reconocer personas con mi modelo» en el panel derecho.")
        elif self.hilo is None:
            self.label_persona.setText("Active la cámara para reconocer")
            self.label_persona_detalle.setText("")
        else:
            self.label_persona.setText("Analizando…")
            self.label_persona_detalle.setText("")

    def _mostrar_reconocimiento(self, resultados, estado_rostro):
        """Promedia las últimas clasificaciones y muestra la persona reconocida."""
        self._historial_tm.append(dict(resultados))
        etiquetas = [e for e, _ in resultados]
        promedio = [(e, sum(r.get(e, 0.0) for r in self._historial_tm) / len(self._historial_tm))
                    for e in etiquetas]
        promedio.sort(key=lambda par: par[1], reverse=True)
        self.panel_tm.mostrar(promedio)

        clase, probabilidad = promedio[0]
        porcentaje = f"{probabilidad * 100:.0f} %"
        umbral = CONFIANZA_MANTENER if clase == self._persona_actual else CONFIANZA_RECONOCIMIENTO
        self._persona_actual = clase if probabilidad >= umbral else None
        if probabilidad < umbral:
            self.label_persona.setText("Sin reconocimiento confiable")
            self.label_persona_detalle.setText(
                f"La clase más parecida es «{clase}» ({porcentaje}), por debajo del "
                f"{CONFIANZA_RECONOCIMIENTO * 100:.0f} % requerido. Mire de frente a la cámara con buena luz.")
        elif clase.strip().lower() in CLASES_SIN_PERSONA:
            self.label_persona.setText("Ninguna persona reconocida")
            self.label_persona_detalle.setText(f"El modelo indica «{clase}» ({porcentaje}).")
        else:
            self.label_persona.setText(f"{clase}  ·  {porcentaje}")
            aviso = "" if estado_rostro in (None, "ok") else " Aviso de la cámara: " + self._ultimo_mensaje_calidad
            self.label_persona_detalle.setText(
                "Persona entrenada en su modelo de Teachable Machine. Es una clasificación: no comprueba "
                "que sea una persona real frente a la cámara." + aviso)

    # ------------------------------------------------------------- Estado
    def _actualizar_estado_registro(self):
        biometria = self.contexto.biometria
        if not biometria.almacenamiento_seguro:
            self.pastilla_registro.establecer("Deshabilitado", "neutra")
            self.banner.mostrar("advertencia", biometria.error_almacenamiento)
        elif biometria.tiene_registro(self.contexto.nombre_usuario, "rostro"):
            self.pastilla_registro.establecer("Registrado", "ok")
        else:
            self.pastilla_registro.establecer("No registrado", "neutra")
        self._actualizar_botones()

    def _actualizar_botones(self):
        capturando = self._solicitud_pendiente is not None or self._temporizador.isActive()
        biometria = self.contexto.biometria
        registrado = biometria.tiene_registro(self.contexto.nombre_usuario, "rostro")
        activa = self.hilo is not None
        self.boton_activar.setEnabled(not activa)
        self.boton_detener.setEnabled(activa and not capturando)
        self.boton_registrar.setEnabled(biometria.almacenamiento_seguro and not capturando)
        self.boton_verificar.setEnabled(registrado and not capturando)
        self.boton_eliminar.setEnabled(registrado and not capturando)
        self.boton_cancelar.setVisible(capturando)

    # ------------------------------------------------------------- Cámara
    def activar_camara(self) -> bool:
        if self.hilo is not None:
            return True
        if not self.contexto.biometria.modelos_rostro_disponibles():
            self.banner.mostrar("error", "Faltan los modelos de rostro (YuNet y SFace). Ejecute "
                                "'python tools/descargar_modelos.py'.")
            return False
        if not solicitar_permiso(self, self.contexto, "camara"):
            self.banner.mostrar("info", "No se activó la cámara porque no se concedió el permiso.")
            return False
        self.banner.ocultar()
        self.procesador = ProcesadorCamaraRostro()
        self.procesador.clasificar_teachable = self.casilla_tm.isChecked()
        self.hilo = HiloCamara(self.contexto.ajustes.indice_camara, self.procesador)
        self.hilo.camara_lista.connect(self._on_camara_lista)
        self.hilo.fotograma.connect(self._on_fotograma)
        self.hilo.resultado.connect(self._on_resultado)
        self.hilo.error.connect(self._on_error_camara)
        self.hilo.finished.connect(self._on_hilo_terminado)
        self.pastilla_camara.establecer("Iniciando…", "neutra")
        self.video.limpiar("Iniciando cámara…")
        self.hilo.start()
        self._actualizar_botones()
        return True

    def detener_camara(self):
        self._cancelar_captura(silencioso=True)
        if self.hilo is not None:
            hilo, self.hilo = self.hilo, None
            hilo.detener()
        self.procesador = None
        self.video.limpiar()
        self.pastilla_camara.establecer("Cámara apagada", "neutra")
        self.label_calidad.setText("—")
        self.panel_tm.limpiar()
        self._historial_tm.clear()
        self._persona_actual = None
        self._mostrar_persona_inactiva()
        self._actualizar_botones()

    def _on_fotograma(self, imagen):
        # Ignora fotogramas en cola de un hilo ya detenido
        if self.sender() is self.hilo:
            self.video.mostrar_imagen(imagen)

    def _on_camara_lista(self):
        self.pastilla_camara.establecer("● Cámara activa", "activa")
        self._mostrar_persona_inactiva()
        if self._solicitud_pendiente and self.procesador:
            modo, cantidad = self._solicitud_pendiente
            self.procesador.solicitar_capturas(modo, cantidad)
            self._temporizador.start(TIEMPO_MAXIMO_CAPTURA_MS)

    def _on_error_camara(self, mensaje):
        self.banner.mostrar("error", mensaje)
        self.detener_camara()

    def _on_hilo_terminado(self):
        # Si el hilo terminó por su cuenta (error), se limpia el estado
        if self.sender() is self.hilo:
            self.hilo = None
            self.detener_camara()

    # ------------------------------------------------------------ Captura
    def _iniciar_captura(self, modo, cantidad):
        self._solicitud_pendiente = (modo, cantidad)
        self.progreso.setRange(0, cantidad)
        self.progreso.setValue(0)
        self.progreso.setVisible(True)
        self.label_progreso.setText("Mire de frente a la cámara y permanezca quieto…")
        self.label_progreso.setVisible(True)
        if self.hilo is None:
            if not self.activar_camara():
                self._cancelar_captura(silencioso=True)
                return
        elif self.procesador:
            self.procesador.solicitar_capturas(modo, cantidad)
            self._temporizador.start(TIEMPO_MAXIMO_CAPTURA_MS)
        self._actualizar_botones()

    def _cancelar_captura(self, silencioso=False):
        self._temporizador.stop()
        self._solicitud_pendiente = None
        if self.procesador:
            self.procesador.cancelar_capturas()
        self.progreso.setVisible(False)
        self.label_progreso.setVisible(False)
        if not silencioso:
            self.banner.mostrar("info", "Captura cancelada.")
        self._actualizar_botones()

    def _captura_agotada(self):
        motivo = self._ultimo_mensaje_calidad or "no se obtuvo una imagen válida"
        self._cancelar_captura(silencioso=True)
        self.banner.mostrar("advertencia", f"No se completó la captura a tiempo. Último aviso: {motivo}")

    def _on_resultado(self, info):
        if self.sender() is not self.hilo:
            return
        if "teachable" in info:
            self._mostrar_reconocimiento(info["teachable"], info.get("estado"))
        elif self.casilla_tm.isChecked() and self.procesador and self.procesador.error_teachable:
            self.nota_tm.setText(f"No se pudo cargar el modelo: {self.procesador.error_teachable}")
        mensaje = info.get("mensaje", "")
        self._ultimo_mensaje_calidad = mensaje
        self.label_calidad.setText(mensaje)
        if "progreso" in info:
            _, actual, total = info["progreso"]
            self.progreso.setValue(actual)
            self.label_progreso.setText(f"Capturando muestra {actual} de {total}…")
        if "capturas" in info:
            modo, vectores = info["capturas"]
            self._temporizador.stop()
            self._solicitud_pendiente = None
            self.progreso.setVisible(False)
            self.label_progreso.setVisible(False)
            if modo == "registro":
                self._finalizar_registro(vectores)
            else:
                self._finalizar_verificacion(vectores)
            self._actualizar_botones()

    # ------------------------------------------------------------ Acciones
    def _registrar(self):
        biometria = self.contexto.biometria
        if not biometria.almacenamiento_seguro:
            self.banner.mostrar("error", biometria.error_almacenamiento)
            return
        if biometria.tiene_registro(self.contexto.nombre_usuario, "rostro") and not confirmar(
                self, "Reemplazar registro", "Ya existe un registro facial. ¿Desea reemplazarlo por uno nuevo?",
                "Reemplazar"):
            return
        dialogo = DialogoConsentimiento(self, "Registro biométrico del rostro", PUNTOS_CONSENTIMIENTO)
        if dialogo.exec_() != DialogoConsentimiento.Accepted:
            self.banner.mostrar("info", "Registro cancelado: no se otorgó el consentimiento.")
            return
        self.banner.ocultar()
        self._iniciar_captura("registro", settings.MUESTRAS_REGISTRO_ROSTRO)

    def _finalizar_registro(self, vectores):
        try:
            self.contexto.biometria.facial.registrar(self.contexto.nombre_usuario, vectores, consentimiento=True)
            self.banner.mostrar("exito", f"Rostro registrado correctamente a partir de {len(vectores)} muestras. "
                                "No se guardó ninguna imagen.")
        except AppException as e:
            self.banner.mostrar("error", e.message)
        self._actualizar_estado_registro()

    def _verificar(self):
        self.banner.ocultar()
        self._iniciar_captura("verificacion", settings.MUESTRAS_VERIFICACION_ROSTRO)

    def _finalizar_verificacion(self, vectores):
        try:
            resultado = self.contexto.biometria.facial.verificar(self.contexto.nombre_usuario, vectores)
        except AppException as e:
            self.banner.mostrar("error", e.message)
            return
        detalle = f"Similitud: {resultado.similitud:.2f} (umbral {resultado.umbral:.2f})."
        if resultado.coincide:
            self.banner.mostrar("exito", f"{resultado.mensaje} {detalle}\nRecuerde: esto no prueba que sea una "
                                "persona real frente a la cámara.")
        else:
            self.banner.mostrar("advertencia", f"{resultado.mensaje} {detalle}\nSi es usted, mejore la "
                                "iluminación, mire de frente e inténtelo de nuevo.")

    def _eliminar(self):
        if not confirmar(self, "Eliminar registro facial",
                         "Se eliminará de forma permanente la representación biométrica de su rostro. "
                         "¿Desea continuar?", "Eliminar", peligroso=True):
            return
        try:
            self.contexto.biometria.facial.eliminar(self.contexto.nombre_usuario)
            self.banner.mostrar("exito", "Registro facial eliminado.")
        except AppException as e:
            self.banner.mostrar("error", e.message)
        self._actualizar_estado_registro()

    # ------------------------------------------------------- Ciclo de vida
    def al_mostrar(self):
        self._actualizar_estado_registro()

    def al_ocultar(self):
        self.detener_camara()
