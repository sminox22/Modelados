"""
Resuelve rutas de recursos (imágenes, íconos, video, base de datos) tanto en
modo desarrollo como cuando la aplicación ya está compilada como .exe con
PyInstaller (donde los archivos van dentro de una carpeta temporal _MEIPASS).
"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a un recurso, funcionando tanto si se ejecuta
    'python main.py' como si se ejecuta el .exe generado con PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # carpeta temporal creada por PyInstaller
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_path, relative_path)


def data_dir() -> str:
    """
    Carpeta donde se guarda la base de datos SQLite en tiempo de ejecución.
    Se usa una carpeta persistente junto al ejecutable (no la temporal de
    PyInstaller) para que el historial no se pierda entre ejecuciones.
    """
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(base_path, "database")
    os.makedirs(path, exist_ok=True)
    return path
