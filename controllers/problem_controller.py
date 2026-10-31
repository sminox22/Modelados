"""
Controlador que orquesta: validar el problema -> consultar la IA ->
guardar en el historial -> devolver el resultado a la interfaz.
"""
import os

from database.db_manager import DBManager
from services.ai_service import AIService
from utils.exceptions import ProblemaVacioError
from utils.validators import validar_problema


class ProblemController:
    def __init__(self):
        self.db = DBManager()

    def resolver(self, usuario: str, problema: str) -> dict:
        validar_problema(problema)
        problema = problema.strip()

        resultado_ia = AIService.resolver_problema(problema)

        self.db.guardar_historial(
            usuario=usuario,
            problema=problema,
            respuesta=f"{resultado_ia['procedimiento']}\nRESULTADO: {resultado_ia['resultado']}",
        )
        return resultado_ia

    def resolver_desde_imagen(self, usuario: str, ruta_imagen: str) -> dict:
        """
        Envía una foto de la operación matemática a la IA, guarda en el
        historial el problema detectado en la imagen junto con el nombre
        del archivo, y devuelve procedimiento + resultado.
        """
        if not ruta_imagen or not os.path.exists(ruta_imagen):
            raise ProblemaVacioError("Debe seleccionar una imagen válida antes de resolver.")

        resultado_ia = AIService.resolver_problema_imagen(ruta_imagen)

        nombre_archivo = os.path.basename(ruta_imagen)
        problema_registrado = (
            f"[Imagen: {nombre_archivo}] {resultado_ia.get('problema_detectado', '')}"
        )

        self.db.guardar_historial(
            usuario=usuario,
            problema=problema_registrado,
            respuesta=f"{resultado_ia['procedimiento']}\nRESULTADO: {resultado_ia['resultado']}",
        )
        return resultado_ia

    def obtener_historial(self, usuario: str, filtro_texto: str = None):
        return self.db.obtener_historial(usuario, filtro_texto)
