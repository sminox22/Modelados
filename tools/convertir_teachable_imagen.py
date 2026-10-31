"""
Convierte el modelo de imagen de Teachable Machine (exportación "Tensorflow >
Keras": keras_model.h5) a ONNX para ejecutarlo con OpenCV, sin TensorFlow.

Solo hace falta al cambiar el modelo. Requiere un entorno APARTE con:
    pip install tensorflow==2.15.1 tf2onnx==1.16.1 onnx==1.16.1

Uso (desde la raíz del proyecto, con ese entorno activado):
    python tools/convertir_teachable_imagen.py [ruta/keras_model.h5]

Por defecto lee models/teachable/imagen/keras_model.h5 y escribe model.onnx
en la misma carpeta (junto a labels.txt).
"""
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CARPETA = os.path.join(RAIZ, "models", "teachable", "imagen")


def main():
    import numpy as np
    import tensorflow as tf
    import tf2onnx

    origen = sys.argv[1] if len(sys.argv) > 1 else os.path.join(CARPETA, "keras_model.h5")
    destino = os.path.join(os.path.dirname(os.path.abspath(origen)), "model.onnx")

    # Los .h5 de Teachable Machine incluyen el argumento 'groups' en DepthwiseConv2D,
    # que algunas versiones de Keras no aceptan al cargar.
    class DepthwiseConv2DCompatible(tf.keras.layers.DepthwiseConv2D):
        def __init__(self, *args, groups=None, **kwargs):
            super().__init__(*args, **kwargs)

    modelo = tf.keras.models.load_model(
        origen, compile=False, custom_objects={"DepthwiseConv2D": DepthwiseConv2DCompatible})
    entrada = tf.TensorSpec((1, 224, 224, 3), tf.float32, name="entrada")
    tf2onnx.convert.from_keras(modelo, input_signature=[entrada], opset=13,
                               inputs_as_nchw=["entrada"], output_path=destino)

    # Comprobación: la salida de Keras y la del ONNX deben coincidir
    muestra = np.random.default_rng(0).uniform(-1, 1, (1, 224, 224, 3)).astype(np.float32)
    referencia = modelo.predict(muestra, verbose=0)
    print(f"Modelo convertido: {destino}")
    print(f"Clases: {referencia.shape[-1]} · salida Keras de referencia: {np.round(referencia.ravel(), 4)}")


if __name__ == "__main__":
    main()
