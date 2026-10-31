# Documento de Requerimientos — Software Matemático IA

## 1. ¿Quién utilizará el sistema?
Aprendices del programa de formación ADSO (Análisis y Desarrollo de Software)
que necesiten resolver y consultar el historial de problemas matemáticos.

## 2. ¿Qué problema resuelve?
Permite plantear problemas matemáticos en lenguaje natural y obtener, de
forma automática, el procedimiento y el resultado, apoyándose en un
servicio de Inteligencia Artificial, evitando resolverlos manualmente y
dejando registro histórico de cada consulta.

## 3. ¿Qué funcionalidades tendrá?
- Registro e inicio de sesión de usuarios.
- Resolución de problemas matemáticos vía IA (procedimiento + resultado).
- Historial de consultas por usuario, con buscador.
- Validaciones de entrada y manejo de errores.
- Generación de ejecutable `.exe` para Windows.

## 4. ¿Qué datos almacenará?
- **Usuarios:** id, nombre, usuario, contraseña (hash PBKDF2-HMAC-SHA256 con sal).
- **Historial:** id, usuario, problema, respuesta, fecha, hora.
- **Plantillas biométricas:** usuario, tipo (rostro/voz), modelo, vector cifrado
  (Fernet + DPAPI), número de muestras, fecha de consentimiento. No se guardan
  imágenes ni grabaciones.

## 5. ¿Qué información mostrará?
Procedimiento y resultado de cada problema resuelto; listado histórico de
consultas propias (fecha, problema, respuesta); mensajes de error claros.

## 6. ¿Qué servicio de IA utilizará?
Configurable: Anthropic Claude (por defecto), OpenAI, Google Gemini, Groq u
OpenRouter. Se define en `services/ai_service.py` (`PROVEEDOR`) y la API key
en `config.py`.

## Requerimientos funcionales (RF)
| # | Requerimiento |
|---|---|
| RF01 | El sistema debe permitir registrar un nuevo usuario validando que no exista duplicado. |
| RF02 | El sistema debe permitir iniciar sesión validando usuario y contraseña. |
| RF03 | El sistema debe rechazar el ingreso con usuarios inexistentes o contraseña incorrecta. |
| RF04 | El sistema debe permitir ingresar un problema matemático en lenguaje natural. |
| RF05 | El sistema debe enviar el problema a la API de IA y mostrar procedimiento y resultado. |
| RF06 | El sistema debe registrar automáticamente cada consulta en el historial (usuario, problema, respuesta, fecha, hora). |
| RF07 | El sistema debe permitir consultar y filtrar el historial propio. |
| RF08 | El sistema debe mostrar mensajes claros ante errores (campos vacíos, sin conexión, error de API, error de base de datos). |
| RF09 | El sistema debe permitir cerrar sesión y salir de la aplicación. |
| RF10 | El sistema debe permitir seleccionar una foto de una operación matemática y enviarla a la IA para su lectura y resolución (proveedores con visión: Claude u OpenAI). |
| RF11 | El sistema debe mostrar el problema que la IA detectó/transcribió de la imagen, además del procedimiento y el resultado. |
| RF12 | El sistema debe permitir registrar, verificar y eliminar el rostro del usuario, previa aceptación de un consentimiento explícito. |
| RF13 | El sistema debe validar la calidad de la captura facial (iluminación, un solo rostro, distancia) y explicar los errores. |
| RF14 | El sistema debe permitir registrar, verificar y eliminar la voz del usuario (verificación del hablante, no transcripción). |
| RF15 | El sistema debe validar duración, volumen, saturación y ruido de las muestras de voz antes de compararlas. |
| RF16 | El sistema debe detectar puntos corporales con la cámara, dibujar el esqueleto, calcular ángulos articulares y avisar si la persona está fuera del encuadre. |
| RF17 | El sistema debe permitir cambiar tema, cámara y micrófono, y eliminar todos los datos biométricos del usuario. |

## Requerimientos no funcionales (RNF)
| # | Requerimiento |
|---|---|
| RNF01 | La interfaz debe ser clara, organizada y de fácil uso (PyQt5). |
| RNF02 | La base de datos debe crearse automáticamente en el primer arranque (SQLite). |
| RNF03 | Las contraseñas deben almacenarse con hash PBKDF2-HMAC-SHA256 con sal, nunca en texto plano. |
| RNF04 | La aplicación debe manejar excepciones sin cerrarse inesperadamente. |
| RNF05 | La consulta a la IA no debe congelar la interfaz (se ejecuta en un hilo aparte). |
| RNF06 | El sistema debe poder compilarse como ejecutable `.exe` independiente para Windows. |
| RNF07 | El código debe estar organizado por módulos (MVC): models, interfaces (vistas), controllers, services, core, storage, utils. |
| RNF08 | Los datos biométricos deben procesarse localmente y guardarse cifrados; la cámara y el micrófono solo se activan a petición del usuario. |
| RNF09 | La captura de cámara y la inferencia de modelos no deben congelar la interfaz y deben liberar los dispositivos al salir. |
