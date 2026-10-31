import hashlib

from controllers.auth_controller import AuthController
from tests.utilidades import EntornoAislado
from utils.exceptions import ContrasenaIncorrectaError, UsuarioDuplicadoError, UsuarioNoExisteError


class PruebasAutenticacion(EntornoAislado):
    def test_registro_e_inicio_de_sesion(self):
        auth = AuthController()
        auth.registrar("Ana Pérez", "ana", "secreto1")
        datos = auth.iniciar_sesion("ana", "secreto1")
        self.assertEqual(datos["usuario"], "ana")
        guardado = self.db.obtener_usuario("ana")[3]
        self.assertTrue(guardado.startswith("pbkdf2_sha256$"))
        self.assertNotIn("secreto1", guardado)

    def test_errores(self):
        auth = AuthController()
        auth.registrar("Ana", "ana", "secreto1")
        with self.assertRaises(UsuarioDuplicadoError):
            auth.registrar("Otra", "ana", "secreto2")
        with self.assertRaises(ContrasenaIncorrectaError):
            auth.iniciar_sesion("ana", "otra")
        with self.assertRaises(UsuarioNoExisteError):
            auth.iniciar_sesion("nadie", "x")

    def test_migra_hash_antiguo(self):
        # Usuario creado con la versión anterior (SHA-256 sin sal)
        self.db.crear_usuario("Luis", "luis", hashlib.sha256(b"clave123").hexdigest())
        AuthController().iniciar_sesion("luis", "clave123")
        self.assertTrue(self.db.obtener_usuario("luis")[3].startswith("pbkdf2_sha256$"))
        AuthController().iniciar_sesion("luis", "clave123")
