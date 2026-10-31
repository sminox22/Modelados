"""
Gestor central de la base de datos SQLite.
Crea automáticamente el archivo .db y las tablas si no existen, y expone
métodos simples para que los controladores no manipulen SQL directamente.
"""
import os
import sqlite3
from datetime import datetime

from utils.exceptions import BaseDatosError
from utils.resources import data_dir


class DBManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Patrón Singleton: una sola conexión/gestor para toda la app
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_name: str = "software_matematico_ia.db"):
        if getattr(self, "_inicializado", False):
            return
        self.db_path = os.path.join(data_dir(), db_name)
        self._inicializado = True
        self._crear_tablas()

    def _conectar(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        except sqlite3.Error as e:
            raise BaseDatosError(f"No fue posible conectar a la base de datos: {e}")

    def _crear_tablas(self):
        try:
            conn = self._conectar()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    usuario TEXT NOT NULL UNIQUE,
                    contrasena TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    problema TEXT NOT NULL,
                    respuesta TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    FOREIGN KEY (usuario) REFERENCES usuarios (usuario)
                );
            """)
            conn.commit()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error creando las tablas: {e}")
        finally:
            conn.close()

    # ---------- USUARIOS ----------
    def crear_usuario(self, nombre: str, usuario: str, contrasena_hash: str):
        try:
            conn = self._conectar()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (nombre, usuario, contrasena) VALUES (?, ?, ?)",
                (nombre, usuario, contrasena_hash),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise  # el controlador decide el mensaje (usuario duplicado)
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error registrando el usuario: {e}")
        finally:
            conn.close()

    def obtener_usuario(self, usuario: str):
        try:
            conn = self._conectar()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, usuario, contrasena FROM usuarios WHERE usuario = ?",
                (usuario,),
            )
            fila = cursor.fetchone()
            return fila
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error consultando el usuario: {e}")
        finally:
            conn.close()

    def actualizar_contrasena(self, usuario: str, contrasena_hash: str):
        try:
            conn = self._conectar()
            conn.execute("UPDATE usuarios SET contrasena = ? WHERE usuario = ?", (contrasena_hash, usuario))
            conn.commit()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error actualizando la contraseña: {e}")
        finally:
            conn.close()

    # ---------- HISTORIAL ----------
    def guardar_historial(self, usuario: str, problema: str, respuesta: str):
        try:
            ahora = datetime.now()
            conn = self._conectar()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO historial (usuario, problema, respuesta, fecha, hora) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    usuario,
                    problema,
                    respuesta,
                    ahora.strftime("%Y-%m-%d"),
                    ahora.strftime("%H:%M:%S"),
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error guardando en el historial: {e}")
        finally:
            conn.close()

    def obtener_historial(self, usuario: str, filtro_texto: str = None):
        try:
            conn = self._conectar()
            cursor = conn.cursor()
            if filtro_texto:
                cursor.execute(
                    "SELECT problema, respuesta, fecha, hora FROM historial "
                    "WHERE usuario = ? AND problema LIKE ? ORDER BY id DESC",
                    (usuario, f"%{filtro_texto}%"),
                )
            else:
                cursor.execute(
                    "SELECT problema, respuesta, fecha, hora FROM historial "
                    "WHERE usuario = ? ORDER BY id DESC",
                    (usuario,),
                )
            return cursor.fetchall()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error consultando el historial: {e}")
        finally:
            conn.close()
