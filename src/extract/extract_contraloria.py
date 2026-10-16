"""Extracción local del dataset de la Contraloría sin modificar el original."""

from __future__ import annotations

import os
import pandas as pd


def extraer_datos_contraloria(ruta_fuente: str, ruta_salida: str) -> pd.DataFrame:
    """Extrae, valida y deja documentados los valores desconocidos.

    El archivo fuente nunca se modifica. La salida de Bronze sí se normaliza:
    los nulos y textos vacíos se reemplazan por ``DESCONOCIDO`` y se genera un
    reporte de calidad junto a la carpeta ``data/quality``.
    """
    if not os.path.isfile(ruta_fuente):
        raise FileNotFoundError(f"No existe el dataset fuente: {ruta_fuente}")
    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    try:
        df = pd.read_csv(ruta_fuente, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(ruta_fuente, encoding="latin-1")

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
    calidad_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(ruta_salida))), "quality")
    os.makedirs(calidad_dir, exist_ok=True)
    calidad_path = os.path.join(calidad_dir, "contraloria_quality.csv")
    pd.DataFrame(reporte).to_csv(calidad_path, index=False, encoding="utf-8")
    print(
        f"Calidad Contraloría: {filas_originales} filas leídas, "
        f"{len(df)} filas válidas, {len(columnas_originales)} columnas evaluadas."
    )
    print(f"Reporte de calidad: {calidad_path}")
    return df
