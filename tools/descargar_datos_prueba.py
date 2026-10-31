"""
Descarga datos públicos de prueba (no se incluyen en el repositorio) para
ejecutar las pruebas de los modelos con imágenes y audios reales:

- Imágenes de prueba de MediaPipe (Apache 2.0): retrato, persona y pose.
- Grabaciones de hablantes de csukuangfj/sr-data (Apache 2.0), usadas en
  los ejemplos de identificación de hablantes de sherpa-onnx.

Uso:  python tools/descargar_datos_prueba.py
Sin estos datos, las pruebas que los necesitan se omiten (skip).
"""
import os
import sys
import urllib.request

CARPETA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests", "datos"))

ARCHIVOS = {
    "portrait.jpg": "https://storage.googleapis.com/mediapipe-assets/portrait.jpg",
    "portrait_rotated.jpg": "https://storage.googleapis.com/mediapipe-assets/portrait_rotated.jpg",
    "business-person.png": "https://storage.googleapis.com/mediapipe-assets/business-person.png",
    "pose.jpg": "https://storage.googleapis.com/mediapipe-assets/pose.jpg",
}
_SR = "https://github.com/csukuangfj/sr-data/raw/main/"
for nombre in ("enroll/fangjun-sr-2.wav", "enroll/fangjun-sr-3.wav", "test/fangjun-test-sr-1.wav",
               "enroll/leijun-sr-1.wav", "enroll/leijun-sr-2.wav", "test/leijun-test-sr-1.wav"):
    ARCHIVOS["voz/" + os.path.basename(nombre)] = _SR + nombre


def main():
    errores = 0
    for nombre, url in ARCHIVOS.items():
        destino = os.path.join(CARPETA, nombre)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        if os.path.exists(destino):
            print(f"  [ok] {nombre} (ya existe)")
            continue
        try:
            urllib.request.urlretrieve(url, destino)
            print(f"  [ok] {nombre}")
        except OSError as e:
            errores += 1
            print(f"  [error] {nombre}: {e}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
