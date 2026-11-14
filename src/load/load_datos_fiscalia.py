"""Construcción de tablas Gold para Fiscalía y contratación SECOP."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import pandas as pd

TipoDataset = Literal["fiscalia", "secop"]


def generar_datos_gold(
    ruta_entrada: str | os.PathLike[str],
    ruta_salida: str | os.PathLike[str],
    tipo_dataset: TipoDataset,
) -> pd.DataFrame:
    """Agrega Silver a indicadores de análisis, sin exponer identificadores personales."""
    entrada = Path(ruta_entrada)
    if not entrada.is_file():
        raise FileNotFoundError(f"No existe el archivo Silver: {entrada}")

    df = pd.read_csv(entrada, encoding="utf-8")
    if df.empty:
        raise ValueError(f"Silver no contiene registros: {entrada}")

    if tipo_dataset == "fiscalia":
        agrupacion = [
            columna
            for columna in (
                "delito",
                "estado",
                "departamento_hecho_origen",
                "a_o_hecho_origen",
            )
            if columna in df.columns
        ]
        if not {"delito", "estado"}.issubset(agrupacion):
            raise ValueError("Silver de Fiscalía debe incluir delito y estado.")
        if "proceso_anonimizado" not in df.columns:
            raise ValueError("Silver de Fiscalía debe incluir proceso_anonimizado.")
        gold = (
            df.groupby(agrupacion, dropna=False)
            .agg(
                total_registros=("proceso_anonimizado", "size"),
                procesos_unicos=("proceso_anonimizado", "nunique"),
            )
            .reset_index()
        )
        gold = gold.sort_values(
            ["total_registros", "procesos_unicos"], ascending=False
        )
    elif tipo_dataset == "secop":
        agrupacion = [
            columna
            for columna in (
                "entidad",
                "modalidad_de_contratacion",
                "estado_del_procedimiento",
            )
            if columna in df.columns
        ]
        if not {"entidad", "estado_del_procedimiento"}.issubset(agrupacion):
            raise ValueError(
                "Silver de SECOP debe incluir entidad y estado_del_procedimiento."
            )
        if not {"id_del_proceso", "precio_base"}.issubset(df.columns):
            raise ValueError("Silver de SECOP debe incluir proceso y precio_base.")
        gold = (
            df.groupby(agrupacion, dropna=False)
            .agg(
                total_procesos=("id_del_proceso", "nunique"),
                precio_base_total=(
                    "precio_base",
                    lambda valores: valores.sum(min_count=1),
                ),
                precio_base_promedio=("precio_base", "mean"),
            )
            .reset_index()
        )
        gold = gold.sort_values("total_procesos", ascending=False)
    else:
        raise ValueError(f"Tipo de dataset no soportado: {tipo_dataset}")

    salida = Path(ruta_salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    gold.to_csv(salida, index=False, encoding="utf-8")
    return gold
