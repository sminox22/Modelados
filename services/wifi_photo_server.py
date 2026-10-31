"""
Servidor web local para recibir una foto tomada desde el iPhone por WiFi.

Cómo funciona (sin apps adicionales en el iPhone, solo Safari):
1. Se levanta un mini servidor HTTP dentro de la propia app, en un puerto
   libre de la máquina.
2. Se genera un código QR con la URL de ese servidor (ej:
   http://192.168.1.34:53214/).
3. El usuario escanea el QR con la cámara del iPhone (abre Safari solo).
4. La página muestra un botón que abre la cámara nativa del iPhone
   (gracias al atributo HTML "capture").
5. Al tomar la foto, el navegador la sube automáticamente al servidor.
6. La app (que está vigilando) detecta la foto recién subida y la carga.

Requiere que el iPhone y el computador estén conectados al MISMO WiFi.
No sube nada a Internet: todo viaja dentro de la red local.
"""
import http.server
import io
import os
import socket
import ssl
import tempfile
import threading
import time
import uuid

from utils.ssl_cert import obtener_o_crear_certificado


class _ManejadorSubidaFoto(http.server.BaseHTTPRequestHandler):
    # Se inyecta desde el servidor: carpeta_destino, callback_foto_recibida
    carpeta_destino = None
    callback_foto_recibida = None

    def log_message(self, formato, *args):
        pass  # silencia los logs por consola de cada petición HTTP

    def do_GET(self):
        if self.path != "/" and self.path != "/index.html":
            self.send_response(404)
            self.end_headers()
            return
        html = _PAGINA_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def do_POST(self):
        if self.path != "/upload":
            self.send_response(404)
            self.end_headers()
            return

        try:
            content_type = self.headers.get("Content-Type", "")
            longitud = int(self.headers.get("Content-Length", 0))
            cuerpo = self.rfile.read(longitud)

            ruta_guardada = self._guardar_imagen_multipart(cuerpo, content_type)

            if ruta_guardada and self.callback_foto_recibida:
                self.callback_foto_recibida(ruta_guardada)

            respuesta = _PAGINA_EXITO.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(respuesta)))
            self.end_headers()
            self.wfile.write(respuesta)
        except Exception:
            self.send_response(500)
            self.end_headers()

    def _guardar_imagen_multipart(self, cuerpo: bytes, content_type: str):
        """
        Parseo manual (sin librerías externas ni el módulo 'cgi', que está
        obsoleto/eliminado en versiones recientes de Python) del cuerpo
        multipart/form-data que envía el formulario HTML de la foto.
        """
        if "boundary=" not in content_type:
            return None
        boundary = content_type.split("boundary=")[1].strip()
        marcador = ("--" + boundary).encode("utf-8")

        partes = cuerpo.split(marcador)
        for parte in partes:
            if b"filename=" not in parte:
                continue
            if b"\r\n\r\n" not in parte:
                continue
            cabeceras, datos = parte.split(b"\r\n\r\n", 1)
            # Quita el \r\n final que antecede al siguiente boundary
            datos = datos.rstrip(b"\r\n")
            if not datos:
                continue

            extension = ".jpg"
            cabeceras_texto = cabeceras.decode("utf-8", errors="ignore")
            if ".png" in cabeceras_texto.lower():
                extension = ".png"
            elif ".heic" in cabeceras_texto.lower():
                extension = ".heic"

            nombre_archivo = f"foto_iphone_wifi_{uuid.uuid4().hex[:8]}{extension}"
            ruta_completa = os.path.join(self.carpeta_destino, nombre_archivo)
            with open(ruta_completa, "wb") as f:
                f.write(datos)
            return ruta_completa
        return None


class ServidorFotoWifi:
    """
    Administra el ciclo de vida del servidor: iniciar en un puerto libre,
    exponer la URL/QR, y detenerlo cuando ya no se necesita.
    """

    def __init__(self):
        self._servidor = None
        self._hilo = None
        self.carpeta_destino = os.path.join(tempfile.gettempdir(), "software_matematico_ia_fotos_wifi")
        os.makedirs(self.carpeta_destino, exist_ok=True)
        self._ruta_foto_recibida = None
        self._lock = threading.Lock()

    def _al_recibir_foto(self, ruta):
        with self._lock:
            self._ruta_foto_recibida = ruta

    def obtener_foto_recibida(self):
        with self._lock:
            return self._ruta_foto_recibida

    def iniciar(self) -> str:
        """
        Inicia el servidor en un puerto libre, sirviendo HTTPS (con un
        certificado autofirmado) para evitar el bloqueo de Safari a
        conexiones HTTP sin cifrar. Devuelve la URL completa (https://...).
        """
        _ManejadorSubidaFoto.carpeta_destino = self.carpeta_destino
        _ManejadorSubidaFoto.callback_foto_recibida = self._al_recibir_foto

        ip_local = self._obtener_ip_local()

        self._servidor = http.server.HTTPServer(("0.0.0.0", 0), _ManejadorSubidaFoto)
        puerto = self._servidor.server_address[1]

        ruta_cert, ruta_llave = obtener_o_crear_certificado(ip_local)
        contexto_ssl = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexto_ssl.load_cert_chain(certfile=ruta_cert, keyfile=ruta_llave)
        self._servidor.socket = contexto_ssl.wrap_socket(self._servidor.socket, server_side=True)

        self._hilo = threading.Thread(target=self._servidor.serve_forever, daemon=True)
        self._hilo.start()

        return f"https://{ip_local}:{puerto}/"

    def detener(self):
        if self._servidor:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None

    @staticmethod
    def _obtener_ip_local() -> str:
        """
        Obtiene la IP local del equipo dentro de la red WiFi (no la IP
        pública de Internet). El truco de conectar un socket UDP a una IP
        externa no envía datos realmente; solo se usa para que el sistema
        operativo elija la interfaz de red correcta.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except OSError:
            return socket.gethostbyname(socket.gethostname())


_PAGINA_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Software Matemático IA</title>
<style>
  body { background:#1a0f0f; color:#f5e6e6; font-family: -apple-system, sans-serif;
         display:flex; flex-direction:column; align-items:center; justify-content:center;
         min-height:100vh; margin:0; padding:24px; text-align:center; }
  h1 { color:#ef4444; font-size:22px; }
  p { color:#c99a9a; }
  label { background:#c1121f; color:white; padding:18px 32px; border-radius:10px;
          font-size:18px; font-weight:600; display:inline-block; margin-top:20px; }
  input[type=file] { display:none; }
  #estado { margin-top:20px; color:#c99a9a; }
</style>
</head>
<body>
  <h1>Tomar foto de la operación</h1>
  <p>Presiona el botón, toma la foto de tu operación matemática y se enviará
  automáticamente a la aplicación.</p>
  <form id="formulario" action="/upload" method="post" enctype="multipart/form-data">
    <label for="foto">Abrir cámara</label>
    <input type="file" id="foto" name="foto" accept="image/*" capture="environment"
           onchange="document.getElementById('formulario').submit(); document.getElementById('estado').innerText='Enviando...';">
  </form>
  <div id="estado"></div>
</body>
</html>"""

_PAGINA_EXITO = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Foto recibida</title>
<style>
  body { background:#1a0f0f; color:#f5e6e6; font-family: -apple-system, sans-serif;
         display:flex; flex-direction:column; align-items:center; justify-content:center;
         min-height:100vh; margin:0; padding:24px; text-align:center; }
  h1 { color:#ef4444; }
</style>
</head>
<body>
  <h1>&#10003; Foto enviada correctamente</h1>
  <p>Ya puedes volver a la aplicación en tu computador. Puedes cerrar esta pestaña.</p>
</body>
</html>"""
