"""
Descarga los modelos preentrenados desde sus fuentes oficiales y verifica
su integridad (SHA-256). Requiere conexión a Internet solo esta vez; luego
la aplicación funciona sin conexión para rostro, voz y posturas.

Uso:  python tools/descargar_modelos.py
"""
import hashlib
import os
import sys
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.settings import MODELOS, carpeta_modelos  # noqa: E402


def sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(info, carpeta: str) -> bool:
    destino = os.path.join(carpeta, info.archivo)
    if os.path.exists(destino) and sha256(destino) == info.sha256:
        print(f"  [ok] {info.archivo} (ya existe)")
        return True
    print(f"  Descargando {info.archivo} …")
    temporal = destino + ".parcial"
    try:
        urllib.request.urlretrieve(info.url, temporal)
    except OSError as e:
        print(f"  [error] No se pudo descargar {info.url}: {e}")
        return False
    obtenido = sha256(temporal)
    if obtenido != info.sha256:
        os.remove(temporal)
        print(f"  [error] El hash de {info.archivo} no coincide (esperado {info.sha256[:12]}…, "
              f"obtenido {obtenido[:12]}…). Se descartó el archivo.")
        return False
    os.replace(temporal, destino)
    print(f"  [ok] {info.archivo}")
    return True


def main():
    carpeta = carpeta_modelos()
    os.makedirs(carpeta, exist_ok=True)
    print(f"Carpeta de modelos: {carpeta}")
    resultados = [descargar(info, carpeta) for info in MODELOS.values()]
    if all(resultados):
        print("Todos los modelos están listos.")
        return 0
    print("Algunos modelos no se pudieron descargar. Revise la conexión e inténtelo de nuevo.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
