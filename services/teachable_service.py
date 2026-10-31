"""
Modelos personalizados entrenados en Teachable Machine (teachablemachine.withgoogle.com).

Son CLASIFICADORES: devuelven la clase más parecida entre las que se usaron al
entrenar (p. ej., "kevin", "fondo"). No son verificación biométrica: cualquier
persona o sonido se asigna a alguna de esas clases, aunque no haya sido entrenada.

- Imagen: exportación "Tensorflow > Keras" (keras_model.h5 + labels.txt),
  convertida una vez a ONNX (tools/convertir_teachable_imagen.py) y ejecutada
  con OpenCV DNN, sin instalar TensorFlow en la aplicación.
- Audio: exportación "Tensorflow.js" (model.json + weights.bin + metadata.json).
  La red se ejecuta con numpy y se replica el espectrograma que genera el
  navegador (Web Audio, FFT de 1024 muestras a 44,1 kHz, 43 tramas x 232 bandas).
"""
import json
import os

import cv2
import numpy as np

from utils.exceptions import ModeloNoDisponibleError
from utils.resources import resource_path

FRECUENCIA_AUDIO_TM = 44100
FFT_TM = 1024
TRAMAS_TM = 43
BANDAS_TM = 232
TAMANO_IMAGEN_TM = 224


def carpeta_teachable(tipo: str) -> str:
    """Carpeta models/teachable/<tipo> (junto al .exe si existe, si no la del proyecto)."""
    import sys
    if getattr(sys, "frozen", False):
        junto_al_exe = os.path.join(os.path.dirname(sys.executable), "models", "teachable", tipo)
        if os.path.isdir(junto_al_exe):
            return junto_al_exe
    return resource_path(os.path.join("models", "teachable", tipo))


def imagen_disponible() -> bool:
    carpeta = carpeta_teachable("imagen")
    return all(os.path.isfile(os.path.join(carpeta, f)) for f in ("model.onnx", "labels.txt"))


def audio_disponible() -> bool:
    carpeta = carpeta_teachable("audio")
    return all(os.path.isfile(os.path.join(carpeta, f)) for f in ("model.json", "weights.bin", "metadata.json"))


def leer_etiquetas_txt(ruta: str) -> list:
    """labels.txt de Teachable Machine: una línea por clase con el formato '0 nombre'."""
    etiquetas = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            partes = linea.split(" ", 1)
            etiquetas.append(partes[1].strip() if len(partes) == 2 and partes[0].isdigit() else linea)
    return etiquetas


def ordenar(etiquetas, probabilidades):
    """[(etiqueta, probabilidad)] de mayor a menor."""
    return sorted(zip(etiquetas, (float(p) for p in probabilidades)), key=lambda par: par[1], reverse=True)


# ---------------------------------------------------------------------------
# Imagen
# ---------------------------------------------------------------------------
class ClasificadorImagenTM:
    def __init__(self, carpeta: str = None):
        carpeta = carpeta or carpeta_teachable("imagen")
        ruta_modelo = os.path.join(carpeta, "model.onnx")
        ruta_etiquetas = os.path.join(carpeta, "labels.txt")
        if not os.path.isfile(ruta_modelo):
            raise ModeloNoDisponibleError(
                "Falta models/teachable/imagen/model.onnx. Convierta el keras_model.h5 de Teachable "
                "Machine con 'python tools/convertir_teachable_imagen.py' (ver README).")
        if not os.path.isfile(ruta_etiquetas):
            raise ModeloNoDisponibleError("Falta models/teachable/imagen/labels.txt de Teachable Machine.")
        with open(ruta_modelo, "rb") as f:
            self._red = cv2.dnn.readNetFromONNX(np.frombuffer(f.read(), dtype=np.uint8))
        self.etiquetas = leer_etiquetas_txt(ruta_etiquetas)

    @staticmethod
    def preprocesar(frame_bgr: np.ndarray) -> np.ndarray:
        """
        Igual que la cámara de Teachable Machine: imagen en espejo, recorte
        cuadrado central, 224x224, RGB y valores en [-1, 1]. Devuelve NCHW.
        """
        frame = cv2.flip(frame_bgr, 1)
        alto, ancho = frame.shape[:2]
        lado = min(alto, ancho)
        y0, x0 = (alto - lado) // 2, (ancho - lado) // 2
        recorte = cv2.resize(frame[y0:y0 + lado, x0:x0 + lado], (TAMANO_IMAGEN_TM, TAMANO_IMAGEN_TM),
                             interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB).astype(np.float32) / 127.5 - 1.0
        return np.ascontiguousarray(rgb.transpose(2, 0, 1)[np.newaxis])

    def clasificar(self, frame_bgr: np.ndarray):
        self._red.setInput(self.preprocesar(frame_bgr))
        probabilidades = self._red.forward().ravel()
        if len(probabilidades) != len(self.etiquetas):
            raise ModeloNoDisponibleError("labels.txt no coincide con el número de clases del modelo de imagen.")
        return ordenar(self.etiquetas, probabilidades)


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------
def espectrograma_tm(audio_44k: np.ndarray) -> np.ndarray:
    """
    Reproduce el AnalyserNode del navegador que usa Teachable Machine: tramas
    consecutivas de 1024 muestras, ventana Blackman, magnitud |X|/N en dB y
    las primeras 232 bandas (0-10 kHz). Usa el último segundo de audio
    (43 tramas) y lo normaliza (media 0, desviación 1) como speech-commands.
    """
    necesario = TRAMAS_TM * FFT_TM
    audio = np.asarray(audio_44k, dtype=np.float32)
    if len(audio) < necesario:
        audio = np.concatenate([np.zeros(necesario - len(audio), np.float32), audio])
    tramas = audio[-necesario:].reshape(TRAMAS_TM, FFT_TM)
    ventana = np.blackman(FFT_TM).astype(np.float32)
    magnitud = np.abs(np.fft.rfft(tramas * ventana, axis=1))[:, :BANDAS_TM] / FFT_TM
    decibeles = 20.0 * np.log10(np.maximum(magnitud, 1e-10))
    desviacion = float(decibeles.std())
    return ((decibeles - decibeles.mean()) / (desviacion if desviacion > 0 else 1.0)).astype(np.float32)


def _conv2d_valida(x, kernel, bias):
    """x: (H, W, Cin), kernel: (kh, kw, Cin, Cout) — convolución 'valid' con paso 1 (Keras)."""
    kh, kw = kernel.shape[:2]
    parches = np.lib.stride_tricks.sliding_window_view(x, (kh, kw), axis=(0, 1))   # (H', W', Cin, kh, kw)
    return np.einsum("hwcij,ijco->hwo", parches, kernel, optimize=True) + bias


def _maxpool(x, tamano, pasos):
    ph, pw = tamano
    sh, sw = pasos
    salida_h = (x.shape[0] - ph) // sh + 1
    salida_w = (x.shape[1] - pw) // sw + 1
    ventanas = np.lib.stride_tricks.sliding_window_view(x, (ph, pw), axis=(0, 1))[::sh, ::sw]
    return ventanas[:salida_h, :salida_w].max(axis=(3, 4))


_ACTIVACIONES = {
    None: lambda v: v,
    "linear": lambda v: v,
    "relu": lambda v: np.maximum(v, 0),
    "softmax": lambda v: (lambda e: e / e.sum())(np.exp(v - v.max())),
}


class ClasificadorAudioTM:
    """Ejecuta con numpy el modelo de audio exportado como TensorFlow.js por Teachable Machine."""

    def __init__(self, carpeta: str = None):
        carpeta = carpeta or carpeta_teachable("audio")
        try:
            with open(os.path.join(carpeta, "model.json"), encoding="utf-8") as f:
                modelo = json.load(f)
            with open(os.path.join(carpeta, "metadata.json"), encoding="utf-8") as f:
                metadatos = json.load(f)
            with open(os.path.join(carpeta, "weights.bin"), "rb") as f:
                binario = f.read()
        except OSError:
            raise ModeloNoDisponibleError(
                "Faltan archivos del modelo de audio de Teachable Machine en models/teachable/audio "
                "(model.json, weights.bin y metadata.json).")

        self.etiquetas = [e.strip() for e in metadatos.get("wordLabels", [])]
        self._pesos = self._leer_pesos(modelo["weightsManifest"], binario)
        self._capas = self._aplanar_capas(modelo["modelTopology"]["config"]["layers"])
        entrada = self._capas[0]["config"]["batch_input_shape"]
        if entrada[1:] != [TRAMAS_TM, BANDAS_TM, 1]:
            raise ModeloNoDisponibleError(f"Formato de entrada de audio no soportado: {entrada}.")

    @staticmethod
    def _leer_pesos(manifiesto, binario):
        pesos, desplazamiento = {}, 0
        for grupo in manifiesto:
            for w in grupo["weights"]:
                if w.get("dtype", "float32") != "float32" or "quantization" in w:
                    raise ModeloNoDisponibleError("Solo se admiten pesos float32 sin cuantizar.")
                cantidad = int(np.prod(w["shape"]))
                pesos[w["name"]] = np.frombuffer(binario, np.float32, cantidad, desplazamiento).reshape(w["shape"])
                desplazamiento += cantidad * 4
        return pesos

    @staticmethod
    def _aplanar_capas(capas):
        resultado = []
        for capa in capas:
            if capa["class_name"] == "Sequential":
                internas = capa["config"]["layers"] if isinstance(capa["config"], dict) else capa["config"]
                resultado.extend(ClasificadorAudioTM._aplanar_capas(internas))
            else:
                resultado.append(capa)
        return resultado

    def _peso(self, nombre_capa, tipo):
        return self._pesos[f"{nombre_capa}/{tipo}"]

    def _inferir(self, x):
        for capa in self._capas:
            clase, cfg = capa["class_name"], capa["config"]
            if clase in ("InputLayer", "Dropout"):
                continue
            if clase == "Conv2D":
                if cfg.get("padding") != "valid" or cfg.get("strides") != [1, 1]:
                    raise ModeloNoDisponibleError("Configuración Conv2D no soportada en el modelo de audio.")
                x = _ACTIVACIONES[cfg.get("activation")](
                    _conv2d_valida(x, self._peso(cfg["name"], "kernel"), self._peso(cfg["name"], "bias")))
            elif clase == "MaxPooling2D":
                x = _maxpool(x, cfg["pool_size"], cfg["strides"])
            elif clase == "Flatten":
                x = x.reshape(-1)
            elif clase == "Dense":
                x = _ACTIVACIONES[cfg.get("activation")](
                    x @ self._peso(cfg["name"], "kernel") + self._peso(cfg["name"], "bias"))
            else:
                raise ModeloNoDisponibleError(f"Capa no soportada en el modelo de audio: {clase}.")
        return x

    def clasificar(self, audio_44k: np.ndarray):
        """Clasifica el último segundo de audio (44,1 kHz, mono, float32 en [-1, 1])."""
        entrada = espectrograma_tm(audio_44k)[..., np.newaxis]
        probabilidades = self._inferir(entrada)
        if len(probabilidades) != len(self.etiquetas):
            raise ModeloNoDisponibleError("metadata.json no coincide con el número de clases del modelo de audio.")
        return ordenar(self.etiquetas, probabilidades)
