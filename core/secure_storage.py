"""
Cifrado de los datos biométricos almacenados.

- Las plantillas (vectores numéricos del rostro o la voz) se cifran con
  Fernet (AES-128-CBC + HMAC-SHA256, paquete 'cryptography').
- La clave de Fernet nunca se guarda en claro: se protege con DPAPI de
  Windows (CryptProtectData), que la vincula a la cuenta de Windows del
  usuario. Otra cuenta, u otro equipo, no puede descifrarla.

Si DPAPI no está disponible (otro sistema operativo o fallo del sistema),
se lanza AlmacenamientoInseguroError y la aplicación deshabilita el
registro biométrico, en lugar de guardar los datos sin protección.
"""
import ctypes
import os
import sys

from cryptography.fernet import Fernet, InvalidToken

from utils.exceptions import AlmacenamientoInseguroError, BiometriaError
from utils.resources import data_dir

_ENTROPIA = b"SoftwareMatematicoIA/biometria/v1"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(datos: bytes):
    buffer = ctypes.create_string_buffer(datos, len(datos))
    return _DATA_BLOB(len(datos), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def dpapi_disponible() -> bool:
    return sys.platform == "win32"


def _dpapi(datos: bytes, proteger: bool) -> bytes:
    if not dpapi_disponible():
        raise AlmacenamientoInseguroError()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    entrada, _buf_entrada = _blob(datos)
    entropia, _buf_entropia = _blob(_ENTROPIA)
    salida = _DATA_BLOB()
    if proteger:
        ok = crypt32.CryptProtectData(
            ctypes.byref(entrada), "SoftwareMatematicoIA", ctypes.byref(entropia),
            None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(salida))
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(entrada), None, ctypes.byref(entropia),
            None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(salida))
    if not ok:
        raise AlmacenamientoInseguroError(
            "Windows no pudo proteger o recuperar la clave de cifrado biométrico "
            f"(código {ctypes.GetLastError()}).")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        kernel32.LocalFree(salida.pbData)


class CifradorBiometrico:
    """Cifra y descifra plantillas biométricas con una clave protegida por DPAPI."""

    def __init__(self, ruta_llave: str = None):
        self.ruta_llave = ruta_llave or os.path.join(data_dir(), "biometria.key")
        self._fernet = Fernet(self._obtener_o_crear_llave())

    def _obtener_o_crear_llave(self) -> bytes:
        if os.path.exists(self.ruta_llave):
            with open(self.ruta_llave, "rb") as f:
                return _dpapi(f.read(), proteger=False)
        llave = Fernet.generate_key()
        protegida = _dpapi(llave, proteger=True)
        with open(self.ruta_llave, "wb") as f:
            f.write(protegida)
        return llave

    def cifrar(self, datos: bytes) -> bytes:
        return self._fernet.encrypt(datos)

    def descifrar(self, token: bytes) -> bytes:
        try:
            return self._fernet.decrypt(token)
        except InvalidToken:
            raise BiometriaError(
                "El registro biométrico guardado no se pudo descifrar (la clave cambió "
                "o los datos están dañados). Elimínelo y vuelva a registrarse.")
