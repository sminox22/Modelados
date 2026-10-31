"""
Ventanas de registro y acceso biométrico usadas al crear la cuenta y al
iniciar sesión: rostro (con reto de gesto comprobado por postura) y voz.
"""
import math
from collections import deque

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout

from controllers.auth_controller import AuthController
from core import settings
from interfaces.permisos import solicitar_permiso
from interfaces.widgets import Banner, Pastilla, VistaVideo, boton
from interfaces.workers import HiloCamara, HiloTarea
from services.audio_recorder import GrabadorAudio
from services.biometric_login import GESTOS, ProcesadorAccesoFacial, gesto_aleatorio
from services.face_service import ProcesadorCamaraRostro
from utils.exceptions import AppException

TIEMPO_ACCESO_MS = 30000
TIEMPO_GESTO_MS = 12000
CUADROS_GESTO = 3           # imágenes seguidas con el gesto correcto
FALLOS_IDENTIDAD = 3        # imágenes seguidas en que el rostro deja de coincidir durante el reto


def _encabezado(layout, titulo, subtitulo):
    etiqueta = QLabel(titulo)
    etiqueta.setObjectName("titulo")
    layout.addWidget(etiqueta)
    texto = QLabel(subtitulo)
    texto.setObjectName("subtitulo")
    texto.setWordWrap(True)
    layout.addWidget(texto)


# ---------------------------------------------------------------------------
# Base con cámara
# ---------------------------------------------------------------------------
class _DialogoCamara(QDialog):
    def __init__(self, parent, ajustes, permisos, titulo, subtitulo):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumSize(640, 640)
        self.ajustes = ajustes
        self.permisos = permisos
        self.hilo = None
        self.procesador = None

        self.raiz = QVBoxLayout(self)
        self.raiz.setContentsMargins(24, 20, 24, 20)
        self.raiz.setSpacing(12)
        _encabezado(self.raiz, titulo, subtitulo)
        self.label_instruccion = QLabel("")
        self.label_instruccion.setObjectName("metrica")
        self.label_instruccion.setWordWrap(True)
        self.raiz.addWidget(self.label_instruccion)
        self.video = VistaVideo("Cámara apagada")
        self.raiz.addWidget(self.video, 1)
        self.label_estado = QLabel("")
        self.label_estado.setObjectName("nota")
        self.label_estado.setWordWrap(True)
        self.raiz.addWidget(self.label_estado)
        self.banner = Banner()
        self.raiz.addWidget(self.banner)
        self.fila_botones = QHBoxLayout()
        self.fila_botones.addStretch()
        self.boton_cancelar = boton("Cancelar", "secundario", self.reject)
        self.fila_botones.addWidget(self.boton_cancelar)
        self.raiz.addLayout(self.fila_botones)

    def crear_procesador(self):
        raise NotImplementedError

    def iniciar_camara(self) -> bool:
        if self.hilo is not None:
            return True
        if not solicitar_permiso(self, self.permisos, "camara"):
            self.banner.mostrar("info", "No se activó la cámara porque no se concedió el permiso.")
            return False
        self.banner.ocultar()
        self.procesador = self.crear_procesador()
        self.hilo = HiloCamara(self.ajustes.indice_camara, self.procesador)
        self.hilo.camara_lista.connect(self._on_camara_lista)
        self.hilo.fotograma.connect(self._on_fotograma)
        self.hilo.resultado.connect(self._on_resultado_hilo)
        self.hilo.error.connect(self._on_error)
        self.video.limpiar("Iniciando cámara…")
        self.hilo.start()
        return True

    def detener_camara(self):
        if self.hilo is not None:
            hilo, self.hilo = self.hilo, None
            hilo.detener()
        self.procesador = None
        self.video.limpiar()

    def _on_fotograma(self, imagen):
        if self.sender() is self.hilo:
            self.video.mostrar_imagen(imagen)

    def _on_resultado_hilo(self, info):
        if self.sender() is self.hilo:
            self.on_resultado(info)

    def _on_camara_lista(self):
        pass

    def on_resultado(self, info):
        pass

    def _on_error(self, mensaje):
        self.detener_camara()
        self.banner.mostrar("error", mensaje)

    def done(self, resultado):
        self.detener_camara()
        super().done(resultado)

    def closeEvent(self, event):
        self.detener_camara()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Registro de rostro (al crear la cuenta)
# ---------------------------------------------------------------------------
class DialogoRegistroRostro(_DialogoCamara):
    def __init__(self, parent, ajustes, permisos, biometria, usuario):
        super().__init__(parent, ajustes, permisos, "Registrar mi rostro",
                         "Mire de frente a la cámara, con buena luz y sin otras personas en la imagen. "
                         f"Se tomarán {settings.MUESTRAS_REGISTRO_ROSTRO} capturas automáticamente.")
        self.biometria = biometria
        self.usuario = usuario
        self.progreso = QProgressBar()
        self.progreso.setRange(0, settings.MUESTRAS_REGISTRO_ROSTRO)
        self.progreso.setTextVisible(False)
        self.raiz.insertWidget(self.raiz.indexOf(self.label_estado), self.progreso)
        self.boton_capturar = boton("Capturar rostro", None, self._capturar)
        self.boton_capturar.setEnabled(False)
        self.fila_botones.addWidget(self.boton_capturar)
        self.label_instruccion.setText("Preparando la cámara…")
        QTimer.singleShot(0, self._arrancar)

    def _arrancar(self):
        if not self.iniciar_camara():
            self.label_instruccion.setText("Cámara no disponible")

    def crear_procesador(self):
        return ProcesadorCamaraRostro()

    def _on_camara_lista(self):
        self.label_instruccion.setText("Colóquese frente a la cámara y pulse «Capturar rostro»")
        self.boton_capturar.setEnabled(True)

    def _capturar(self):
        if self.procesador is None:
            return
        self.boton_capturar.setEnabled(False)
        self.progreso.setValue(0)
        self.banner.ocultar()
        self.label_instruccion.setText("Capturando… no se mueva")
        self.procesador.solicitar_capturas("registro", settings.MUESTRAS_REGISTRO_ROSTRO)

    def on_resultado(self, info):
        self.label_estado.setText(info.get("mensaje", ""))
        if "progreso" in info:
            self.progreso.setValue(info["progreso"][1])
        if "capturas" in info:
            self._guardar(info["capturas"][1])

    def _guardar(self, vectores):
        try:
            otra = self.biometria.identificar_rostro(vectores)
            if otra is not None and otra.usuario != self.usuario:
                raise AppException(f"Este rostro ya está registrado en otra cuenta (@{otra.usuario}).")
            self.biometria.facial.registrar(self.usuario, vectores, consentimiento=True)
        except AppException as e:
            self.banner.mostrar("error", e.message)
            self.label_instruccion.setText("Inténtelo de nuevo")
            self.boton_capturar.setEnabled(True)
            return
        self.accept()


# ---------------------------------------------------------------------------
# Inicio de sesión con el rostro
# ---------------------------------------------------------------------------
class DialogoAccesoFacial(_DialogoCamara):
    """
    1) Identifica la cuenta comparando el rostro con todas las registradas.
    2) Pide un gesto al azar (mano derecha, izquierda o ambas) y lo comprueba
       con detección de postura, mientras el rostro sigue coincidiendo.
    """

    def __init__(self, parent, ajustes, permisos, biometria, usuario=None):
        super().__init__(parent, ajustes, permisos, "Iniciar sesión con mi rostro",
                         "Mire a la cámara. Cuando se le reconozca, haga el gesto que se le indique "
                         "(sirve para comprobar que hay una persona real y no una fotografía).")
        self.setMinimumSize(640, 700)
        self.biometria = biometria
        self.usuario_filtro = usuario or None
        self.datos_usuario = None
        self._vectores = deque(maxlen=settings.MUESTRAS_ACCESO_ROSTRO)
        self._identificado = None
        self._gesto = None
        self._cuadros_gesto = 0
        self._fallos = 0
        self.pastilla_paso = Pastilla("Paso 1 de 2 · Reconocimiento", "neutra")
        self.raiz.insertWidget(2, self.pastilla_paso)
        self.boton_reintentar = boton("Reintentar", None, self._reiniciar)
        self.boton_reintentar.setVisible(False)
        self.fila_botones.addWidget(self.boton_reintentar)
        self._limite = QTimer(self)
        self._limite.setSingleShot(True)
        self._limite.timeout.connect(lambda: self._fallar("No se completó el inicio de sesión a tiempo."))
        self._limite_gesto = QTimer(self)
        self._limite_gesto.setSingleShot(True)
        self._limite_gesto.timeout.connect(lambda: self._fallar("No se detectó el gesto solicitado a tiempo."))
        QTimer.singleShot(0, self._reiniciar)

    def crear_procesador(self):
        return ProcesadorAccesoFacial()

    def done(self, resultado):
        self._limite.stop()
        self._limite_gesto.stop()
        super().done(resultado)

    def _reiniciar(self):
        self.banner.ocultar()
        self.boton_reintentar.setVisible(False)
        self._vectores.clear()
        self._identificado = None
        self._gesto = None
        self._cuadros_gesto = self._fallos = 0
        self.pastilla_paso.establecer("Paso 1 de 2 · Reconocimiento", "neutra")
        self.label_instruccion.setText("Buscando su rostro…")
        if self.iniciar_camara():
            self._limite.start(TIEMPO_ACCESO_MS)

    def _fallar(self, mensaje):
        self._limite.stop()
        self._limite_gesto.stop()
        self.detener_camara()
        self.label_instruccion.setText("No fue posible iniciar sesión")
        self.banner.mostrar("advertencia", mensaje + " Puede reintentar o entrar con su contraseña.")
        self.boton_reintentar.setVisible(True)

    def _on_error(self, mensaje):
        self._limite.stop()
        self._limite_gesto.stop()
        super()._on_error(mensaje)
        self.boton_reintentar.setVisible(True)

    def on_resultado(self, info):
        if info.get("estado") != "ok":
            self.label_estado.setText(info.get("mensaje", ""))
        else:
            self.label_estado.setText("")
        try:
            if self._identificado is None:
                self._paso_reconocimiento(info)
            else:
                self._paso_gesto(info)
        except AppException as e:
            self._fallar(e.message)

    def _paso_reconocimiento(self, info):
        if "vector" not in info:
            return
        self._vectores.append(info["vector"])
        if len(self._vectores) < self._vectores.maxlen:
            return
        identificacion = self.biometria.identificar_rostro(list(self._vectores), self.usuario_filtro)
        if identificacion is None:
            self.label_instruccion.setText("Rostro no reconocido todavía… mire de frente a la cámara")
            return
        self._identificado = identificacion.usuario
        self._gesto = gesto_aleatorio()
        self.procesador.pedir_gesto(self._gesto)
        self.pastilla_paso.establecer(f"Paso 2 de 2 · Hola, @{identificacion.usuario}", "ok")
        self.label_instruccion.setText(GESTOS[self._gesto])
        self._limite_gesto.start(TIEMPO_GESTO_MS)

    def _paso_gesto(self, info):
        if "vector" in info:
            # El rostro debe seguir siendo el de la cuenta identificada durante el gesto
            coincide = self.biometria.identificar_rostro([info["vector"]], self._identificado)
            self._fallos = 0 if coincide else self._fallos + 1
            if self._fallos >= FALLOS_IDENTIDAD:
                raise AppException("El rostro dejó de coincidir con la cuenta durante el gesto.")
        if info.get("gesto_ok"):
            self._cuadros_gesto += 1
            if self._cuadros_gesto >= CUADROS_GESTO:
                self._limite.stop()
                self._limite_gesto.stop()
                self.datos_usuario = AuthController().datos_usuario(self._identificado)
                self.accept()
        elif "gesto_ok" in info:
            self._cuadros_gesto = 0


# ---------------------------------------------------------------------------
# Voz: base de grabación
# ---------------------------------------------------------------------------
class _DialogoVoz(QDialog):
    def __init__(self, parent, ajustes, permisos, biometria, titulo, subtitulo):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(540)
        self.ajustes = ajustes
        self.permisos = permisos
        self.biometria = biometria
        self.grabador = None
        self.hilo = None
        self._reloj = QTimer(self)
        self._reloj.setInterval(80)
        self._reloj.timeout.connect(self._actualizar)

        self.raiz = QVBoxLayout(self)
        self.raiz.setContentsMargins(24, 20, 24, 20)
        self.raiz.setSpacing(12)
        _encabezado(self.raiz, titulo, subtitulo)
        frase = QLabel("Por ejemplo: <i>«Las matemáticas nos ayudan a describir el mundo: medimos, contamos, "
                       "comparamos y resolvemos problemas paso a paso.»</i>")
        frase.setTextFormat(Qt.RichText)
        frase.setWordWrap(True)
        frase.setObjectName("nota")
        self.raiz.addWidget(frase)
        self.label_instruccion = QLabel("")
        self.label_instruccion.setObjectName("metrica")
        self.label_instruccion.setWordWrap(True)
        self.raiz.addWidget(self.label_instruccion)
        self.nivel = QProgressBar()
        self.nivel.setRange(0, 100)
        self.nivel.setTextVisible(False)
        self.raiz.addWidget(self.nivel)
        self.label_duracion = QLabel("")
        self.label_duracion.setObjectName("nota")
        self.raiz.addWidget(self.label_duracion)
        self.banner = Banner()
        self.raiz.addWidget(self.banner)
        fila = QHBoxLayout()
        fila.addStretch()
        self.boton_cancelar = boton("Cancelar", "secundario", self.reject)
        self.boton_grabar = boton("Grabar", None, self._grabar)
        self.boton_detener = boton("Detener", None, self._detener)
        self.boton_detener.setVisible(False)
        for b in (self.boton_cancelar, self.boton_grabar, self.boton_detener):
            fila.addWidget(b)
        self.raiz.addLayout(fila)

    def _grabar(self):
        if not solicitar_permiso(self, self.permisos, "microfono"):
            self.banner.mostrar("info", "No se activó el micrófono porque no se concedió el permiso.")
            return
        grabador = GrabadorAudio(self.ajustes.dispositivo_microfono, max_segundos=10.0)
        try:
            grabador.iniciar()
        except AppException as e:
            self.banner.mostrar("error", e.message)
            return
        self.grabador = grabador
        self.banner.ocultar()
        self.label_instruccion.setText("Grabando… hable de forma natural")
        self.boton_grabar.setVisible(False)
        self.boton_detener.setVisible(True)
        self._reloj.start()

    def _actualizar(self):
        if self.grabador is None:
            return
        nivel = self.grabador.nivel
        self.nivel.setValue(0 if nivel <= 0 else max(0, min(100, int((20 * math.log10(nivel) + 60) / 60 * 100))))
        self.label_duracion.setText(f"{self.grabador.duracion:.1f} s".replace(".", ","))
        if self.grabador.limite_alcanzado:
            self._detener()

    def _detener(self):
        if self.grabador is None:
            return
        self._reloj.stop()
        grabador, self.grabador = self.grabador, None
        audio = grabador.detener()
        self.nivel.setValue(0)
        self.boton_detener.setVisible(False)
        self.boton_grabar.setVisible(True)
        self.boton_grabar.setEnabled(False)
        self.label_instruccion.setText("Analizando…")
        self.hilo = HiloTarea(self.biometria.voz.procesar_muestra, audio)
        self.hilo.exito.connect(self._on_vector)
        self.hilo.error.connect(self._on_error_muestra)
        self.hilo.finished.connect(lambda: self.boton_grabar.setEnabled(True))
        self.hilo.start()

    def _on_error_muestra(self, mensaje):
        self.label_instruccion.setText("Muestra no válida")
        self.banner.mostrar("advertencia", mensaje)

    def _on_vector(self, vector):
        raise NotImplementedError

    def done(self, resultado):
        self._reloj.stop()
        if self.grabador is not None:
            self.grabador.detener()
            self.grabador = None
        if self.hilo is not None:
            self.hilo.wait(5000)
        super().done(resultado)


class DialogoRegistroVoz(_DialogoVoz):
    def __init__(self, parent, ajustes, permisos, biometria, usuario):
        super().__init__(parent, ajustes, permisos, biometria, "Registrar mi voz",
                         f"Grabe {settings.MUESTRAS_REGISTRO_VOZ} muestras de 4 a 8 segundos cada una, hablando "
                         "de forma natural en un lugar silencioso. Puede decir cualquier frase.")
        self.usuario = usuario
        self.vectores = []
        self._mostrar_progreso()

    def _mostrar_progreso(self):
        self.label_instruccion.setText(
            f"Muestra {len(self.vectores) + 1} de {settings.MUESTRAS_REGISTRO_VOZ}: pulse «Grabar»")

    def _on_vector(self, vector):
        self.vectores.append(vector)
        if len(self.vectores) < settings.MUESTRAS_REGISTRO_VOZ:
            self.banner.mostrar("exito", f"Muestra {len(self.vectores)} válida.")
            self._mostrar_progreso()
            return
        try:
            self.biometria.voz.registrar(self.usuario, self.vectores, consentimiento=True)
        except AppException as e:
            self.vectores = []
            self.banner.mostrar("error", e.message + " Vuelva a grabar las muestras.")
            self._mostrar_progreso()
            return
        self.accept()


class DialogoAccesoVoz(_DialogoVoz):
    def __init__(self, parent, ajustes, permisos, biometria, usuario=None):
        super().__init__(parent, ajustes, permisos, biometria, "Iniciar sesión con mi voz",
                         "Grabe una muestra de 4 a 8 segundos. El sistema buscará la cuenta a la que pertenece "
                         "su voz.")
        self.usuario_filtro = usuario or None
        self.datos_usuario = None
        self.label_instruccion.setText("Pulse «Grabar» y hable")

    def _on_vector(self, vector):
        try:
            identificacion = self.biometria.identificar_voz(vector, self.usuario_filtro)
            if identificacion is None:
                self.label_instruccion.setText("Voz no reconocida")
                self.banner.mostrar("advertencia", "Su voz no coincide con ninguna cuenta registrada. Inténtelo "
                                    "de nuevo en un lugar silencioso o entre con su contraseña.")
                return
            self.datos_usuario = AuthController().datos_usuario(identificacion.usuario)
        except AppException as e:
            self.banner.mostrar("error", e.message)
            return
        self.accept()
