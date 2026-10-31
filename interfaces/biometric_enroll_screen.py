"""
Pantalla que aparece justo después de crear la cuenta: permite registrar el
rostro y la voz para poder iniciar sesión con ellos. Es opcional.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from core import settings
from interfaces.biometric_dialogs import DialogoRegistroRostro, DialogoRegistroVoz
from interfaces.face_screen import PUNTOS_CONSENTIMIENTO as CONSENTIMIENTO_ROSTRO
from interfaces.voice_screen import PUNTOS_CONSENTIMIENTO as CONSENTIMIENTO_VOZ
from interfaces.widgets import Banner, DialogoConsentimiento, Pastilla, Tarjeta, boton

TEXTO_USO_ACCESO = "Además, se usará para iniciar sesión en esta aplicación sin escribir la contraseña."


class BiometricEnrollScreen(QWidget):
    def __init__(self, usuario, ajustes, permisos, biometria, on_continuar):
        super().__init__()
        self.usuario = usuario
        self.ajustes = ajustes
        self.permisos = permisos
        self.biometria = biometria
        self.on_continuar = on_continuar
        self._construir_ui()
        self._actualizar()

    def _construir_ui(self):
        externo = QVBoxLayout(self)
        externo.setAlignment(Qt.AlignCenter)
        contenedor = QWidget()
        contenedor.setFixedWidth(760)
        layout = QVBoxLayout(contenedor)
        layout.setSpacing(16)
        externo.addWidget(contenedor, alignment=Qt.AlignCenter)

        titulo = QLabel("Cuenta creada. Configure su acceso biométrico")
        titulo.setObjectName("titulo")
        titulo.setWordWrap(True)
        subtitulo = QLabel(f"@{self.usuario}: registre su rostro y su voz para iniciar sesión sin contraseña. "
                           "Es opcional; siempre podrá entrar con su contraseña.")
        subtitulo.setObjectName("subtitulo")
        subtitulo.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)

        fila = QHBoxLayout()
        fila.setSpacing(16)
        self.tarjeta_rostro, self.pastilla_rostro, self.boton_rostro = self._tarjeta(
            "Rostro",
            f"Se toman {settings.MUESTRAS_REGISTRO_ROSTRO} capturas de su cara. Al iniciar sesión se le reconocerá "
            "y se le pedirá un gesto con la mano, comprobado con detección de postura, para confirmar que es una "
            "persona real y no una fotografía.",
            "Registrar rostro", self._registrar_rostro)
        self.tarjeta_voz, self.pastilla_voz, self.boton_voz = self._tarjeta(
            "Voz",
            f"Se graban {settings.MUESTRAS_REGISTRO_VOZ} muestras de su voz diciendo cualquier frase. Al iniciar "
            "sesión bastará con hablar unos segundos.",
            "Registrar voz", self._registrar_voz)
        fila.addWidget(self.tarjeta_rostro)
        fila.addWidget(self.tarjeta_voz)
        layout.addLayout(fila)

        self.banner = Banner()
        layout.addWidget(self.banner)
        if not self.biometria.almacenamiento_seguro:
            self.banner.mostrar("advertencia", self.biometria.error_almacenamiento)

        nota = QLabel("No se guardan fotos ni grabaciones: solo representaciones numéricas cifradas en este equipo. "
                      "Puede eliminarlas en Configuración y privacidad.")
        nota.setObjectName("nota")
        nota.setWordWrap(True)
        layout.addWidget(nota)

        fila_final = QHBoxLayout()
        fila_final.addStretch()
        self.boton_continuar = boton("Continuar al inicio de sesión", None, self.on_continuar)
        fila_final.addWidget(self.boton_continuar)
        layout.addLayout(fila_final)

    def _tarjeta(self, titulo, texto, texto_boton, accion):
        tarjeta = Tarjeta(titulo)
        pastilla = Pastilla("", "neutra")
        tarjeta.cuerpo.addWidget(pastilla)
        descripcion = QLabel(texto)
        descripcion.setObjectName("nota")
        descripcion.setWordWrap(True)
        tarjeta.cuerpo.addWidget(descripcion)
        tarjeta.cuerpo.addStretch()
        b = boton(texto_boton, "secundario", accion)
        tarjeta.cuerpo.addWidget(b)
        return tarjeta, pastilla, b

    def _actualizar(self):
        b = self.biometria
        for tipo, pastilla, boton_registro, modelo_ok in (
                ("rostro", self.pastilla_rostro, self.boton_rostro, b.modelos_rostro_disponibles()
                 and b.modelo_postura_disponible()),
                ("voz", self.pastilla_voz, self.boton_voz, b.modelo_voz_disponible())):
            registrado = b.tiene_registro(self.usuario, tipo)
            if not modelo_ok:
                pastilla.establecer("Falta el modelo", "neutra")
            elif registrado:
                pastilla.establecer("Registrado", "ok")
            else:
                pastilla.establecer("Sin registrar", "neutra")
            boton_registro.setEnabled(b.almacenamiento_seguro and modelo_ok)
            boton_registro.setText(("Volver a registrar " if registrado else "Registrar ") + tipo)

    def _consentir(self, titulo, puntos) -> bool:
        dialogo = DialogoConsentimiento(self, titulo, puntos + [TEXTO_USO_ACCESO])
        if dialogo.exec_() != DialogoConsentimiento.Accepted:
            self.banner.mostrar("info", "Registro cancelado: no se otorgó el consentimiento.")
            return False
        return True

    def _registrar_rostro(self):
        if not self._consentir("Registro biométrico del rostro", CONSENTIMIENTO_ROSTRO):
            return
        dialogo = DialogoRegistroRostro(self, self.ajustes, self.permisos, self.biometria, self.usuario)
        if dialogo.exec_() == DialogoRegistroRostro.Accepted:
            self.banner.mostrar("exito", "Rostro registrado. Ya puede iniciar sesión con su rostro.")
        self._actualizar()

    def _registrar_voz(self):
        if not self._consentir("Registro biométrico de la voz", CONSENTIMIENTO_VOZ):
            return
        dialogo = DialogoRegistroVoz(self, self.ajustes, self.permisos, self.biometria, self.usuario)
        if dialogo.exec_() == DialogoRegistroVoz.Accepted:
            self.banner.mostrar("exito", "Voz registrada. Ya puede iniciar sesión con su voz.")
        self._actualizar()
