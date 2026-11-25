"""Lectura de la capa Gold (CSV o API) y limpieza de etiquetas para el dashboard."""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"

# Se usa solo si config.yaml no trae la sección ``app.datasets``.
DATASETS_POR_DEFECTO = {
    "etapa": "fiscalia_procesos_etapa_gold.csv",
    "departamento": "fiscalia_procesos_departamento_gold.csv",
    "anio_capitulo": "fiscalia_procesos_año_capitulo_gold.csv",
    "top_delitos": "fiscalia_top_delitos_gold.csv",
    "sentencias": "fiscalia_procesados_sentencias_gold.csv",
    "perfil": "fiscalia_perfil_condenados_gold.csv",
    "secop": "datos_secop_gold.csv",
    "procuraduria": "resumen_procuraduria_gold.csv",
    "contraloria": "dataset_contraloria.csv",
}


class DatoNoDisponible(Exception):
    """El dataset Gold no existe todavía (hay que correr main.py)."""


class ApiNoDisponible(Exception):
    """La API no responde (hay que iniciarla con: uvicorn api.main:app)."""


def consultar(q: str, timeout: float = 8.0) -> dict:
    """Consulta por cédula/NIT o número de proceso a través de la API (/consulta).

    Lanza ValueError si el texto no es válido y ApiNoDisponible si la API está apagada.
    """
    import requests

    try:
        resp = requests.get(f"{api_url()}/consulta", params={"q": q}, timeout=timeout)
    except requests.RequestException as e:
        raise ApiNoDisponible("No se pudo conectar con el servicio de datos. Pida iniciar la API (uvicorn api.main:app).") from e
    if resp.status_code == 422:
        detalle = resp.json().get("detail")
        raise ValueError(detalle if isinstance(detalle, str) else "Escriba al menos 4 caracteres (cédula o número de proceso).")
    if resp.status_code == 503:
        raise DatoNoDisponible(resp.json().get("detail", "La capa de consulta aún no está construida."))
    resp.raise_for_status()
    return resp.json()


# Configuración
def cargar_config() -> dict:
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return {}


def config_app() -> dict:
    return cargar_config().get("app", {}) or {}


def datasets() -> dict:
    return config_app().get("datasets") or DATASETS_POR_DEFECTO


def ruta_gold() -> Path:
    carpeta = (cargar_config().get("paths", {}) or {}).get("gold", "data/gold")
    return BASE_DIR / carpeta


def fuente_datos() -> str:
    return (os.environ.get("APP_FUENTE_DATOS") or config_app().get("fuente_datos") or "csv").lower()


def api_url() -> str:
    return (os.environ.get("APP_API_URL") or config_app().get("api_url") or "http://127.0.0.1:8000").rstrip("/")


# Limpieza de texto (Gold viene sin tildes en varios campos)
def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))


_ACENTOS = {
    "celebracion": "celebración", "concusion": "concusión", "usurpacion": "usurpación",
    "utilizacion": "utilización", "informacion": "información", "ilicito": "ilícito",
    "trafico": "tráfico", "omision": "omisión", "ejecucion": "ejecución",
    "indagacion": "indagación", "investigacion": "investigación", "publico": "público",
    "publicos": "públicos", "publica": "pública", "publicas": "públicas", "accion": "acción",
    "apropiacion": "apropiación", "defraudacion": "defraudación", "evasion": "evasión",
    "promocion": "promoción", "administracion": "administración", "contratacion": "contratación",
    "seleccion": "selección", "licitacion": "licitación", "enajenacion": "enajenación",
    "minima": "mínima", "cuantia": "cuantía", "regimen": "régimen", "interes": "interés",
    "funcion": "función", "alcaldia": "alcaldía", "secretaria": "secretaría",
    "gobernacion": "gobernación", "educacion": "educación", "policia": "policía",
    "ejercito": "ejército", "fiscalia": "fiscalía", "defensoria": "defensoría",
    "proteccion": "protección", "restitucion": "restitución", "cancerologia": "cancerología",
    "petroleos": "petróleos", "electricas": "eléctricas", "contraloria": "contraloría",
    "procuraduria": "procuraduría", "bogota": "bogotá", "atlantico": "atlántico",
    "bolivar": "bolívar", "boyaca": "boyacá", "caqueta": "caquetá", "choco": "chocó",
    "cordoba": "córdoba", "guainia": "guainía", "narino": "nariño", "quindio": "quindío",
    "vaupes": "vaupés", "archipielago": "archipiélago", "andres": "andrés", "ano": "año",
    "medellin": "medellín", "cali": "Cali", "agrario": "agrario", "sancion": "sanción",
    "sanciones": "sanciones", "comision": "comisión", "direccion": "dirección",
    "penitenciario": "penitenciario", "union": "unión", "salud": "salud",
}
_RE_ACENTOS = re.compile(r"\b(" + "|".join(sorted(_ACENTOS, key=len, reverse=True)) + r")\b", re.IGNORECASE)


def acentuar(texto):
    """Devuelve el texto con las tildes de las palabras más comunes del Gold."""
    if not isinstance(texto, str):
        return texto

    def reemplazo(m):
        palabra = m.group(0)
        bueno = _ACENTOS[palabra.lower()]
        if palabra.isupper() and len(palabra) > 1:
            return bueno.upper()
        if palabra[0].isupper():
            return bueno[0].upper() + bueno[1:]
        return bueno

    return _RE_ACENTOS.sub(reemplazo, texto)


_MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "al", "para", "por"}
_SIGLAS = {"INPEC", "ESP", "ESE", "E.S.P.", "E.S.E.", "S.A.", "S.A", "EMCALI", "CEDELCA",
           "FERTICOL", "DC", "D.C.", "EPM", "SA", "E.S.P", "E.S.E"}


def titulo_legible(texto: str) -> str:
    """'ALCALDIA MUNICIPIO - JURADO (CHOCO)' -> 'Alcaldía Municipio - Jurado (Chocó)'."""
    if not isinstance(texto, str):
        return texto
    texto = acentuar(texto.strip())
    palabras = []
    for i, p in enumerate(texto.split()):
        limpio = p.strip("()-,")
        if limpio.upper() in _SIGLAS:
            palabras.append(p.upper() if limpio.upper() in _SIGLAS else p)
        elif limpio.lower() in _MINUSCULAS and i > 0:
            palabras.append(p.lower())
        else:
            palabras.append(p[:1].upper() + p[1:].lower() if p.isupper() or p.islower() else p)
    return " ".join(palabras)


def limpiar_departamento(nombre: str) -> str:
    n = sin_tildes(nombre).upper().strip()
    if n.startswith("BOGOTA"):
        return "Bogotá D.C."
    if n.startswith("ARCHIPIELAGO"):
        return "San Andrés y Providencia"
    return titulo_legible(nombre)


def unificar_entidad(nombre: str) -> str:
    """Une escrituras distintas de una misma entidad (p. ej. INPEC)."""
    n = sin_tildes(nombre).upper()
    if "INPEC" in n or "INSTITUTO NACIONAL PENITENCIARIO" in n:
        return "INPEC (Instituto Nacional Penitenciario y Carcelario)"
    if "ACUEDUCTO Y ALCANTARILLADO DE BOGOTA" in n or "ACUEEDUCTO Y ALCANTARILLADO DE BOGOTA" in n:
        return "Empresa de Acueducto y Alcantarillado de Bogotá"
    return titulo_legible(nombre)


_RE_FUERZA_PUBLICA = re.compile(
    r"POLIC|EJERCITO|FUERZAS? (PUBLICAS?|MILITARES?)|ARMADA|FUERZA AEREA|NAVAL|MILITAR", re.IGNORECASE
)


def es_fuerza_publica(nombre: str) -> bool:
    return bool(_RE_FUERZA_PUBLICA.search(sin_tildes(nombre)))


# Lectura de la capa Gold
def nombre_api(archivo: str) -> str:
    """Nombre del dataset en la API: 'fiscalia_procesos_año_capitulo_gold.csv' -> 'fiscalia_procesos_ano_capitulo'."""
    stem = Path(archivo).stem
    if stem.endswith("_gold"):
        stem = stem[:-5]
    return sin_tildes(stem).lower()


def _preparar(nombre: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].replace({"NO REGISTRADO": "Sin registrar"})
        if col == "entidad_sancionado":
            df[col] = df[col].map(unificar_entidad)
        elif col.startswith("departamento"):
            df[col] = df[col].map(limpiar_departamento)
        elif col == "entidad":
            df[col] = df[col].map(titulo_legible)
        else:
            df[col] = df[col].map(acentuar)
    if nombre == "procuraduria":
        df["fuerza_publica"] = df["entidad_sancionado"].map(es_fuerza_publica)
        df = df.groupby(["entidad_sancionado", "fuerza_publica"], as_index=False)["total_sanciones"].sum()
        df = df.sort_values("total_sanciones", ascending=False).reset_index(drop=True)
    return df


def leer_csv(nombre: str) -> pd.DataFrame:
    archivos = datasets()
    if nombre not in archivos:
        raise DatoNoDisponible(f"El dataset '{nombre}' no está definido en config.yaml.")
    ruta = ruta_gold() / archivos[nombre]
    if not ruta.exists():
        raise DatoNoDisponible(f"Falta {ruta.name}. Ejecute primero: python main.py")
    return pd.read_csv(ruta, encoding="utf-8")


def leer_api(nombre: str, timeout: float = 4.0) -> pd.DataFrame:
    import requests

    archivo = datasets().get(nombre)
    if archivo is None:
        raise DatoNoDisponible(f"El dataset '{nombre}' no está definido en config.yaml.")
    resp = requests.get(f"{api_url()}/gold/{nombre_api(archivo)}", timeout=timeout)
    resp.raise_for_status()
    return pd.DataFrame(resp.json()["Data"])


def cargar(nombre: str) -> pd.DataFrame:
    """Dataset Gold ya limpio. Usa la API si está configurada; si falla, el CSV."""
    df = None
    if fuente_datos() == "api":
        try:
            df = leer_api(nombre)
        except Exception:
            df = None
    if df is None:
        df = leer_csv(nombre)
    return _preparar(nombre, df)


def disponible(nombre: str) -> bool:
    try:
        return (ruta_gold() / datasets()[nombre]).exists()
    except KeyError:
        return False


# Estado del pipeline (para mostrar qué tan actuales son las cifras)
_RE_LINEA = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ \[INFO\]\s+(FISCAL\S*[^\n]*?|CONTRALOR\S*|PROCURADUR\S*|DATA WAREHOUSE)\s+(OK|FALL\S*)\s*$")


def estado_pipeline() -> dict:
    """Último resultado de cada módulo según logs/pipeline.log."""
    ruta = BASE_DIR / "logs" / "pipeline.log"
    estado: dict = {}
    if not ruta.exists():
        return estado
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _RE_LINEA.match(linea)
        if m:
            fecha, modulo, res = m.groups()
            modulo = titulo_legible(sin_tildes(modulo).replace("  ", " ").strip())
            estado[modulo] = {"ok": res == "OK", "fecha": datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")}
    return estado


def ultima_actualizacion() -> datetime | None:
    """Fecha de la última ejecución del ETL (log) o, si no hay log, del archivo Gold más nuevo."""
    est = estado_pipeline()
    if est:
        return max(v["fecha"] for v in est.values())
    archivos = list(ruta_gold().glob("*.csv")) if ruta_gold().exists() else []
    if archivos:
        return datetime.fromtimestamp(max(a.stat().st_mtime for a in archivos))
    return None


def proxima_actualizacion() -> datetime | None:
    ultima = ultima_actualizacion()
    horas = (cargar_config().get("execution", {}) or {}).get("schedule_interval_hours", 24)
    return ultima + timedelta(hours=horas) if ultima else None
