# Software Matemático IA

Aplicación de escritorio (PyQt5 + SQLite) que permite registrar usuarios,
iniciar sesión y resolver problemas matemáticos con ayuda de una API de
Inteligencia Artificial, guardando un historial de consultas.

Desde la versión 2.0 incluye además tres módulos de visión por computador y
audio que funcionan **localmente, sin Internet**: reconocimiento facial,
verificación biométrica de voz y detección de posturas corporales (ver
secciones 4 a 6).

## 1. Instalación (modo desarrollo)

Requisitos: Windows 10/11 de 64 bits y **Python 3.10** (probado con 3.10.11).

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python tools/descargar_modelos.py
```

El último comando descarga una sola vez (~74 MB, requiere Internet) los
modelos preentrenados en `models/weights/` y verifica su integridad (SHA-256).
Sin ellos la aplicación funciona, pero los módulos de rostro, voz y posturas
muestran un aviso indicando qué modelo falta.

## 2. Configurar la API de Inteligencia Artificial (OBLIGATORIO)

**Opción recomendada (gratis, ya configurada por defecto): Groq**

1. Ve a https://console.groq.com/keys e inicia sesión (con Google, GitHub o correo).
2. Genera una API key gratuita (no pide tarjeta de crédito).
3. Copia `config.example.py` como `config.py` y pega la key.
4. Listo — el proyecto ya usa `PROVEEDOR = "groq"` y soporta tanto texto
   como fotos de operaciones matemáticas.

> Nota: la capa gratuita tiene límites de solicitudes por minuto/día
> (normales en cualquier API gratuita). Son más que suficientes para un
> proyecto académico. Si los superas, espera unos minutos.

**Alternativa también gratis: Google Gemini**

1. Ve a https://aistudio.google.com/apikey e inicia sesión con una cuenta Google.
2. Genera una API key gratuita.
3. Copia `config.example.py` como `config.py` y pega la key.
4. Abre `services/ai_service.py` y cambia `PROVEEDOR = "groq"` por
   `PROVEEDOR = "gemini"`. También soporta texto y fotos.

**Otras opciones (de pago):**

1. Abre `services/ai_service.py` y cambia `PROVEEDOR` por `"claude"`,
   `"openai"` u `"openrouter"`.
2. Consigue la API key en el panel de ese proveedor y pégala en `config.py`.

### Resolver problemas a partir de una foto

En la pantalla "Resolver problema" hay un botón **"Seleccionar imagen"** que
permite elegir una foto (tomada previamente con el celular y guardada, o
desde una webcam) de una operación matemática escrita a mano o impresa. La
IA la transcribe y la resuelve, mostrando el problema detectado, el
procedimiento y el resultado. Esta función está disponible con los proveedores `"claude"`, `"openai"`,
`"gemini"` y `"groq"` (los cuatro tienen capacidad de visión). Si usas
`"openrouter"` el sistema mostrará un mensaje indicando que cambies de
proveedor para usar esta opción.

## 3. Nuevas funciones: Calculadora, Graficar y Foto por WiFi

### Menú principal rediseñado
Ahora el menú tiene las opciones a la izquierda y una ilustración
matemática (dibujada en código, sin archivos externos) a la derecha.

### Tres modos en "Resolver problema"
Al entrar a "Resolver problema" hay tres botones arriba:

- **Calculadora:** cálculo directo (suma, resta, multiplicación,
  división, potencias, raíces, funciones trigonométricas), funciona
  **sin Internet y sin usar la API de IA**.
- **Inteligencia Artificial:** escribir el problema, cargar una imagen
  desde el computador, o tomar una foto en el momento con el código QR
  (ver abajo).
- **Graficar:** dibuja una función f(x) (ej: `x^2 - 3*x + 2`, `sin(x)`)
  en modo línea, puntos o barras, con el rango de x que definas.

### Tomar foto por WiFi (código QR)

No requiere configurar nada en `config.py` ni instalar apps en el
iPhone. Funciona con un mini servidor web que la propia aplicación
levanta en tu computador:

1. En la sección "Inteligencia Artificial", haz clic en
   **"Tomar foto por WiFi (QR)"**.
2. Se abre una ventana con un código QR.
3. Escanéalo con la cámara del iPhone (no necesitas ninguna app, solo
   apuntar la cámara nativa — abre Safari solo).
4. La primera vez, Safari mostrará una advertencia de "conexión no
   privada" (es normal, es tu propio computador usando un certificado
   autofirmado): toca **"Mostrar detalles"** → **"Visitar este sitio
   web"**.
5. En la página que se abre, toca "Abrir cámara", toma la foto de la
   operación.
6. La foto se sube sola por WiFi y aparece cargada automáticamente en
   la app, en segundos.

**Requisito:** el iPhone y el computador deben estar conectados a la
**misma red WiFi** (no funciona con datos móviles, ni si están en redes
distintas). No sube nada a Internet — todo viaja dentro de tu red local.

## 4. Módulos de biometría y visión

Tras iniciar sesión, la barra lateral organiza la aplicación en: Inicio,
Resolver problema, Historial, Reconocimiento facial, Verificación de voz,
Posturas corporales, Configuración y privacidad, e Información. Hay tema
claro y oscuro (Configuración › Apariencia).

### 4.0 Registro e inicio de sesión biométrico

1. **Crear cuenta:** después de llenar nombre, usuario y contraseña aparece
   la pantalla *Configure su acceso biométrico*, donde puede registrar su
   **rostro** (5 capturas) y su **voz** (3 muestras), previo consentimiento.
   Es opcional y se puede hacer más tarde desde las secciones del programa.
2. **Iniciar sesión:** además de la contraseña, los botones **«Mi rostro»**
   y **«Mi voz»** abren la cuenta a la que pertenece el rostro o la voz.
   Si se escribe el usuario, solo se compara con esa cuenta.
3. **Rostro + postura:** al entrar con el rostro, primero se identifica la
   cuenta (3 capturas, similitud ≥ 0,45 y al menos 0,05 por encima de la
   segunda cuenta más parecida). Luego se pide un **gesto al azar**
   (mano derecha, izquierda o ambas sobre el hombro), comprobado con
   MediaPipe Pose durante 3 imágenes seguidas, mientras el rostro sigue
   coincidiendo. Esto impide entrar con una fotografía impresa; un video de
   la persona haciendo el gesto correcto todavía podría engañarlo.
4. **Voz:** una muestra de 4 a 8 s; se acepta con similitud ≥ 0,55 y margen
   de 0,05 sobre la segunda cuenta.
5. Un mismo rostro no puede registrarse en dos cuentas distintas.
6. La contraseña siempre sigue funcionando como alternativa.

### 4.1 Reconocimiento facial

- **Detección** (YuNet): indica si hay un rostro y si la captura es válida
  (iluminación, un solo rostro, distancia, nitidez).
- **Comparación de identidad** (SFace): el registro toma 5 capturas válidas y
  guarda su promedio; la verificación toma 3 capturas y acepta si la
  similitud coseno es ≥ 0,363 (umbral publicado por OpenCV para este modelo).
- **No hay detección de vida**: una fotografía, un video o una pantalla con
  la cara de la persona registrada podrían ser aceptados. Por eso la
  verificación es informativa y **no se usa para iniciar sesión**.

### 4.2 Verificación biométrica de voz

- No es reconocimiento de voz (no transcribe palabras): estima **quién**
  habla. Es independiente del texto: se puede decir cualquier frase.
- Cada muestra se valida (al menos 2 s de voz, volumen, saturación y
  relación señal/ruido ≥ 10 dB) antes de pasar por el modelo CAM++.
- Registro con 3 muestras coherentes entre sí; verificación con 1 muestra,
  aceptada si la similitud coseno es ≥ 0,50.
- El umbral 0,50 se eligió con una prueba sobre grabaciones públicas
  (6 hablantes de `sr-data`: 0 % de falsas aceptaciones). **No está
  calibrado para el micrófono y el idioma de cada usuario**; conviene
  ajustarlo (`UMBRAL_VOZ` en `core/settings.py`) con muestras reales.
- No detecta grabaciones reproducidas ni voces sintéticas.

### 4.3 Posturas corporales

- MediaPipe Pose Landmarker (lite) detecta 33 puntos; se usan hombros,
  codos, muñecas, caderas, rodillas y tobillos. Se dibujan los puntos y el
  esqueleto sobre el video.
- Ángulos articulares de codos, hombros, caderas y rodillas, solo cuando los
  tres puntos tienen visibilidad ≥ 60 %.
- La interpretación (`services/pose_analysis.py`) está separada de la
  detección y usa reglas explícitas: *De pie* (rodillas y caderas ≥ 160°),
  *Piernas flexionadas* (rodillas y caderas entre 60° y 130°), *Brazos
  levantados* (muñecas sobre la cabeza) y *Brazos en cruz* (codos ≥ 150°,
  hombros entre 70° y 110°). Avisa si la persona está fuera del encuadre o
  si la detección es insuficiente.
- **No es una herramienta médica**: no detecta lesiones ni evalúa la salud.

### 4.4 Modelos propios de Teachable Machine

La aplicación también usa modelos entrenados en
[Teachable Machine](https://teachablemachine.withgoogle.com/). Son
**clasificadores**: indican a cuál de las clases entrenadas se parece la
imagen o el sonido. No verifican la identidad (una persona no entrenada se
asignará igual a alguna clase).

| Modelo | Exportación en Teachable Machine | Carpeta | Dónde se usa |
|---|---|---|---|
| Imagen | *Exportar › Tensorflow › Keras* → `keras_model.h5` + `labels.txt` | `models/teachable/imagen/` | Reconocimiento facial › «Mi modelo (Teachable Machine)» |
| Audio | *Exportar › Tensorflow.js › Descargar* → `model.json` + `weights.bin` + `metadata.json` | `models/teachable/audio/` | Verificación de voz › «Mi modelo de audio» |

- **Audio:** basta con copiar los tres archivos. La aplicación ejecuta la red
  con numpy y reproduce el espectrograma del navegador (44,1 kHz, FFT de
  1024, 43 × 232). Clasifica el último segundo cada 0,5 s.
- **Imagen:** el `.h5` necesita TensorFlow. Para no incluirlo en la
  aplicación, se convierte **una vez** a ONNX y se ejecuta con OpenCV:

  ```bash
  # en un entorno virtual aparte, solo para convertir
  python -m venv venv_conversion
  venv_conversion\Scripts\activate
  pip install tensorflow==2.15.1 tf2onnx==1.16.1 onnx==1.16.1
  python tools/convertir_teachable_imagen.py   # crea models/teachable/imagen/model.onnx
  ```

  Al reentrenar en Teachable Machine, reemplace `keras_model.h5` y
  `labels.txt` y repita la conversión.
- La imagen se procesa como en la web de Teachable Machine: cámara en
  espejo, recorte cuadrado central, 224 × 224 y valores en [-1, 1].
- Se muestra la clase con mayor probabilidad y una barra por clase; por
  debajo del 75 % se avisa que la confianza es baja.
- Con el `.exe`, copie también `models/teachable/` junto al ejecutable.

### 4.5 Modelos y bibliotecas incorporados

| Componente | Versión | Licencia | Uso | Internet |
|---|---|---|---|---|
| opencv-contrib-python | 4.11.0.86 | Apache 2.0 | Cámara, YuNet y SFace | No |
| YuNet `face_detection_yunet_2023mar.onnx` | 2023mar | MIT | Detección de rostros | Solo para descargar |
| SFace `face_recognition_sface_2021dec.onnx` | 2021dec | Apache 2.0 | Representación del rostro | Solo para descargar |
| sherpa-onnx | 1.13.8 | Apache 2.0 | Inferencia del modelo de voz | No |
| CAM++ `3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx` | — | Apache 2.0 | Representación de la voz | Solo para descargar |
| mediapipe | 1.1.1 | Apache 2.0 | Detección de posturas | No |
| `pose_landmarker_lite.task` | float16 | Apache 2.0 | 33 puntos corporales | Solo para descargar |
| sounddevice | 0.5.6 | MIT | Captura del micrófono | No |

Las URL oficiales y los hashes SHA-256 de cada modelo están en
`core/settings.py` (`MODELOS`). Todo se ejecuta en CPU; no se requiere GPU.

## 5. Seguridad y privacidad

- La cámara y el micrófono **solo se activan cuando el usuario lo pide**,
  previa confirmación una vez por sesión, y muestran un indicador visible
  mientras están activos. Se detienen al cambiar de sección, cerrar sesión o
  cerrar la aplicación.
- El registro biométrico exige un **consentimiento explícito** que explica
  qué se captura, para qué y cómo eliminarlo.
- **No se guardan imágenes ni grabaciones**: solo la representación numérica
  (128 valores para el rostro, 512 para la voz).
- Las representaciones se guardan en SQLite **cifradas con Fernet**; la clave
  (`database/biometria.key`) está protegida con **DPAPI de Windows**, de modo
  que solo la misma cuenta de Windows en el mismo equipo puede descifrarla.
  Cada registro cifrado incluye el usuario y se rechaza si se copia a otro.
  Si DPAPI no está disponible, el registro biométrico se deshabilita.
- Los registros se eliminan desde cada módulo o desde *Configuración y
  privacidad* (también «Eliminar todos mis datos biométricos»).
- Las contraseñas ahora se guardan con PBKDF2-HMAC-SHA256 con sal; las
  cuentas antiguas (SHA-256) se migran solas en su siguiente inicio de sesión.
- La única función que usa Internet es *Resolver problema › Inteligencia
  Artificial*, que envía el texto o la imagen al proveedor configurado; la
  interfaz lo indica en esa pantalla y en Configuración.
- Riesgos: ningún modelo biométrico es infalible. Pueden ocurrir **falsos
  rechazos** (luz, ángulo, ruido, resfriado) y **falsas aceptaciones**
  (personas parecidas, fotos, grabaciones). No use estos módulos como único
  mecanismo de seguridad.

## 6. Pruebas

```bash
python tools/descargar_datos_prueba.py      # opcional: imágenes y audios públicos de prueba
python -m unittest discover -s tests -t . -v
python tools/prueba_hardware.py 0 3         # cámara 0 y micrófono reales (no guarda nada)
```

- Las pruebas de interfaz usan una cámara simulada y no necesitan hardware.
- Las pruebas que requieren modelos o datos de prueba se omiten (skip) si faltan.
- `tools/prueba_hardware.py` comprueba la cámara y el micrófono reales.

## 7. Ejecutar en modo desarrollo

```bash
python main.py
```

## 8. Agregar tu ícono (.ico) — PENDIENTE PARA TI

1. Consigue o crea un archivo de ícono en formato `.ico` (256x256 recomendado).
2. Cópialo dentro de `images/` con el nombre exacto `icon.ico`
   (puedes usar también `icon.png` para la pantalla de bienvenida y la
   ventana; para el propio `.exe` en Windows se necesita el `.ico`).

## 9. Agregar tu video de apertura — PENDIENTE PARA TI

1. Consigue un video corto en formato `.mp4` (ideal: H.264, pocos segundos).
2. Cópialo dentro de `images/` con el nombre exacto `splash_video.mp4`.
3. Si el video no reproduce en Windows, instala el paquete de códecs
   "K-Lite Codec Pack" o vuelve a exportar el video en H.264/AAC.
4. Si no agregas ningún video, la app funciona igual, solo que la pantalla
   de bienvenida no reproduce nada.

## 10. Generar el ejecutable (.exe)

Debes ejecutar este comando **en Windows** (PyInstaller genera el ejecutable
para el sistema operativo en el que se ejecuta):

```bash
pyinstaller --noconfirm --onefile --windowed ^
  --name SoftwareMatematicoIA ^
  --icon images/icon.ico ^
  --add-data "images;images" ^
  --add-data "config.py;." ^
  --hidden-import matplotlib.backends.backend_qt5agg ^
  --collect-all mediapipe ^
  --collect-all sherpa_onnx ^
  --collect-all sounddevice ^
  main.py
```

(Equivale a `pyinstaller --noconfirm SoftwareMatematicoIA.spec`, que ya
incluye estas opciones.)

> El `--hidden-import` es necesario porque PyInstaller a veces no detecta
> automáticamente el backend gráfico de matplotlib usado en la sección
> "Graficar". Los `--collect-all` incluyen las bibliotecas nativas de
> MediaPipe, sherpa-onnx (ONNX Runtime) y PortAudio.

El archivo `SoftwareMatematicoIA.exe` (≈ 150 MB) quedará en la carpeta
`dist/`. Cópialo a la carpeta `executable/` del proyecto para la entrega y
**copia también la carpeta `models/weights/` junto al .exe**
(`executable/models/weights/…`): los modelos no se empaquetan dentro del
ejecutable.

> Seguridad: `--add-data "config.py;."` incluye la API key dentro del .exe,
> de donde puede extraerse. No distribuyas ese .exe públicamente con tu key.

> Nota: si usas Linux/Mac para desarrollar, el `.exe` para Windows solo se
> puede generar corriendo PyInstaller en una máquina/VM con Windows (o
> usando un servicio de CI con runner Windows).

## 11. Estructura del proyecto

```
SoftwareMatematicoIA/
├── main.py                # Punto de entrada (bienvenida → login → contenedor con barra lateral)
├── core/                  # Configuración común: rutas y hashes de modelos, umbrales, ajustes, cifrado (DPAPI + Fernet)
├── storage/               # Repositorio de plantillas biométricas cifradas (SQLite)
├── database/              # DBManager (SQLite) + archivo .db, clave cifrada y ajustes generados en ejecución
├── interfaces/            # Pantallas PyQt5
│   ├── app_shell.py         # Barra lateral y navegación entre secciones
│   ├── home_screen.py       # Panel de inicio
│   ├── face_screen.py / voice_screen.py / pose_screen.py   # Módulos de biometría y visión
│   ├── settings_screen.py   # Configuración y privacidad
│   ├── styles.py            # Temas claro y oscuro (QSS)
│   ├── widgets.py           # Componentes reutilizables (tarjetas, mensajes, video, diálogos)
│   ├── workers.py           # Hilos de cámara y de tareas (no bloquean la interfaz)
│   ├── panels/              # Paneles de "Resolver problema": calculadora, IA, graficar
│   └── wifi_photo_dialog.py # Ventana del código QR para foto por WiFi
├── controllers/           # Lógica de negocio (auth, resolución de problemas, biometría)
├── services/              # API de IA, foto por WiFi, cámara, rostro, voz, audio y posturas
├── models/                # Clases de datos (Usuario, RegistroHistorial) y weights/ (modelos descargados)
├── utils/                 # Validaciones, excepciones, calculadora, graficador, rutas
├── tests/                 # Pruebas automatizadas (unittest)
├── tools/                 # Descarga de modelos y datos de prueba, prueba de hardware
├── images/                # icon.ico / icon.png / splash_video.mp4 (los agregas tú)
├── docs/                  # Documento técnico y manual de usuario
├── executable/            # Aquí va el .exe final
├── config.example.py      # Plantilla de configuración (cópiala a config.py)
└── requirements.txt
```

## 12. Qué falta que agregues tú (resumen)

| Elemento | Dónde | Obligatorio |
|---|---|---|
| API key del proveedor de IA | `config.py` (copiar de `config.example.py`) | Sí, para la sección IA |
| Modelos preentrenados | `python tools/descargar_modelos.py` | Sí, para rostro, voz y posturas |
| Cámara web y micrófono | Configuración › Dispositivos | Para los módulos biométricos |
| Ícono `.ico` / `.png` | `images/icon.ico`, `images/icon.png` | No (recomendado) |
| Video de apertura `.mp4` | `images/splash_video.mp4` | No (opcional) |
| Generar el `.exe` en Windows | comando `pyinstaller` de arriba | Sí, para la entrega |

