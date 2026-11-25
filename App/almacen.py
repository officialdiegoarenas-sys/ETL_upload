"""Guarda los favoritos y recordatorios de cada usuario en un archivo JSON local."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import date
from pathlib import Path

TIPOS_EVENTO = ["Audiencia", "Plazo o vencimiento", "Reunión", "Recordatorio"]


def _ruta() -> Path:
    env = os.environ.get("APP_DATOS_USUARIO")
    return Path(env) if env else Path(__file__).resolve().parent / "datos_usuario" / "usuarios.json"


def _clave(correo: str) -> str:
    return (correo or "").strip().lower()


def _leer() -> dict:
    ruta = _ruta()
    try:
        with ruta.open("r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _escribir(datos: dict) -> None:
    ruta = _ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Escritura atómica: nunca queda el archivo a medias si se cierra la app.
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ruta)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _usuario(datos: dict, correo: str) -> dict:
    u = datos.setdefault(_clave(correo), {})
    u.setdefault("favoritos", [])
    u.setdefault("eventos", [])
    return u


# Favoritos
def favoritos(correo: str) -> list[str]:
    return list(_usuario(_leer(), correo)["favoritos"])


def es_favorito(correo: str, reporte_id: str) -> bool:
    return reporte_id in favoritos(correo)


def alternar_favorito(correo: str, reporte_id: str) -> bool:
    """Agrega o quita el reporte. Devuelve True si quedó guardado."""
    datos = _leer()
    u = _usuario(datos, correo)
    if reporte_id in u["favoritos"]:
        u["favoritos"].remove(reporte_id)
        guardado = False
    else:
        u["favoritos"].append(reporte_id)
        guardado = True
    _escribir(datos)
    return guardado


# Recordatorios
def eventos(correo: str) -> list[dict]:
    return sorted(_usuario(_leer(), correo)["eventos"], key=lambda e: (e["fecha"], e["titulo"]))


def agregar_evento(correo: str, fecha: date, titulo: str, tipo: str, nota: str = "") -> dict:
    titulo = (titulo or "").strip()
    if not titulo:
        raise ValueError("Escriba un título para el recordatorio.")
    if len(titulo) > 120:
        raise ValueError("El título es muy largo (máximo 120 letras).")
    if tipo not in TIPOS_EVENTO:
        raise ValueError("Tipo de recordatorio no válido.")
    if not isinstance(fecha, date):
        raise ValueError("Fecha no válida.")
    evento = {
        "id": uuid.uuid4().hex[:10],
        "fecha": fecha.isoformat(),
        "titulo": titulo,
        "tipo": tipo,
        "nota": (nota or "").strip()[:500],
    }
    datos = _leer()
    _usuario(datos, correo)["eventos"].append(evento)
    _escribir(datos)
    return evento


def eliminar_evento(correo: str, evento_id: str) -> bool:
    datos = _leer()
    u = _usuario(datos, correo)
    antes = len(u["eventos"])
    u["eventos"] = [e for e in u["eventos"] if e["id"] != evento_id]
    _escribir(datos)
    return len(u["eventos"]) < antes
