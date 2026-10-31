"""
Verificación biométrica de voz (identidad del hablante).

Esto NO es reconocimiento de voz: no se transcribe ni se interpreta lo que
la persona dice. El modelo CAM++ (vía sherpa-onnx) convierte la voz en un
vector de 512 valores que describe características del hablante, y se
compara con la plantilla registrada mediante similitud coseno.

Limitaciones: una grabación reproducida de la persona registrada puede ser
aceptada (no hay detección de reproducción/suplantación); el ruido, el
micrófono y el estado de la voz afectan la similitud.
"""
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from core import settings
from services.biometria_comun import (
    ResultadoVerificacion, combinar_muestras, normalizar, verificar_contra_plantilla,
)
from utils.exceptions import BiometriaError, ConsentimientoRequeridoError, ModeloNoDisponibleError

MODELO_ID = "3dspeaker-campplus-zh-en-advanced-16k"
FRECUENCIA = 16000
_VENTANA = int(0.03 * FRECUENCIA)      # 30 ms

RMS_MINIMO = 0.004                      # por debajo, la grabación es casi silencio
SATURACION_MAXIMA = 0.01                # fracción de muestras recortadas
SNR_MINIMO_DB = 10.0


@dataclass
class ValidacionAudio:
    valida: bool
    mensaje: str
    duracion_total: float
    duracion_voz: float
    rms: float
    snr_db: float


def _energias(audio: np.ndarray) -> np.ndarray:
    n = len(audio) // _VENTANA
    if n == 0:
        return np.zeros(0)
    tramas = audio[: n * _VENTANA].reshape(n, _VENTANA)
    return np.sqrt(np.mean(tramas ** 2, axis=1))


def _mascara_voz(energias: np.ndarray) -> np.ndarray:
    """Detector de actividad de voz por energía, relativo al ruido de fondo."""
    if energias.size == 0:
        return np.zeros(0, dtype=bool)
    ruido = float(np.percentile(energias, 10))
    umbral = max(ruido * 3.0, RMS_MINIMO)
    return energias > umbral


def validar_audio(audio: np.ndarray) -> ValidacionAudio:
    audio = np.asarray(audio, dtype=np.float32)
    duracion_total = len(audio) / FRECUENCIA
    if duracion_total < settings.DURACION_MIN_VOZ:
        return ValidacionAudio(False, f"La grabación es muy corta ({duracion_total:.1f} s). Hable al menos "
                               f"{settings.DURACION_MIN_VOZ + 1:.0f} segundos.", duracion_total, 0.0, 0.0, 0.0)
    if not np.any(audio):
        return ValidacionAudio(False, "El micrófono entregó silencio absoluto. Verifique que no esté silenciado "
                               "y que Windows permita el acceso al micrófono.", duracion_total, 0.0, 0.0, 0.0)

    rms = float(np.sqrt(np.mean(audio ** 2)))
    energias = _energias(audio)
    mascara = _mascara_voz(energias)
    duracion_voz = float(mascara.sum() * _VENTANA / FRECUENCIA)
    ruido = float(np.mean(energias[~mascara])) if np.any(~mascara) else 1e-6
    voz = float(np.mean(energias[mascara])) if np.any(mascara) else 0.0
    snr_db = 20 * np.log10(max(voz, 1e-9) / max(ruido, 1e-9))
    saturacion = float(np.mean(np.abs(audio) >= 0.99))

    def resultado(valida, mensaje):
        return ValidacionAudio(valida, mensaje, duracion_total, duracion_voz, rms, float(snr_db))

    if rms < RMS_MINIMO:
        return resultado(False, "El volumen es demasiado bajo. Acérquese al micrófono y hable con normalidad.")
    if saturacion > SATURACION_MAXIMA:
        return resultado(False, "El audio está saturado. Aléjese un poco del micrófono o baje la ganancia.")
    if duracion_voz < settings.DURACION_MIN_VOZ:
        return resultado(False, f"Se detectaron solo {duracion_voz:.1f} s de voz. Hable de forma continua "
                         f"durante al menos {settings.DURACION_MIN_VOZ + 1:.0f} segundos.")
    if snr_db < SNR_MINIMO_DB:
        return resultado(False, "Hay demasiado ruido de fondo respecto a la voz. Busque un lugar más silencioso.")
    return resultado(True, "Muestra de voz válida.")


def recortar_silencios(audio: np.ndarray) -> np.ndarray:
    """Conserva solo las tramas con voz (más un margen) para el modelo."""
    energias = _energias(audio)
    mascara = _mascara_voz(energias)
    if not np.any(mascara):
        return audio
    # Margen de 3 tramas (90 ms) alrededor de cada segmento con voz
    margen = np.convolve(mascara.astype(int), np.ones(7, dtype=int), mode="same") > 0
    tramas = audio[: len(margen) * _VENTANA].reshape(len(margen), _VENTANA)
    return tramas[margen].ravel()


def _ruta_compatible(ruta: str) -> str:
    """
    sherpa-onnx recibe la ruta del modelo como texto y en Windows puede fallar
    con caracteres no ASCII (tildes, ñ). En ese caso se usa una copia en la
    carpeta temporal del sistema.
    """
    if ruta.isascii():
        return ruta
    destino = os.path.join(tempfile.gettempdir(), "software_matematico_ia_modelos", os.path.basename(ruta))
    if destino.isascii():
        if not os.path.exists(destino) or os.path.getsize(destino) != os.path.getsize(ruta):
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copyfile(ruta, destino)
        return destino
    return ruta


class ExtractorVoz:
    def __init__(self):
        try:
            import sherpa_onnx
        except ImportError:
            raise ModeloNoDisponibleError("No está instalado el paquete 'sherpa-onnx'.")
        ruta = settings.ruta_modelo("voz")
        if not settings.modelo_disponible("voz"):
            raise ModeloNoDisponibleError(
                f"Falta el modelo de voz '{settings.MODELOS['voz'].archivo}'. Ejecute "
                "'python tools/descargar_modelos.py' para descargarlo.")
        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=_ruta_compatible(ruta), num_threads=2)
        if not config.validate():
            raise ModeloNoDisponibleError("La configuración del modelo de voz no es válida.")
        self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)

    def extraer(self, audio: np.ndarray) -> np.ndarray:
        stream = self._extractor.create_stream()
        stream.accept_waveform(FRECUENCIA, recortar_silencios(np.asarray(audio, dtype=np.float32)))
        stream.input_finished()
        if not self._extractor.is_ready(stream):
            raise BiometriaError("La muestra es demasiado corta para el modelo de voz.")
        return normalizar(self._extractor.compute(stream))


class ServicioVoz:
    def __init__(self, repositorio, extractor: ExtractorVoz = None):
        self.repositorio = repositorio
        self._extractor = extractor

    @property
    def extractor(self) -> ExtractorVoz:
        # Carga diferida: el modelo solo se lee cuando se necesita
        if self._extractor is None:
            self._extractor = ExtractorVoz()
        return self._extractor

    def tiene_registro(self, usuario: str) -> bool:
        return self.repositorio.existe(usuario, "voz")

    def procesar_muestra(self, audio: np.ndarray) -> np.ndarray:
        """Valida la calidad y devuelve la representación biométrica (puede tardar; usar en un hilo)."""
        validacion = validar_audio(audio)
        if not validacion.valida:
            raise BiometriaError(validacion.mensaje)
        return self.extractor.extraer(audio)

    def registrar(self, usuario: str, vectores, consentimiento: bool):
        if not consentimiento:
            raise ConsentimientoRequeridoError()
        if len(vectores) < settings.MUESTRAS_REGISTRO_VOZ:
            raise BiometriaError(f"Se necesitan {settings.MUESTRAS_REGISTRO_VOZ} muestras de voz válidas.")
        plantilla = combinar_muestras(vectores, settings.UMBRAL_VOZ)
        self.repositorio.guardar(usuario, "voz", MODELO_ID, plantilla, len(vectores),
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def verificar(self, usuario: str, vector) -> ResultadoVerificacion:
        plantilla = self.repositorio.obtener(usuario, "voz")
        if plantilla is None:
            raise BiometriaError("No tiene una voz registrada. Regístrela primero.")
        if plantilla.modelo != MODELO_ID:
            raise BiometriaError("El registro se hizo con otro modelo. Elimínelo y vuelva a registrarse.")
        return verificar_contra_plantilla(plantilla.vector, [vector], settings.UMBRAL_VOZ)

    def eliminar(self, usuario: str) -> bool:
        return self.repositorio.eliminar(usuario, "voz") > 0
