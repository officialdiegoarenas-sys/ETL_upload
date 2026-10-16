"""Transformación del dataset de la Contraloría."""

from __future__ import annotations

import os
import re

import pandas as pd


def _nombre_columna(nombre: str) -> str:
    texto = re.sub(r"[^a-z0-9áéíóúüñ]+", "_", str(nombre).strip().lower())
    return (texto.strip("_").replace("á", "a").replace("é", "e")
            .replace("í", "i").replace("ó", "o").replace("ú", "u")
            .replace("ü", "u").replace("ñ", "n"))


def _numero_moneda(valor: object) -> float:
    if pd.isna(valor):
        return 0.0
    texto = str(valor).replace("$", "").replace(" ", "").replace(",", "")
    return 0.0 if texto in {"", "-", "-0"} else float(texto)


def transformar_datos_contraloria(ruta_entrada: str, ruta_salida: str) -> pd.DataFrame:
    """Limpia nombres, duplicados y tipos en una salida separada del original."""
    try:
        df = pd.read_csv(ruta_entrada, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(ruta_entrada, encoding="latin-1")
    df = df.dropna(how="all").drop_duplicates().copy()
    df.columns = [_nombre_columna(columna) for columna in df.columns]
    if "sujeto_auditado" in df.columns:
        df["sujeto_auditado"] = df["sujeto_auditado"].fillna("NO REGISTRADO").astype(str).str.strip()
    for columna in ("hallazgos_administrativos", "hallazgos_disciplinarios", "hallazgos_penales", "hallazgos_fiscales"):
        if columna in df.columns:
            df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0).astype(int)
    if "cuantia" in df.columns:
        df["cuantia"] = df["cuantia"].map(_numero_moneda)
    if "vigencia" in df.columns:
        df["vigencia"] = pd.to_numeric(df["vigencia"], errors="coerce").astype("Int64")
    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    df.to_csv(ruta_salida, index=False, encoding="utf-8")
    return df

