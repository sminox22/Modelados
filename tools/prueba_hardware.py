"""
Prueba manual del hardware real: cámara y micrófono del equipo.
No guarda imágenes ni audio; solo muestra estadísticas en la consola.

Uso:  python tools/prueba_hardware.py [indice_camara] [segundos_audio]
"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.audio_recorder import GrabadorAudio, listar_microfonos  # noqa: E402
from services.camera import CamaraLocal, brillo_medio  # noqa: E402
from services.voice_service import validar_audio  # noqa: E402
from utils.exceptions import AppException  # noqa: E402


def probar_camara(indice: int, segundos: float = 4.0):
    print(f"\n== Cámara {indice} ==")
    camara = CamaraLocal(indice)
    try:
        inicio = time.time()
        camara.abrir()
        print(f"Abierta en {time.time() - inicio:.2f} s")
        from services.face_service import AnalizadorFacial
        from services.pose_service import ProcesadorCamaraPostura
        rostro = AnalizadorFacial()
        postura = ProcesadorCamaraPostura()
        postura.preparar()
        estados_rostro, estados_postura, brillos, n = Counter(), Counter(), [], 0
        inicio = time.time()
        while time.time() - inicio < segundos:
            frame = camara.leer()
            if frame is None:
                continue
            n += 1
            brillos.append(brillo_medio(frame))
            estados_rostro[rostro.analizar(frame).estado] += 1
            estados_postura[postura.procesar(frame)[1]["encuadre"].estado] += 1
        postura.cerrar()
        print(f"Fotogramas: {n} ({n / segundos:.1f} fps con detección de rostro y postura)")
        print(f"Brillo medio: {sum(brillos) / max(len(brillos), 1):.1f} (0-255)")
        print(f"Rostro: {dict(estados_rostro)}")
        print(f"Postura: {dict(estados_postura)}")
    except AppException as e:
        print(f"Error: {e.message}")
    finally:
        camara.liberar()
        print("Cámara liberada.")


def probar_microfono(segundos: float = 3.0):
    print("\n== Micrófono ==")
    print("Dispositivos de entrada:", listar_microfonos())
    grabador = GrabadorAudio()
    try:
        grabador.iniciar()
        print(f"Grabando {segundos:.0f} s… (hable si desea probar la validación)")
        time.sleep(segundos)
        audio = grabador.detener()
        validacion = validar_audio(audio)
        print(f"Muestras: {len(audio)} ({len(audio) / 16000:.1f} s a 16 kHz)")
        print(f"RMS: {validacion.rms:.4f} · voz detectada: {validacion.duracion_voz:.1f} s · "
              f"SNR: {validacion.snr_db:.1f} dB")
        print(f"Validación: {'válida' if validacion.valida else 'no válida'} — {validacion.mensaje}")
    except AppException as e:
        print(f"Error: {e.message}")
    finally:
        if grabador.grabando:
            grabador.detener()
        print("Micrófono liberado.")


if __name__ == "__main__":
    probar_camara(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    probar_microfono(float(sys.argv[2]) if len(sys.argv) > 2 else 3.0)
