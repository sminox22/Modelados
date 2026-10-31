"""
Controlador de autenticación. Contiene la lógica de negocio de registro
e inicio de sesión, dejando las pantallas (interfaces/) libres de lógica.
"""
import hashlib
import hmac
import os
import sqlite3

from database.db_manager import DBManager
from utils.exceptions import (
    CamposVaciosError,
    UsuarioDuplicadoError,
    UsuarioNoExisteError,
    ContrasenaIncorrectaError,
)
from utils.validators import validar_campos_no_vacios, validar_usuario, validar_contrasena


class AuthController:
    def __init__(self):
        self.db = DBManager()

    ITERACIONES = 310_000

    @staticmethod
    def _hash(texto: str) -> str:
        """Hash SHA-256 sin sal usado por versiones anteriores (solo para migrar)."""
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    @classmethod
    def _hash_seguro(cls, contrasena: str, sal: bytes = None) -> str:
        """PBKDF2-HMAC-SHA256 con sal aleatoria. Formato: pbkdf2_sha256$iteraciones$sal$hash"""
        sal = sal or os.urandom(16)
        derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, cls.ITERACIONES)
        return f"pbkdf2_sha256${cls.ITERACIONES}${sal.hex()}${derivado.hex()}"

    @classmethod
    def _verificar(cls, contrasena: str, almacenado: str) -> bool:
        if almacenado.startswith("pbkdf2_sha256$"):
            _, iteraciones, sal, esperado = almacenado.split("$")
            derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), int(iteraciones))
            return hmac.compare_digest(derivado.hex(), esperado)
        return hmac.compare_digest(cls._hash(contrasena), almacenado)

    def registrar(self, nombre: str, usuario: str, contrasena: str):
        validar_campos_no_vacios(nombre=nombre, usuario=usuario, contrasena=contrasena)

        if not validar_usuario(usuario):
            raise CamposVaciosError(
                "El usuario debe tener entre 3 y 20 caracteres (letras, números o '_')."
            )
        if not validar_contrasena(contrasena):
            raise CamposVaciosError("La contraseña debe tener al menos 4 caracteres.")

        try:
            self.db.crear_usuario(nombre.strip(), usuario.strip(), self._hash_seguro(contrasena))
        except sqlite3.IntegrityError:
            raise UsuarioDuplicadoError()
        return True

    def datos_usuario(self, usuario: str) -> dict:
        """Datos públicos de una cuenta (para el inicio de sesión biométrico)."""
        fila = self.db.obtener_usuario(usuario.strip())
        if fila is None:
            raise UsuarioNoExisteError()
        _id, nombre, usuario_db, _ = fila
        return {"id": _id, "nombre": nombre, "usuario": usuario_db}

    def iniciar_sesion(self, usuario: str, contrasena: str):
        validar_campos_no_vacios(usuario=usuario, contrasena=contrasena)

        fila = self.db.obtener_usuario(usuario.strip())
        if fila is None:
            raise UsuarioNoExisteError()

        _id, nombre, usuario_db, contrasena_hash = fila
        if not self._verificar(contrasena, contrasena_hash):
            raise ContrasenaIncorrectaError()

        # Migra automáticamente las contraseñas guardadas con el formato antiguo
        if not contrasena_hash.startswith("pbkdf2_sha256$"):
            self.db.actualizar_contrasena(usuario_db, self._hash_seguro(contrasena))

        return {"id": _id, "nombre": nombre, "usuario": usuario_db}
