"""Protección de las plantillas biométricas (cifrado, vinculación al usuario y eliminación)."""
import os
import sqlite3
import unittest

import numpy as np

from core.secure_storage import CifradorBiometrico, dpapi_disponible
from storage.biometric_repository import RepositorioBiometrico
from tests.utilidades import EntornoAislado
from utils.exceptions import BiometriaError


@unittest.skipUnless(dpapi_disponible(), "DPAPI solo existe en Windows")
class PruebasAlmacenamiento(EntornoAislado):
    def setUp(self):
        super().setUp()
        self.repo = RepositorioBiometrico()
        self.vector = np.random.default_rng(1).standard_normal(128).astype(np.float32)

    def test_la_clave_no_se_guarda_en_claro(self):
        cifrador = CifradorBiometrico()
        with open(cifrador.ruta_llave, "rb") as f:
            contenido = f.read()
        self.assertNotIn(cifrador._fernet._signing_key, contenido)
        # Una segunda instancia recupera la misma clave mediante DPAPI
        self.assertEqual(CifradorBiometrico().descifrar(cifrador.cifrar(b"hola")), b"hola")

    def test_guardar_obtener_y_eliminar(self):
        self.assertFalse(self.repo.existe("ana", "rostro"))
        self.repo.guardar("ana", "rostro", "modelo-x", self.vector, 5, "2026-01-01 10:00:00")
        plantilla = self.repo.obtener("ana", "rostro")
        np.testing.assert_allclose(plantilla.vector, self.vector)
        self.assertEqual(plantilla.n_muestras, 5)
        self.assertEqual([r.tipo for r in self.repo.listar("ana")], ["rostro"])
        self.assertEqual(self.repo.eliminar("ana", "rostro"), 1)
        self.assertIsNone(self.repo.obtener("ana", "rostro"))

    def test_eliminar_todo(self):
        self.repo.guardar("ana", "rostro", "m", self.vector, 5, "f")
        self.repo.guardar("ana", "voz", "m", self.vector, 3, "f")
        self.repo.guardar("luis", "voz", "m", self.vector, 3, "f")
        self.assertEqual(self.repo.eliminar("ana"), 2)
        self.assertEqual(self.repo.listar("ana"), [])
        self.assertTrue(self.repo.existe("luis", "voz"))

    def test_los_datos_estan_cifrados_en_la_base(self):
        self.repo.guardar("ana", "rostro", "m", self.vector, 5, "f")
        with open(self.repo.db_path, "rb") as f:
            contenido = f.read()
        self.assertNotIn(self.vector.tobytes(), contenido)

    def test_fila_copiada_a_otro_usuario_es_rechazada(self):
        self.repo.guardar("ana", "rostro", "m", self.vector, 5, "f")
        conn = sqlite3.connect(self.repo.db_path)
        conn.execute("UPDATE plantillas_biometricas SET usuario = 'intruso' WHERE usuario = 'ana'")
        conn.commit()
        conn.close()
        with self.assertRaises(BiometriaError):
            self.repo.obtener("intruso", "rostro")

    def test_clave_distinta_no_descifra(self):
        self.repo.guardar("ana", "voz", "m", self.vector, 3, "f")
        otro = RepositorioBiometrico(cifrador=CifradorBiometrico(os.path.join(self.tmp, "otra.key")))
        with self.assertRaises(BiometriaError):
            otro.obtener("ana", "voz")
