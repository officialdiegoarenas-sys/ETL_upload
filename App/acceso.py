"""Login simulado: el correo debe contener la palabra "fiscalia"; la contraseña puede ser cualquiera."""
from __future__ import annotations

import re
import unicodedata

PALABRA_CLAVE = "fiscalia"
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def normalizar_correo(correo: str) -> str:
    return (correo or "").strip().lower()


def validar_acceso(correo: str, clave: str) -> tuple[bool, str]:
    """Devuelve (permitido, mensaje). El mensaje explica en lenguaje simple qué corregir."""
    correo = normalizar_correo(correo)
    if not correo:
        return False, "Escriba su correo institucional."
    if not _RE_CORREO.match(correo):
        return False, "El correo no parece válido. Ejemplo: nombre@fiscalia.gov.co"
    if PALABRA_CLAVE not in _sin_tildes(correo):
        return False, "Use su correo institucional: debe contener la palabra «fiscalia»."
    if not clave:
        return False, "Escriba su contraseña (por ahora puede ser cualquiera)."
    return True, "Bienvenido(a)."


def nombre_para_mostrar(correo: str) -> str:
    """'maria.perez@fiscalia.gov.co' -> 'Maria Perez'."""
    local = normalizar_correo(correo).split("@")[0]
    sin_clave = re.sub(PALABRA_CLAVE, "", _sin_tildes(local))      # 'diegofiscalia' -> 'diego'
    partes = re.split(r"[._\-\d]+", sin_clave or local)
    return " ".join(p.capitalize() for p in partes if p) or "Usuario"
