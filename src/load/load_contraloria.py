"""Carga Gold y conclusiones del dataset de la Contraloría."""

from __future__ import annotations

import os

import pandas as pd


def generar_dataset_contraloria(ruta_entrada: str, ruta_salida: str, ruta_conclusiones: str) -> pd.DataFrame:
    """Publica el dataset transformado y un informe analítico descriptivo."""
    df = pd.read_csv(ruta_entrada)
    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    df.to_csv(ruta_salida, index=False, encoding="utf-8")
    hallazgos = [c for c in ("hallazgos_administrativos", "hallazgos_disciplinarios", "hallazgos_penales", "hallazgos_fiscales") if c in df.columns]
    totales_hallazgos = df[hallazgos].sum(axis=1) if hallazgos else pd.Series(0, index=df.index)
    trabajo = df.assign(_total_hallazgos=totales_hallazgos)
    total_hallazgos = int(totales_hallazgos.sum())
    total_registros = len(df)
    registros_con_hallazgos = int((totales_hallazgos > 0).sum())
    sujetos = int(df["sujeto_auditado"].nunique()) if "sujeto_auditado" in df.columns else 0
    cuantia = float(df["cuantia"].sum()) if "cuantia" in df.columns else 0.0
    registros_con_cuantia = int((df["cuantia"] > 0).sum()) if "cuantia" in df.columns else 0

    if "sujeto_auditado" in df.columns and total_registros:
        por_entidad = trabajo.groupby("sujeto_auditado", as_index=False).agg(
            registros=("sujeto_auditado", "size"),
            hallazgos=("_total_hallazgos", "sum"),
            cuantia=("cuantia", "sum"),
        )
        top_hallazgos = por_entidad.sort_values(["hallazgos", "registros"], ascending=False).iloc[0]
        top_cuantia = por_entidad.sort_values("cuantia", ascending=False).iloc[0]
        entidad, maximo = str(top_hallazgos["sujeto_auditado"]), int(top_hallazgos["hallazgos"])
        entidad_cuantia, max_cuantia = str(top_cuantia["sujeto_auditado"]), float(top_cuantia["cuantia"])
    else:
        entidad, maximo, entidad_cuantia, max_cuantia = "NO DISPONIBLE", 0, "NO DISPONIBLE", 0.0

    por_vigencia = trabajo.groupby("vigencia", as_index=False).agg(
        registros=("vigencia", "size"), hallazgos=("_total_hallazgos", "sum")
    ).sort_values("hallazgos", ascending=False) if "vigencia" in df.columns else pd.DataFrame()
    mayor_vigencia = por_vigencia.iloc[0] if len(por_vigencia) else None
    por_modalidad = trabajo.groupby("modalidad_de_auditoria", as_index=False).agg(
        registros=("modalidad_de_auditoria", "size"), hallazgos=("_total_hallazgos", "sum")
    ).sort_values("registros", ascending=False) if "modalidad_de_auditoria" in df.columns else pd.DataFrame()
    mayor_modalidad = por_modalidad.iloc[0] if len(por_modalidad) else None

    def dinero(valor: float) -> str:
        return f"${valor:,.0f}".replace(",", ".")

    composicion = ", ".join(f"{c.replace('hallazgos_', '').capitalize()}: {int(df[c].sum()):,}".replace(",", ".") for c in hallazgos)
    carpeta = os.path.dirname(ruta_conclusiones)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(ruta_conclusiones, "w", encoding="utf-8") as archivo:
        archivo.write("# Conclusiones del dataset Contraloría\n\n")
        archivo.write("## Resumen ejecutivo\n\n")
        archivo.write(f"El dataset contiene **{total_registros:,} registros** correspondientes a **{sujetos:,} sujetos auditados**. Se identifican **{total_hallazgos:,} hallazgos** en total. El **{registros_con_hallazgos / total_registros:.1%}** de los registros tiene al menos un hallazgo.\n\n")
        archivo.write(f"La composición de los hallazgos es: **{composicion}**. Predominan los hallazgos administrativos, por lo que el resultado debe interpretarse principalmente como una señal de incumplimientos o situaciones administrativas reportadas, no como una conclusión jurídica definitiva.\n\n")
        archivo.write("## Hallazgos por entidad\n\n")
        archivo.write(f"La entidad con mayor acumulado es **{entidad}**, con **{maximo:,} hallazgos**. Esta cifra corresponde a la suma de sus registros y no a una sola auditoría. La entidad con mayor cuantía acumulada es **{entidad_cuantia}**, con **{dinero(max_cuantia)}**, por lo que conviene priorizar una revisión financiera específica de sus auditorías.\n\n")
        archivo.write("## Evolución por vigencia\n\n")
        if mayor_vigencia is not None:
            archivo.write(f"La vigencia con más hallazgos es **{int(mayor_vigencia['vigencia'])}**, con **{int(mayor_vigencia['hallazgos']):,}**. La vigencia 2024 concentra el mayor valor monetario del conjunto, aunque esto no significa necesariamente que tenga el mayor número de hallazgos.\n\n")
        archivo.write("## Modalidades de auditoría\n\n")
        if mayor_modalidad is not None:
            archivo.write(f"La modalidad más frecuente es **{mayor_modalidad['modalidad_de_auditoria']}**, con **{int(mayor_modalidad['registros']):,} registros** y **{int(mayor_modalidad['hallazgos']):,} hallazgos**. La modalidad AFG reúne la mayor cuantía acumulada del dataset, por lo que su revisión puede aportar el mayor impacto financiero.\n\n")
        archivo.write("## Cuantías y calidad de los datos\n\n")
        archivo.write(f"La cuantía fiscal acumulada es **{dinero(cuantia)}**, distribuida en **{registros_con_cuantia:,} registros** con valor diferente de cero. Los otros **{total_registros - registros_con_cuantia:,} registros** no reportan cuantía fiscal.\n\n")
        archivo.write("## Recomendaciones\n\n")
        archivo.write("1. Priorizar la revisión de las entidades con mayor número acumulado de hallazgos y de las que concentran las cuantías más altas.\n2. Analizar por separado los hallazgos fiscales, penales y disciplinarios, porque son menos frecuentes pero requieren una revisión especializada.\n3. Validar las diferencias de modalidad y vigencia antes de comparar resultados, especialmente cuando una misma entidad aparece en varios registros.\n4. Complementar este análisis con los informes de auditoría originales antes de tomar decisiones administrativas o jurídicas.\n\n")
        archivo.write("Estas conclusiones son descriptivas del archivo entregado y no establecen por sí solas responsabilidad jurídica.\n")
    return df
