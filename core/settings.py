"""
Configuración central de la aplicación: rutas de modelos, umbrales de los
módulos biométricos y preferencias del usuario (tema, cámara, micrófono).

Las preferencias se guardan en un archivo JSON local (database/ajustes.json).
No contiene contraseñas ni claves API: la API key de la IA sigue en config.py.
"""
import json
import os
import sys
from dataclasses import dataclass, asdict, field

from utils.resources import data_dir, resource_path


# ---------------------------------------------------------------------------
# Modelos preentrenados (ver tools/descargar_modelos.py y README)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class InfoModelo:
    clave: str
    archivo: str
    descripcion: str
    licencia: str
    url: str
    sha256: str


MODELOS = {
    "detector_rostro": InfoModelo(
        clave="detector_rostro",
        archivo="face_detection_yunet_2023mar.onnx",
        descripcion="YuNet (OpenCV Zoo) - detección de rostros",
        licencia="MIT",
        url="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "reconocedor_rostro": InfoModelo(
        clave="reconocedor_rostro",
        archivo="face_recognition_sface_2021dec.onnx",
        descripcion="SFace (OpenCV Zoo) - representación biométrica del rostro",
        licencia="Apache 2.0",
        url="https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
    "voz": InfoModelo(
        clave="voz",
        archivo="3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx",
        descripcion="CAM++ zh-en advanced (3D-Speaker) - representación biométrica de la voz",
        licencia="Apache 2.0",
        url="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx",
        sha256="aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2",
    ),
    "postura": InfoModelo(
        clave="postura",
        archivo="pose_landmarker_lite.task",
        descripcion="MediaPipe Pose Landmarker (lite) - 33 puntos corporales",
        licencia="Apache 2.0",
        url="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
        sha256="59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a",
    ),
}


def carpeta_modelos() -> str:
    """
    Carpeta donde se buscan los modelos. Con el .exe se usa la carpeta
    'models/weights' junto al ejecutable (para no inflar el .exe); en
    desarrollo, la del proyecto.
    """
    if getattr(sys, "frozen", False):
        junto_al_exe = os.path.join(os.path.dirname(sys.executable), "models", "weights")
        if os.path.isdir(junto_al_exe):
            return junto_al_exe
    return resource_path(os.path.join("models", "weights"))


def ruta_modelo(clave: str) -> str:
    return os.path.join(carpeta_modelos(), MODELOS[clave].archivo)


def modelo_disponible(clave: str) -> bool:
    return os.path.isfile(ruta_modelo(clave))


# ---------------------------------------------------------------------------
# Umbrales biométricos (similitud coseno entre representaciones)
# ---------------------------------------------------------------------------
# SFace: 0.363 es el umbral publicado por OpenCV para el modelo 2021dec
# (evaluado en LFW). Por encima de él se considera la misma identidad.
UMBRAL_ROSTRO = 0.363
MUESTRAS_REGISTRO_ROSTRO = 5
MUESTRAS_VERIFICACION_ROSTRO = 3

# CAM++ zh-en advanced: 0.50 dio 0 falsas aceptaciones en una prueba con
# muestras públicas (sr-data, 6 hablantes); debe recalibrarse con muestras
# reales del entorno (micrófono, ruido, idioma).
UMBRAL_VOZ = 0.50
MUESTRAS_REGISTRO_VOZ = 3

# Inicio de sesión biométrico: umbrales más exigentes que la verificación,
# porque se busca entre todas las cuentas registradas, y diferencia mínima
# con la segunda cuenta más parecida para evitar confusiones.
UMBRAL_ROSTRO_ACCESO = 0.45
UMBRAL_VOZ_ACCESO = 0.55
MARGEN_IDENTIFICACION = 0.05
MUESTRAS_ACCESO_ROSTRO = 3
DURACION_MIN_VOZ = 2.0    # segundos de voz efectiva (sin silencios)
DURACION_MAX_GRABACION = 15.0


# ---------------------------------------------------------------------------
# Preferencias persistentes
# ---------------------------------------------------------------------------
@dataclass
class Ajustes:
    tema: str = "claro"                 # "claro" | "oscuro"
    indice_camara: int = 0
    dispositivo_microfono: int = -1     # -1 = predeterminado del sistema
    extras: dict = field(default_factory=dict)


def ruta_ajustes() -> str:
    return os.path.join(data_dir(), "ajustes.json")


def cargar_ajustes(ruta: str = None) -> Ajustes:
    ruta = ruta or ruta_ajustes()
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        ajustes = Ajustes()
        for clave, valor in datos.items():
            if hasattr(ajustes, clave):
                setattr(ajustes, clave, valor)
        if ajustes.tema not in ("claro", "oscuro"):
            ajustes.tema = "claro"
        return ajustes
    except (OSError, ValueError, TypeError):
        return Ajustes()


def guardar_ajustes(ajustes: Ajustes, ruta: str = None):
    ruta = ruta or ruta_ajustes()
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(asdict(ajustes), f, ensure_ascii=False, indent=2)
