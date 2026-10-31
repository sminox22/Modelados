"""
Genera (una sola vez, y lo reutiliza) un certificado autofirmado para que
el servidor local de la app pueda hablar HTTPS en vez de HTTP.

Por qué es necesario: desde iOS 17, Safari puede bloquear por completo las
conexiones HTTP sin cifrar ("Error en la navegación debido a que se
solicitó una dirección URL HTTP aunque sólo se admite HTTPS"). Usar HTTPS,
aunque sea con un certificado autofirmado (no emitido por una autoridad
reconocida), evita ese bloqueo. Safari mostrará una advertencia de
"conexión no privada" la primera vez -- es normal con certificados
autofirmados -- y el usuario debe tocar "Mostrar detalles" -> "visitar
este sitio web" una única vez.
"""
import datetime
import ipaddress
import os
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def obtener_o_crear_certificado(ip_local: str):
    """
    Devuelve (ruta_certificado, ruta_llave). Si ya existen de una ejecución
    anterior, los reutiliza; si no, los genera.
    """
    carpeta = os.path.join(tempfile.gettempdir(), "software_matematico_ia_certs")
    os.makedirs(carpeta, exist_ok=True)
    ruta_cert = os.path.join(carpeta, "certificado.pem")
    ruta_llave = os.path.join(carpeta, "llave.pem")

    if os.path.exists(ruta_cert) and os.path.exists(ruta_llave):
        return ruta_cert, ruta_llave

    llave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    nombre = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, ip_local),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Software Matematico IA"),
    ])

    nombres_alternativos = [x509.IPAddress(ipaddress.ip_address(ip_local))]
    try:
        nombres_alternativos.append(x509.IPAddress(ipaddress.ip_address("127.0.0.1")))
    except ValueError:
        pass

    certificado = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(llave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(nombres_alternativos), critical=False)
        .sign(llave, hashes.SHA256())
    )

    with open(ruta_cert, "wb") as f:
        f.write(certificado.public_bytes(serialization.Encoding.PEM))

    with open(ruta_llave, "wb") as f:
        f.write(llave.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    return ruta_cert, ruta_llave
