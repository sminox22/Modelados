"""
Excepciones personalizadas del sistema SoftwareMatematicoIA.
Centralizar las excepciones facilita mostrar mensajes claros al usuario
y controlar el flujo de errores en toda la aplicación.
"""


class AppException(Exception):
    """Excepción base de la aplicación."""
    def __init__(self, message="Ha ocurrido un error en la aplicación."):
        self.message = message
        super().__init__(self.message)


class CamposVaciosError(AppException):
    def __init__(self, message="Debe completar todos los campos obligatorios."):
        super().__init__(message)


class UsuarioDuplicadoError(AppException):
    def __init__(self, message="El nombre de usuario ya se encuentra registrado."):
        super().__init__(message)


class UsuarioNoExisteError(AppException):
    def __init__(self, message="El usuario no existe. Verifique el nombre de usuario."):
        super().__init__(message)


class ContrasenaIncorrectaError(AppException):
    def __init__(self, message="La contraseña ingresada es incorrecta."):
        super().__init__(message)


class ProblemaVacioError(AppException):
    def __init__(self, message="Debe escribir un problema matemático antes de resolver."):
        super().__init__(message)


class ConexionInternetError(AppException):
    def __init__(self, message="No hay conexión a Internet. Verifique su red e intente de nuevo."):
        super().__init__(message)


class ApiError(AppException):
    def __init__(self, message="Ocurrió un error al consultar el servicio de Inteligencia Artificial."):
        super().__init__(message)


class BaseDatosError(AppException):
    def __init__(self, message="Ocurrió un error al acceder a la base de datos."):
        super().__init__(message)


class CalculoError(AppException):
    def __init__(self, message="No fue posible interpretar el resultado del cálculo."):
        super().__init__(message)


# ---------- Biometría, cámara y micrófono ----------
class CamaraNoDisponibleError(AppException):
    def __init__(self, message=(
        "No fue posible acceder a la cámara. Verifique que esté conectada, que "
        "ninguna otra aplicación la esté usando y que el acceso esté permitido en "
        "Configuración de Windows > Privacidad y seguridad > Cámara."
    )):
        super().__init__(message)


class MicrofonoNoDisponibleError(AppException):
    def __init__(self, message=(
        "No fue posible acceder al micrófono. Verifique que esté conectado y que el "
        "acceso esté permitido en Configuración de Windows > Privacidad y seguridad > Micrófono."
    )):
        super().__init__(message)


class ModeloNoDisponibleError(AppException):
    def __init__(self, message=(
        "No se encontró el archivo del modelo. Ejecute 'python tools/descargar_modelos.py' "
        "para descargarlo."
    )):
        super().__init__(message)


class AlmacenamientoInseguroError(AppException):
    def __init__(self, message=(
        "No es posible proteger los datos biométricos en este equipo, por lo que el "
        "registro biométrico está deshabilitado."
    )):
        super().__init__(message)


class BiometriaError(AppException):
    def __init__(self, message="No fue posible procesar la muestra biométrica."):
        super().__init__(message)


class ConsentimientoRequeridoError(AppException):
    def __init__(self, message="Debe aceptar el consentimiento antes de registrar datos biométricos."):
        super().__init__(message)
