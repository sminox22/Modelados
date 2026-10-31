"""Panel de inicio: resumen de secciones y estado de los módulos."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from interfaces.styles import paleta
from interfaces.widgets import EncabezadoPagina, Pastilla, Tarjeta, boton, icono, pagina_desplazable

SECCIONES = [
    ("resolver", "Resolver problema", "Calculadora sin conexión, resolución con IA (texto o foto) y graficador de funciones."),
    ("historial", "Historial", "Consulte y filtre los problemas que ha resuelto con la IA."),
    ("rostro", "Reconocimiento facial", "Registre su rostro y verifique si una nueva captura coincide."),
    ("voz", "Verificación de voz", "Registre su voz y compare nuevas muestras con el registro."),
    ("postura", "Posturas corporales", "Visualice puntos del cuerpo, esqueleto y ángulos articulares en vivo."),
    ("ajustes", "Configuración y privacidad", "Tema, dispositivos, modelos instalados y sus datos biométricos."),
]


class HomeScreen(QWidget):
    def __init__(self, contexto, on_navegar):
        super().__init__()
        self.contexto = contexto
        self.on_navegar = on_navegar
        self.pastillas = {}
        self._construir_ui()
        self.al_mostrar()

    def _construir_ui(self):
        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        nombre = self.contexto.usuario.get("nombre", "").split(" ")[0] or self.contexto.nombre_usuario
        layout.addWidget(EncabezadoPagina(f"Hola, {nombre}", "¿Qué desea hacer hoy?"))

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(16)
        rejilla.setVerticalSpacing(16)
        for i, (clave, titulo, descripcion) in enumerate(SECCIONES):
            rejilla.addWidget(self._tarjeta_seccion(clave, titulo, descripcion), i // 3, i % 3)
        for columna in range(3):
            rejilla.setColumnStretch(columna, 1)
        layout.addLayout(rejilla)

        privacidad = Tarjeta("Privacidad")
        texto = QLabel(
            "La cámara y el micrófono solo se activan cuando usted lo solicita. Los datos biométricos se "
            "procesan en este equipo y se guardan cifrados; puede eliminarlos en cualquier momento desde "
            "Configuración y privacidad.")
        texto.setWordWrap(True)
        texto.setObjectName("nota")
        privacidad.cuerpo.addWidget(texto)
        layout.addWidget(privacidad)
        layout.addStretch()

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(pagina_desplazable(contenido))

    def _tarjeta_seccion(self, clave, titulo, descripcion):
        tarjeta = Tarjeta()
        cabecera = QHBoxLayout()
        cabecera.setSpacing(10)
        icono_label = QLabel()
        icono_label.setPixmap(icono(clave, paleta()["acento"], 18).pixmap(22, 22))
        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("seccion")
        cabecera.addWidget(icono_label)
        cabecera.addWidget(etiqueta)
        cabecera.addStretch()
        tarjeta.cuerpo.addLayout(cabecera)
        texto = QLabel(descripcion)
        texto.setWordWrap(True)
        texto.setObjectName("nota")
        texto.setMinimumHeight(36)
        texto.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        tarjeta.cuerpo.addWidget(texto)
        pie = QHBoxLayout()
        pastilla = Pastilla("", "neutra")
        self.pastillas[clave] = pastilla
        pie.addWidget(pastilla)
        pie.addStretch()
        pie.addWidget(boton("Abrir", "secundario", lambda: self.on_navegar(clave)))
        tarjeta.cuerpo.addLayout(pie)
        return tarjeta

    def al_mostrar(self):
        biometria = self.contexto.biometria
        usuario = self.contexto.nombre_usuario

        def estado_biometrico(tipo, modelo_ok):
            if not modelo_ok:
                return "Falta el modelo", "neutra"
            if not biometria.almacenamiento_seguro:
                return "Registro deshabilitado", "neutra"
            return ("Registrado", "ok") if biometria.tiene_registro(usuario, tipo) else ("Sin registro", "neutra")

        estados = {
            "resolver": ("Calculadora sin conexión", "neutra"),
            "historial": ("Local", "neutra"),
            "rostro": estado_biometrico("rostro", biometria.modelos_rostro_disponibles()),
            "voz": estado_biometrico("voz", biometria.modelo_voz_disponible()),
            "postura": ("Modelo disponible", "ok") if biometria.modelo_postura_disponible()
            else ("Falta el modelo", "neutra"),
            "ajustes": (f"Tema {self.contexto.ajustes.tema}", "neutra"),
        }
        for clave, (texto, tipo) in estados.items():
            self.pastillas[clave].establecer(texto, tipo)
