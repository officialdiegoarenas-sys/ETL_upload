"""Extracción del dataset de la Contraloría desde la API de datos.gov.co."""

from __future__ import annotations

import os

import pandas as pd
import requests


def extraer_datos_contraloria(url_api: str, ruta_salida: str) -> pd.DataFrame:
    """Descarga el JSON de Contraloría, guarda Bronze y genera el reporte de calidad."""
    respuesta = requests.get(url_api, timeout=30)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, list) or not all(isinstance(fila, dict) for fila in datos):
        raise ValueError("La API de Contraloría no devolvió una lista de registros JSON.")
    if not datos:
        raise ValueError("La API de Contraloría no devolvió registros.")

    df = pd.DataFrame(datos)
    carpeta_salida = os.path.dirname(ruta_salida)
    if carpeta_salida:
        os.makedirs(carpeta_salida, exist_ok=True)

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
        os.path.dirname(os.path.dirname(os.path.dirname(ruta_salida))), "quality"
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
