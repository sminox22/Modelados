"""
Funciones de validación reutilizables para toda la aplicación.
"""
import re
from utils.exceptions import CamposVaciosError, ProblemaVacioError


def validar_campos_no_vacios(**campos):
    """
    Recibe pares nombre=valor y lanza CamposVaciosError si alguno está vacío.
    Ejemplo: validar_campos_no_vacios(usuario=usuario, contrasena=contrasena)
    """
    for nombre, valor in campos.items():
        if valor is None or str(valor).strip() == "":
            raise CamposVaciosError(f"El campo '{nombre}' no puede estar vacío.")
    return True


def validar_usuario(usuario: str) -> bool:
    """El usuario debe tener entre 3 y 20 caracteres alfanuméricos (y '_')."""
    patron = r"^[A-Za-z0-9_]{3,20}$"
    return re.match(patron, usuario.strip()) is not None


def validar_contrasena(contrasena: str) -> bool:
    """La contraseña debe tener al menos 4 caracteres."""
    return len(contrasena.strip()) >= 4


def validar_problema(problema: str):
    if problema is None or problema.strip() == "":
        raise ProblemaVacioError()
    return True


def hay_conexion_internet(timeout: float = 3.0) -> bool:
    """Verifica de forma sencilla si hay conexión a Internet."""
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False
