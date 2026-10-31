"""
Grabación de audio desde el micrófono con 'sounddevice' (PortAudio).

La captura ocurre en el hilo de audio de PortAudio; la interfaz solo
consulta el nivel y la duración. El audio se mantiene en memoria y nunca
se escribe en disco.
"""
import threading

import numpy as np

from utils.exceptions import MicrofonoNoDisponibleError

try:
    import sounddevice as sd
except (ImportError, OSError):   # OSError: PortAudio no disponible
    sd = None

FRECUENCIA_OBJETIVO = 16000


def listar_microfonos():
    """Devuelve [(indice, nombre)] de los dispositivos de entrada (API predeterminada del sistema)."""
    if sd is None:
        return []
    try:
        api_predeterminada = sd.default.hostapi
        dispositivos = sd.query_devices()
    except Exception:
        return []
    resultado = []
    for indice, d in enumerate(dispositivos):
        if d["max_input_channels"] > 0 and (api_predeterminada < 0 or d["hostapi"] == api_predeterminada):
            resultado.append((indice, d["name"]))
    return resultado


def remuestrear(audio: np.ndarray, origen: int, destino: int) -> np.ndarray:
    """Remuestreo con filtro paso bajo (sinc enventanado) + interpolación lineal."""
    if origen == destino or audio.size == 0:
        return audio.astype(np.float32)
    if destino < origen:
        corte = destino / origen / 2
        n = np.arange(-32, 33)
        filtro = 2 * corte * np.sinc(2 * corte * n) * np.hamming(len(n))
        audio = np.convolve(audio, filtro / filtro.sum(), mode="same")
    duracion = audio.size / origen
    t_origen = np.arange(audio.size) / origen
    t_destino = np.arange(int(duracion * destino)) / destino
    return np.interp(t_destino, t_origen, audio).astype(np.float32)


class GrabadorAudio:
    def __init__(self, dispositivo: int = None, max_segundos: float = 15.0,
                 frecuencia_objetivo: int = FRECUENCIA_OBJETIVO, continuo: bool = False):
        """
        continuo=True: no se detiene al llegar a max_segundos; conserva solo los
        últimos max_segundos (escucha en vivo).
        """
        self.dispositivo = None if dispositivo is None or dispositivo < 0 else dispositivo
        self.max_segundos = max_segundos
        self.frecuencia_objetivo = frecuencia_objetivo
        self.continuo = continuo
        self._bloques = []
        self._muestras = 0
        self._nivel = 0.0
        self._lock = threading.Lock()
        self._stream = None
        self._frecuencia = frecuencia_objetivo
        self.error_estado = None

    @property
    def grabando(self) -> bool:
        return self._stream is not None

    @property
    def nivel(self) -> float:
        return self._nivel

    @property
    def duracion(self) -> float:
        return self._muestras / self._frecuencia

    @property
    def limite_alcanzado(self) -> bool:
        return not self.continuo and self.duracion >= self.max_segundos

    def _elegir_frecuencia(self) -> int:
        try:
            sd.check_input_settings(device=self.dispositivo, channels=1, samplerate=self.frecuencia_objetivo,
                                    dtype="float32")
            return self.frecuencia_objetivo
        except Exception:
            return int(sd.query_devices(self.dispositivo, "input")["default_samplerate"])

    def iniciar(self):
        if sd is None:
            raise MicrofonoNoDisponibleError("No está instalado el soporte de audio (paquete 'sounddevice').")
        try:
            sd.query_devices(self.dispositivo, "input")
        except Exception:
            raise MicrofonoNoDisponibleError("No se encontró ningún micrófono disponible en este equipo.")
        self._bloques, self._muestras, self._nivel = [], 0, 0.0
        self.error_estado = None
        try:
            self._frecuencia = self._elegir_frecuencia()
            self._stream = sd.InputStream(device=self.dispositivo, channels=1, dtype="float32",
                                          samplerate=self._frecuencia, callback=self._callback)
            self._stream.start()
        except Exception as e:
            self._stream = None
            raise MicrofonoNoDisponibleError(f"No fue posible abrir el micrófono: {e}")

    def _callback(self, datos, frames, tiempo, estado):
        if estado:
            self.error_estado = str(estado)
        bloque = datos[:, 0].copy()
        with self._lock:
            if self.continuo:
                self._bloques.append(bloque)
                self._muestras += len(bloque)
                limite = int(self.max_segundos * self._frecuencia)
                while self._bloques and self._muestras - len(self._bloques[0]) >= limite:
                    self._muestras -= len(self._bloques.pop(0))
            elif self._muestras / self._frecuencia < self.max_segundos:
                self._bloques.append(bloque)
                self._muestras += len(bloque)
        self._nivel = float(np.sqrt(np.mean(bloque ** 2))) if len(bloque) else 0.0

    def ventana(self, segundos: float) -> np.ndarray:
        """Últimos 'segundos' de audio sin detener la grabación (a la frecuencia objetivo)."""
        with self._lock:
            audio = np.concatenate(self._bloques) if self._bloques else np.zeros(0, dtype=np.float32)
        audio = audio[-int(segundos * self._frecuencia):]
        return remuestrear(audio, self._frecuencia, self.frecuencia_objetivo)

    def detener(self) -> np.ndarray:
        """Detiene la grabación y devuelve el audio mono (float32) a la frecuencia objetivo."""
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        with self._lock:
            audio = np.concatenate(self._bloques) if self._bloques else np.zeros(0, dtype=np.float32)
            self._bloques = []
        self._nivel = 0.0
        return remuestrear(audio, self._frecuencia, self.frecuencia_objetivo)
