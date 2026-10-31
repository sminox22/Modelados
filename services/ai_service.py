"""
Servicio de Inteligencia Artificial.

Este módulo envía el problema matemático a un proveedor de IA (Anthropic
Claude, OpenAI, Groq, Gemini u OpenRouter) y devuelve el procedimiento y el
resultado. Está desacoplado del resto de la aplicación: los controladores
solo llaman a `AIService.resolver_problema(texto)` para texto, o
`AIService.resolver_problema_imagen(ruta_imagen)` para resolver a partir de
una foto de la operación (disponible con los proveedores "claude",
"openai", "gemini" y "groq", que tienen capacidad de visión).

===========================================================================
QUÉ DEBES HACER TÚ (obligatorio para que esto funcione):
===========================================================================
1. El proveedor configurado por defecto es Groq, que tiene CAPA GRATUITA
   sin necesidad de tarjeta de crédito y es muy rápido (baja latencia).
   Consigue tu API key gratis en: https://console.groq.com/keys
2. Si prefieres otro proveedor, cambia PROVEEDOR más abajo:
   - "gemini": también GRATIS. Key en https://aistudio.google.com/apikey
   - "claude", "openai", "openrouter": de pago, requieren tarjeta.
3. Copia el archivo `config.example.py` como `config.py` (en la raíz del
   proyecto) y pega tu API key allí. NUNCA subas `config.py` a GitHub.
4. La capa gratuita de Groq tiene límites de solicitudes por minuto/día
   (suficientes para un proyecto académico). Si los superas, la app
   mostrará el mensaje de error correspondiente; simplemente espera unos
   minutos.
===========================================================================
"""
import base64
import json
import mimetypes
import os
import urllib.request
import urllib.error

from utils.exceptions import ApiError, ConexionInternetError
from utils.validators import hay_conexion_internet

try:
    import config  
except ImportError:
    config = None


class AIService:
    # Cambia este valor para elegir el proveedor: "claude", "openai",
    # "gemini", "groq" u "openrouter"
    # Por defecto se usa "groq": tiene capa GRATUITA sin tarjeta de
    # crédito y es muy rápido. Soporta texto e imagen (visión).
    PROVEEDOR = "groq"

    PROMPT_SISTEMA = (
        "Eres un tutor de matemáticas para estudiantes de programación. "
        "Cuando el usuario te dé un problema matemático, respondes ÚNICAMENTE "
        "en este formato, sin texto adicional:\n"
        "PROCEDIMIENTO:\n<pasos numerados y breves>\n"
        "RESULTADO:\n<resultado final, una sola línea>"
    )

    PROMPT_SISTEMA_IMAGEN = (
        "Eres un tutor de matemáticas para estudiantes de programación. "
        "El usuario te enviará una foto de un problema u operación matemática "
        "escrita a mano o impresa. Primero identifica el problema exactamente "
        "como aparece en la imagen y luego resuélvelo. Responde ÚNICAMENTE en "
        "este formato, sin texto adicional:\n"
        "PROBLEMA_DETECTADO:\n<transcripción del problema que ves en la imagen>\n"
        "PROCEDIMIENTO:\n<pasos numerados y breves>\n"
        "RESULTADO:\n<resultado final, una sola línea>"
    )

    # Proveedores con capacidad de visión ya implementada en este archivo.
    # OpenRouter también podría soportar visión con ajustes, pero no está
    # implementado aquí todavía.
    PROVEEDORES_CON_VISION = ("claude", "openai", "gemini", "groq")

    @classmethod
    def resolver_problema_imagen(cls, ruta_imagen: str) -> dict:
        """
        Igual que resolver_problema, pero envía una imagen (foto de la
        operación) en lugar de texto. Devuelve además la clave
        "problema_detectado" con lo que la IA leyó en la imagen.
        """
        if not hay_conexion_internet():
            raise ConexionInternetError()

        if config is None or not getattr(config, "API_KEY", ""):
            raise ApiError(
                "No se ha configurado la API key. Copia 'config.example.py' "
                "como 'config.py' y agrega tu clave."
            )

        if cls.PROVEEDOR not in cls.PROVEEDORES_CON_VISION:
            raise ApiError(
                f"El proveedor '{cls.PROVEEDOR}' no tiene soporte de imágenes "
                f"implementado en esta versión. Usa 'claude', 'openai', "
                f"'gemini' o 'groq' para resolver problemas desde una foto."
            )

        if not os.path.exists(ruta_imagen):
            raise ApiError("No se encontró el archivo de imagen seleccionado.")

        try:
            if cls.PROVEEDOR == "claude":
                texto = cls._llamar_claude_vision(ruta_imagen)
            elif cls.PROVEEDOR == "openai":
                texto = cls._llamar_openai_vision(ruta_imagen)
            elif cls.PROVEEDOR == "gemini":
                texto = cls._llamar_gemini_vision(ruta_imagen)
            elif cls.PROVEEDOR == "groq":
                texto = cls._llamar_groq_vision(ruta_imagen)
        except urllib.error.HTTPError as e:
            detalle = cls._leer_cuerpo_error(e)
            raise ApiError(f"Error de la API ({e.code}): {detalle}")
        except urllib.error.URLError as e:
            raise ApiError(f"Error de comunicación con la API: {e}")
        except Exception as e:
            raise ApiError(f"Error inesperado consultando la IA: {e}")

        return cls._parsear_respuesta_imagen(texto)

    @staticmethod
    def _codificar_imagen(ruta_imagen: str):
        tipo_mime, _ = mimetypes.guess_type(ruta_imagen)
        if tipo_mime not in ("image/png", "image/jpeg", "image/jpg", "image/webp"):
            tipo_mime = "image/jpeg"  # valor por defecto razonable
        with open(ruta_imagen, "rb") as f:
            datos_b64 = base64.b64encode(f.read()).decode("utf-8")
        return tipo_mime, datos_b64

    @classmethod
    def _llamar_claude_vision(cls, ruta_imagen: str) -> str:
        tipo_mime, datos_b64 = cls._codificar_imagen(ruta_imagen)
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": config.API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": "claude-sonnet-5",
            "max_tokens": 800,
            "system": cls.PROMPT_SISTEMA_IMAGEN,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": tipo_mime, "data": datos_b64
                    }},
                    {"type": "text", "text": "Resuelve el problema matemático de esta imagen."},
                ],
            }],
        }
        data = cls._post(url, headers, body)
        return data["content"][0]["text"]

    @classmethod
    def _llamar_openai_vision(cls, ruta_imagen: str) -> str:
        tipo_mime, datos_b64 = cls._codificar_imagen(ruta_imagen)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": cls.PROMPT_SISTEMA_IMAGEN},
                {"role": "user", "content": [
                    {"type": "text", "text": "Resuelve el problema matemático de esta imagen."},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{tipo_mime};base64,{datos_b64}"
                    }},
                ]},
            ],
        }
        data = cls._post(url, headers, body)
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parsear_respuesta_imagen(texto: str) -> dict:
        problema_detectado, procedimiento, resultado = "", texto, ""
        if "PROBLEMA_DETECTADO:" in texto:
            texto = texto.split("PROBLEMA_DETECTADO:")[1]
        if "PROCEDIMIENTO:" in texto:
            partes = texto.split("PROCEDIMIENTO:")
            problema_detectado = partes[0].strip()
            texto = "PROCEDIMIENTO:" + partes[1]
        if "RESULTADO:" in texto:
            partes = texto.split("RESULTADO:")
            procedimiento = partes[0].replace("PROCEDIMIENTO:", "").strip()
            resultado = partes[1].strip()

        # Algunos modelos, cuando se quedan sin espacio de respuesta, en
        # vez de dejar el campo vacío devuelven una plantilla sin llenar
        # (ej. "<transcription>", "<steps>"). Se detecta y se avisa en
        # vez de mostrarlo tal cual al usuario.
        def _es_plantilla_vacia(valor: str) -> bool:
            v = valor.strip().strip("<>").lower()
            return valor.strip().startswith("<") and valor.strip().endswith(">") and len(v) < 40

        if _es_plantilla_vacia(problema_detectado) or _es_plantilla_vacia(procedimiento) or _es_plantilla_vacia(resultado):
            raise ApiError(
                "El modelo no devolvió una respuesta completa (probablemente se "
                "quedó sin espacio de respuesta). Intenta de nuevo; si se repite, "
                "prueba con otro proveedor (por ejemplo, 'gemini')."
            )

        return {
            "problema_detectado": problema_detectado or "(no se pudo leer el enunciado)",
            "procedimiento": procedimiento,
            "resultado": resultado or "Ver procedimiento.",
        }

    @classmethod
    def resolver_problema(cls, problema: str) -> dict:
        """
        Devuelve un diccionario {"procedimiento": str, "resultado": str}.
        Lanza ConexionInternetError o ApiError si algo falla.
        """
        if not hay_conexion_internet():
            raise ConexionInternetError()

        if config is None or not getattr(config, "API_KEY", ""):
            raise ApiError(
                "No se ha configurado la API key. Copia 'config.example.py' "
                "como 'config.py' y agrega tu clave (ver instrucciones en "
                "services/ai_service.py)."
            )

        try:
            if cls.PROVEEDOR == "claude":
                texto = cls._llamar_claude(problema)
            elif cls.PROVEEDOR == "openai":
                texto = cls._llamar_openai(problema)
            elif cls.PROVEEDOR == "groq":
                texto = cls._llamar_groq(problema)
            elif cls.PROVEEDOR == "gemini":
                texto = cls._llamar_gemini(problema)
            elif cls.PROVEEDOR == "openrouter":
                texto = cls._llamar_openrouter(problema)
            else:
                raise ApiError(f"Proveedor de IA no reconocido: {cls.PROVEEDOR}")
        except urllib.error.HTTPError as e:
            detalle = cls._leer_cuerpo_error(e)
            raise ApiError(f"Error de la API ({e.code}): {detalle}")
        except urllib.error.URLError as e:
            raise ApiError(f"Error de comunicación con la API: {e}")
        except Exception as e:
            raise ApiError(f"Error inesperado consultando la IA: {e}")

        return cls._parsear_respuesta(texto)

    # ---------------- Proveedores ----------------

    @classmethod
    def _llamar_claude(cls, problema: str) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": config.API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": "claude-sonnet-5",
            "max_tokens": 800,
            "system": cls.PROMPT_SISTEMA,
            "messages": [{"role": "user", "content": problema}],
        }
        data = cls._post(url, headers, body)
        return data["content"][0]["text"]

    @classmethod
    def _llamar_openai(cls, problema: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": cls.PROMPT_SISTEMA},
                {"role": "user", "content": problema},
            ],
        }
        data = cls._post(url, headers, body)
        return data["choices"][0]["message"]["content"]

    @classmethod
    def _llamar_groq(cls, problema: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": cls.PROMPT_SISTEMA},
                {"role": "user", "content": problema},
            ],
            "max_completion_tokens": 1200,
            "reasoning_effort": "low",
        }
        data = cls._post(url, headers, body)
        return data["choices"][0]["message"]["content"]

    @classmethod
    def _llamar_groq_vision(cls, ruta_imagen: str) -> str:
        tipo_mime, datos_b64 = cls._codificar_imagen(ruta_imagen)
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "qwen/qwen3.6-27b",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": cls.PROMPT_SISTEMA_IMAGEN + "\n\nResuelve el problema matemático de esta imagen."},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{tipo_mime};base64,{datos_b64}"
                    }},
                ],
            }],
            # qwen3.6-27b es un modelo "pensante": si no se limita el
            # razonamiento, puede gastar todo max_completion_tokens
            # "pensando" y dejar la respuesta final vacía o incompleta.
            "reasoning_effort": "none",
            "max_completion_tokens": 1500,
        }
        data = cls._post(url, headers, body)
        return data["choices"][0]["message"]["content"]

    @classmethod
    def _llamar_openrouter(cls, problema: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "system", "content": cls.PROMPT_SISTEMA},
                {"role": "user", "content": problema},
            ],
        }
        data = cls._post(url, headers, body)
        return data["choices"][0]["message"]["content"]

    @classmethod
    def _llamar_gemini(cls, problema: str) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={config.API_KEY}"
        )
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [
                {"parts": [{"text": cls.PROMPT_SISTEMA + "\n\n" + problema}]}
            ]
        }
        data = cls._post(url, headers, body)
        return data["candidates"][0]["content"]["parts"][0]["text"]

    @classmethod
    def _llamar_gemini_vision(cls, ruta_imagen: str) -> str:
        tipo_mime, datos_b64 = cls._codificar_imagen(ruta_imagen)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-lite:generateContent?key={config.API_KEY}"
        )
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [{
                "parts": [
                    {"text": cls.PROMPT_SISTEMA_IMAGEN + "\n\nResuelve el problema matemático de esta imagen."},
                    {"inline_data": {"mime_type": tipo_mime, "data": datos_b64}},
                ]
            }]
        }
        data = cls._post(url, headers, body)
        return data["candidates"][0]["content"]["parts"][0]["text"]

    # ---------------- Utilidades ----------------

    @staticmethod
    def _post(url, headers, body, timeout=100):
        # Se agrega un User-Agent "normal" porque algunos proveedores
        # (ej. Groq, protegido por Cloudflare) bloquean el User-Agent por
        # defecto de Python ("Python-urllib/3.x") por parecer tráfico de
        # bot, aunque la API key y la red estén perfectamente bien.
        headers_finales = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SoftwareMatematicoIA/1.0",
            **headers,
        }
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers_finales, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _leer_cuerpo_error(error_http) -> str:
        """
        Extrae el mensaje real que devuelve el proveedor (Google, OpenAI,
        Anthropic, etc.) dentro del cuerpo de un HTTPError, en vez de
        mostrar solo el genérico "HTTP Error 404: Not Found". Si el cuerpo
        no es JSON (por ejemplo, una página de bloqueo de Cloudflare),
        devuelve el texto crudo para poder diagnosticar el problema.
        """
        try:
            cuerpo = error_http.read().decode("utf-8", errors="replace")
        except Exception:
            return str(error_http)

        try:
            datos = json.loads(cuerpo)
            # La mayoría de proveedores usan {"error": {"message": "..."}}
            if isinstance(datos, dict) and "error" in datos:
                error_obj = datos["error"]
                if isinstance(error_obj, dict):
                    return error_obj.get("message", cuerpo)
                if isinstance(error_obj, list) and error_obj:
                    return error_obj[0].get("error", {}).get("message", cuerpo)
            return cuerpo
        except (json.JSONDecodeError, ValueError):
            # No es JSON: probablemente un bloqueo de red/Cloudflare antes
            # de llegar a la aplicación de Groq. Devolvemos un extracto.
            texto_plano = cuerpo.strip()
            if "cloudflare" in texto_plano.lower() or "access denied" in texto_plano.lower():
                return (
                    "Bloqueo de red/Cloudflare antes de llegar a la API (no es un "
                    "error de tu API key ni del código). Prueba desde otra red, sin "
                    "VPN/proxy, o revisa tu firewall/antivirus."
                )
            return texto_plano[:300] if texto_plano else str(error_http)

    @staticmethod
    def _parsear_respuesta(texto: str) -> dict:
        procedimiento, resultado = texto, ""
        if "RESULTADO:" in texto:
            partes = texto.split("RESULTADO:")
            procedimiento = partes[0].replace("PROCEDIMIENTO:", "").strip()
            resultado = partes[1].strip()
        return {"procedimiento": procedimiento, "resultado": resultado or "Ver procedimiento."}
