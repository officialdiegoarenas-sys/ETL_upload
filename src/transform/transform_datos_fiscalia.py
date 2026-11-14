"""Limpieza tipada y controles de calidad para Fiscalía y contratación SECOP."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from typing import Literal

import pandas as pd

TipoDataset = Literal["fiscalia", "secop"]

ESQUEMAS = {
    "fiscalia": {
        "requeridas": {"proceso_anonimizado", "delito", "estado", "etapa"},
        "numericas_enteras": {
            "deli_id",
            "a_o_hecho_origen",
            "mes_hecho_origen",
            "a_o_creacion_origen",
            "mes_creacion_origen",
        },
        "numericas": set(),
        "fechas": {"fecha_actualizacion_datos"},
    },
    "secop": {
        "requeridas": {
            "id_del_proceso",
            "entidad",
            "estado_del_procedimiento",
            "precio_base",
        },
        "numericas_enteras": {
            "duracion",
            "proveedores_invitados",
            "proveedores_con_invitacion",
            "visualizaciones_del",
            "proveedores_que_manifestaron",
            "respuestas_al_procedimiento",
            "respuestas_externas",
            "conteo_de_respuestas_a_ofertas",
            "proveedores_unicos_con",
            "numero_de_lotes",
            "id_estado_del_procedimiento",
        },
        "numericas": {"precio_base", "valor_total_adjudicacion"},
        "fechas": {
            "fecha_de_publicacion_del",
            "fecha_de_ultima_publicaci",
            "fecha_de_publicacion_fase_3",
        },
    },
}

_NULOS_TEXTUALES = {"", "nan", "none", "null", "<na>", "nat"}


def transformar_datos(
    ruta_entrada: str | os.PathLike[str],
    ruta_salida: str | os.PathLike[str],
    tipo_dataset: TipoDataset,
    ruta_calidad: str | os.PathLike[str],
) -> pd.DataFrame:
    """Genera Silver y un reporte de calidad; conserva categorías descriptivas."""
    if tipo_dataset not in ESQUEMAS:
        raise ValueError(f"Tipo de dataset no soportado: {tipo_dataset}")

    entrada = Path(ruta_entrada)
    if not entrada.is_file():
        raise FileNotFoundError(f"No existe el archivo Bronze: {entrada}")

    df = pd.read_json(entrada, orient="records", convert_dates=False)
    if df.empty:
        raise ValueError(f"El archivo Bronze no contiene registros: {entrada}")

    columnas_de_sistema = [col for col in df.columns if str(col).startswith(":")]
    df = df.drop(columns=columnas_de_sistema)
    df.columns = [_normalizar_nombre(col) for col in df.columns]
    if df.columns.duplicated().any():
        duplicadas = df.columns[df.columns.duplicated()].tolist()
        raise ValueError(f"Hay columnas duplicadas tras normalizar nombres: {duplicadas}")

    requeridas = ESQUEMAS[tipo_dataset]["requeridas"]
    faltantes = sorted(requeridas.difference(df.columns))
    if faltantes:
        raise ValueError(
            f"El esquema de {tipo_dataset} no contiene las columnas requeridas: "
            f"{', '.join(faltantes)}"
        )

    filas_entrada = len(df)
    nulos_entrada: dict[str, int] = {}
    for columna in df.columns:
        serie = df[columna].astype("string").str.strip()
        es_nulo_textual = serie.str.lower().isin(_NULOS_TEXTUALES)
        nulos_entrada[columna] = int((df[columna].isna() | es_nulo_textual).sum())
        df[columna] = serie.mask(es_nulo_textual, pd.NA)

    registros_vacios_eliminados = int(df.isna().all(axis=1).sum())
    df = df.dropna(how="all").copy()
    duplicados = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    filas_salida = len(df)

    valores_invalidos = {columna: 0 for columna in df.columns}
    esquema = ESQUEMAS[tipo_dataset]
    for columna in esquema["numericas_enteras"]:
        if columna not in df.columns:
            continue
        original = df[columna]
        numerica = pd.to_numeric(original, errors="coerce")
        fraccionarios = numerica.notna() & numerica.mod(1).ne(0)
        invalidos = original.notna() & (numerica.isna() | fraccionarios)
        valores_invalidos[columna] = int(invalidos.sum())
        df[columna] = numerica.mask(fraccionarios).astype("Int64")

    for columna in esquema["numericas"]:
        if columna not in df.columns:
            continue
        original = df[columna]
        numerica = pd.to_numeric(original, errors="coerce")
        valores_invalidos[columna] = int((original.notna() & numerica.isna()).sum())
        df[columna] = numerica.astype("Float64")

    for columna in esquema["fechas"]:
        if columna not in df.columns:
            continue
        original = df[columna]
        fecha = pd.to_datetime(
            original, errors="coerce", dayfirst=True, format="mixed", utc=True
        )
        valores_invalidos[columna] = int((original.notna() & fecha.isna()).sum())
        df[columna] = fecha.dt.strftime("%Y-%m-%d").astype("string")
        df[columna] = df[columna].mask(fecha.isna(), pd.NA)

    reporte = pd.DataFrame(
        [
            {
                "dataset": tipo_dataset,
                "columna": columna,
                "filas_entrada": filas_entrada,
                "filas_silver": filas_salida,
                "registros_vacios_eliminados": registros_vacios_eliminados,
                "duplicados_eliminados": duplicados,
                "nulos_entrada": nulos_entrada[columna],
                "nulos_silver": int(df[columna].isna().sum()),
                "valores_invalidos": valores_invalidos[columna],
            }
            for columna in df.columns
        ]
    )

    salida = Path(ruta_salida)
    calidad = Path(ruta_calidad)
    salida.parent.mkdir(parents=True, exist_ok=True)
    calidad.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False, encoding="utf-8")
    reporte.to_csv(calidad, index=False, encoding="utf-8")
    return df


def _normalizar_nombre(nombre: object) -> str:
    texto = unicodedata.normalize("NFKD", str(nombre))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto.strip().lower())
    return texto.strip("_")
