"""Solicitud de permiso, dentro de la aplicación, antes de activar la cámara o el micrófono."""
from interfaces.widgets import confirmar

_TEXTOS = {
    "camara": ("Permiso para usar la cámara",
               "La aplicación encenderá la cámara de este equipo. Las imágenes se procesan solo "
               "en este computador, no se guardan ni se envían a Internet. Puede detenerla en "
               "cualquier momento con el botón «Detener cámara».\n\n¿Desea permitir el acceso?",
               "Permitir cámara"),
    "microfono": ("Permiso para usar el micrófono",
                  "La aplicación grabará audio desde el micrófono mientras la grabación esté "
                  "activa. El audio se procesa solo en este computador, no se guarda en disco "
                  "ni se envía a Internet.\n\n¿Desea permitir el acceso?",
                  "Permitir micrófono"),
}


def solicitar_permiso(parent, contexto, recurso: str) -> bool:
    """Pide permiso una vez por sesión. Devuelve True si el usuario lo concede."""
    if recurso in contexto.permisos:
        return True
    titulo, texto, aceptar = _TEXTOS[recurso]
    if confirmar(parent, titulo, texto, aceptar):
        contexto.permisos.add(recurso)
        return True
    return False
