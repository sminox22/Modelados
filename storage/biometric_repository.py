"""
Repositorio de plantillas biométricas (rostro y voz) en la base SQLite local.

Solo se guardan representaciones numéricas (vectores) cifradas; nunca
imágenes ni grabaciones originales. Cada plantilla cifrada incluye el
usuario y el tipo, y se comprueban al descifrar para impedir que una fila
copiada a otro usuario sea aceptada.
"""
import base64
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from core.secure_storage import CifradorBiometrico
from database.db_manager import DBManager
from utils.exceptions import BaseDatosError, BiometriaError

TIPOS_VALIDOS = ("rostro", "voz")


@dataclass
class PlantillaBiometrica:
    usuario: str
    tipo: str
    modelo: str
    vector: np.ndarray
    n_muestras: int
    consentimiento_fecha: str
    creado: str


@dataclass
class ResumenPlantilla:
    tipo: str
    modelo: str
    n_muestras: int
    consentimiento_fecha: str
    creado: str


class RepositorioBiometrico:
    def __init__(self, db_path: str = None, cifrador: CifradorBiometrico = None):
        self.db_path = db_path or DBManager().db_path
        # Si DPAPI no está disponible se propaga AlmacenamientoInseguroError
        self.cifrador = cifrador or CifradorBiometrico()
        self._crear_tabla()

    def _conectar(self):
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            raise BaseDatosError(f"No fue posible conectar a la base de datos: {e}")

    def _crear_tabla(self):
        conn = self._conectar()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plantillas_biometricas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    tipo TEXT NOT NULL CHECK (tipo IN ('rostro', 'voz')),
                    modelo TEXT NOT NULL,
                    datos BLOB NOT NULL,
                    n_muestras INTEGER NOT NULL,
                    consentimiento_fecha TEXT NOT NULL,
                    creado TEXT NOT NULL,
                    UNIQUE (usuario, tipo)
                );
            """)
            conn.commit()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error creando la tabla biométrica: {e}")
        finally:
            conn.close()

    def guardar(self, usuario: str, tipo: str, modelo: str, vector: np.ndarray,
                n_muestras: int, consentimiento_fecha: str):
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo biométrico no válido: {tipo}")
        carga = json.dumps({
            "usuario": usuario,
            "tipo": tipo,
            "modelo": modelo,
            "vector": base64.b64encode(np.asarray(vector, dtype=np.float32).tobytes()).decode("ascii"),
        }).encode("utf-8")
        datos = self.cifrador.cifrar(carga)
        conn = self._conectar()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO plantillas_biometricas "
                "(usuario, tipo, modelo, datos, n_muestras, consentimiento_fecha, creado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (usuario, tipo, modelo, datos, int(n_muestras), consentimiento_fecha,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error guardando el registro biométrico: {e}")
        finally:
            conn.close()

    def obtener(self, usuario: str, tipo: str):
        conn = self._conectar()
        try:
            fila = conn.execute(
                "SELECT modelo, datos, n_muestras, consentimiento_fecha, creado "
                "FROM plantillas_biometricas WHERE usuario = ? AND tipo = ?",
                (usuario, tipo),
            ).fetchone()
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error consultando el registro biométrico: {e}")
        finally:
            conn.close()
        if fila is None:
            return None

        modelo, datos, n_muestras, consentimiento_fecha, creado = fila
        carga = json.loads(self.cifrador.descifrar(datos).decode("utf-8"))
        if carga.get("usuario") != usuario or carga.get("tipo") != tipo or carga.get("modelo") != modelo:
            raise BiometriaError("El registro biométrico no corresponde a este usuario. Elimínelo.")
        vector = np.frombuffer(base64.b64decode(carga["vector"]), dtype=np.float32).copy()
        return PlantillaBiometrica(usuario, tipo, modelo, vector, n_muestras, consentimiento_fecha, creado)

    def obtener_todos(self, tipo: str):
        """Plantillas de todos los usuarios para un tipo (para el inicio de sesión biométrico)."""
        conn = self._conectar()
        try:
            usuarios = [f[0] for f in conn.execute(
                "SELECT usuario FROM plantillas_biometricas WHERE tipo = ? ORDER BY usuario", (tipo,)).fetchall()]
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error consultando los registros biométricos: {e}")
        finally:
            conn.close()
        plantillas = []
        for usuario in usuarios:
            try:
                plantillas.append(self.obtener(usuario, tipo))
            except BiometriaError:
                continue        # registro dañado o manipulado: se ignora
        return plantillas

    def existe(self, usuario: str, tipo: str) -> bool:
        conn = self._conectar()
        try:
            return conn.execute(
                "SELECT 1 FROM plantillas_biometricas WHERE usuario = ? AND tipo = ?",
                (usuario, tipo),
            ).fetchone() is not None
        finally:
            conn.close()

    def listar(self, usuario: str):
        conn = self._conectar()
        try:
            filas = conn.execute(
                "SELECT tipo, modelo, n_muestras, consentimiento_fecha, creado "
                "FROM plantillas_biometricas WHERE usuario = ? ORDER BY tipo",
                (usuario,),
            ).fetchall()
        finally:
            conn.close()
        return [ResumenPlantilla(*f) for f in filas]

    def eliminar(self, usuario: str, tipo: str = None) -> int:
        """Elimina un tipo de registro o, si tipo es None, todos los del usuario."""
        conn = self._conectar()
        try:
            if tipo:
                cursor = conn.execute(
                    "DELETE FROM plantillas_biometricas WHERE usuario = ? AND tipo = ?", (usuario, tipo))
            else:
                cursor = conn.execute(
                    "DELETE FROM plantillas_biometricas WHERE usuario = ?", (usuario,))
            conn.commit()
            # Sobrescribe páginas liberadas para no dejar restos del cifrado en el archivo
            conn.execute("VACUUM")
            return cursor.rowcount
        except sqlite3.Error as e:
            raise BaseDatosError(f"Error eliminando el registro biométrico: {e}")
        finally:
            conn.close()
