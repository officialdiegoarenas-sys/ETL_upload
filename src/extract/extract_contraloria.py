"""Extracción del dataset de la Contraloría desde la API de datos.gov.co (con soporte para CSV local)."""

from __future__ import annotations

import os
import pandas as pd
import requests

URL_API_CONTRALORIA = "https://www.datos.gov.co/resource/wasc-xi4h.json?$limit=5000"


def _cargar_desde_api(url_api: str) -> pd.DataFrame:
    """Descarga los registros JSON de la Contraloría desde la API de datos.gov.co."""
    respuesta = requests.get(url_api, timeout=30)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, list) or not all(isinstance(fila, dict) for fila in datos):
        raise ValueError("La API de Contraloría no devolvió una lista de registros JSON.")
    if not datos:
        raise ValueError("La API de Contraloría no devolvió registros.")
    return pd.DataFrame(datos)


def extraer_datos_contraloria(
    ruta_fuente: str = URL_API_CONTRALORIA,
    ruta_salida: str = "data/bronze/contraloria_raw.csv",
) -> pd.DataFrame:
    """Extrae desde la API de datos.gov.co o desde un CSV local si se indica una ruta existente.

    Normaliza la salida de Bronze reemplazando nulos y textos vacíos por
    ``DESCONOCIDO`` y genera el reporte de calidad en ``data/quality``.
    """
    es_url = isinstance(ruta_fuente, str) and ruta_fuente.startswith(("http://", "https://"))

    if es_url:
        df = _cargar_desde_api(ruta_fuente)
    elif ruta_fuente and os.path.isfile(ruta_fuente):
        try:
            df = pd.read_csv(ruta_fuente, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(ruta_fuente, encoding="latin-1")
    else:
        # Si no existe el archivo local, extrae directamente de la API de Datos Abiertos
        url_fallback = os.environ.get("CONTRALORIA_API_URL", URL_API_CONTRALORIA)
        df = _cargar_desde_api(url_fallback)

    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    filas_originales = len(df)
    columnas_originales = list(df.columns)
    df = df.dropna(how="all").copy()
    reporte = []
    for columna in df.columns:
        vacios = df[columna].isna() | df[columna].astype(str).str.strip().eq("")
        cantidad = int(vacios.sum())
        df.loc[vacios, columna] = "DESCONOCIDO"
        reporte.append(
            {
                "columna": columna,
                "filas_evaluadas": len(df),
                "valores_desconocidos_reemplazados": cantidad,
                "valores_desconocidos_finales": int(
                    df[columna].astype(str).str.strip().eq("DESCONOCIDO").sum()
                ),
            }
        )

    df.to_csv(ruta_salida, index=False, encoding="utf-8")
    calidad_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(ruta_salida)))),
        "quality",
    )
    os.makedirs(calidad_dir, exist_ok=True)
    calidad_path = os.path.join(calidad_dir, "contraloria_quality.csv")
    pd.DataFrame(reporte).to_csv(calidad_path, index=False, encoding="utf-8")
    print(
        f"Calidad Contraloría: {filas_originales} filas recibidas, "
        f"{len(df)} filas válidas, {len(columnas_originales)} columnas evaluadas."
    )
    print(f"Reporte de calidad: {calidad_path}")
    return df


if __name__ == "__main__":
    extraer_datos_contraloria(URL_API_CONTRALORIA, "data/bronze/contraloria_raw.csv")
