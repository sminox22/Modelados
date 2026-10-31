"""Utilidades comunes de las pruebas: entorno aislado (BD, clave y ajustes temporales) y datos opcionales."""
import os
import shutil
import tempfile
import unittest
import wave

import numpy as np

import core.secure_storage as secure_storage
import core.settings as settings
from database.db_manager import DBManager

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATOS = os.path.join(RAIZ, "tests", "datos")


def dato(nombre: str) -> str:
    return os.path.join(DATOS, nombre)


def hay_dato(*nombres) -> bool:
    return all(os.path.exists(dato(n)) for n in nombres)


def hay_modelo(*claves) -> bool:
    return all(settings.modelo_disponible(c) for c in claves)


def leer_wav(ruta: str) -> np.ndarray:
    with wave.open(ruta) as w:
        assert w.getframerate() == 16000 and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


class EntornoAislado(unittest.TestCase):
    """Redirige la base de datos, la clave de cifrado y los ajustes a una carpeta temporal."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="smia_pruebas_")
        DBManager._instance = None
        self.db = DBManager(db_name=os.path.join(self.tmp, "pruebas.db"))
        self._data_dir_original = secure_storage.data_dir
        self._ruta_ajustes_original = settings.ruta_ajustes
        secure_storage.data_dir = lambda: self.tmp
        settings.ruta_ajustes = lambda: os.path.join(self.tmp, "ajustes.json")

    def tearDown(self):
        secure_storage.data_dir = self._data_dir_original
        settings.ruta_ajustes = self._ruta_ajustes_original
        DBManager._instance = None
        shutil.rmtree(self.tmp, ignore_errors=True)
