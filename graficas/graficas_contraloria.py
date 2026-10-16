"""Genera un resumen exploratorio y gráficas del archivo de Contraloría.

Uso desde la raíz del repositorio:
    python graficas/graficas_contraloria.py "ruta/al/archivo.csv"

Las figuras se guardan en ``graficas/contraloria`` y el informe en la raíz.
"""

from __future__ import annotations

import argparse
import re
import textwrap
import unicodedata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


HALLAZGOS = {
    "Hallazgos administrativos": "hallazgos_administrativos",
    "Hallazgos disciplinarios": "hallazgos_disciplinarios",
    "Hallazgos fiscales": "hallazgos_fiscales",
    "Hallazgos penales": "hallazgos_penales",
}
PALETA = ["#1F5A85", "#2F7E79", "#D39B36", "#B75C4B"]


def normalizar_nombre(nombre: object) -> str:
    texto = unicodedata.normalize("NFKD", str(nombre))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto.strip().lower())
    return texto.strip("_")


def leer_datos(ruta: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(ruta, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(ruta, encoding="latin-1")
    df = df.dropna(how="all").drop_duplicates().copy()
    df.columns = [normalizar_nombre(c) for c in df.columns]
    requeridas = {"sujeto_auditado", "vigencia", "cuantia", *HALLAZGOS.values()}
    faltantes = sorted(requeridas.difference(df.columns))
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas en el CSV: {', '.join(faltantes)}")

    for columna in HALLAZGOS.values():
        df[columna] = pd.to_numeric(df[columna], errors="coerce").fillna(0)
    df["vigencia"] = pd.to_numeric(df["vigencia"], errors="coerce")
    df["cuantia"] = df["cuantia"].map(parsear_moneda)
    df["sujeto_auditado"] = (
        df["sujeto_auditado"].fillna("NO REGISTRADO").astype(str).str.strip()
    )
    if "modalidad_de_auditoria" not in df:
        df["modalidad_de_auditoria"] = "NO REGISTRADA"
    df["modalidad_de_auditoria"] = (
        df["modalidad_de_auditoria"].fillna("NO REGISTRADA").astype(str).str.strip()
    )
    df["total_hallazgos"] = df[list(HALLAZGOS.values())].sum(axis=1)
    return df


def parsear_moneda(valor: object) -> float:
    if pd.isna(valor):
        return 0.0
    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if texto in {"", "-", "-0"}:
        return 0.0
    # El archivo fuente publica los montos con coma como separador de miles.
    texto = texto.replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def formato_cop(valor: float) -> str:
    return "$" + f"{valor:,.0f}".replace(",", ".")


def crear_graficas(df: pd.DataFrame, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "axes.titlesize": 15, "axes.labelsize": 11}
    )

    # 1. Comparación directa de los tipos de hallazgo.
    totales = pd.Series(
        {etiqueta: df[columna].sum() for etiqueta, columna in HALLAZGOS.items()}
    ).sort_values()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.barh(totales.index, totales.values, color=PALETA)
    ax.bar_label(bars, labels=[f"{v:,.0f}".replace(",", ".") for v in totales], padding=6)
    ax.set_title("Hallazgos reportados por tipo")
    ax.set_xlabel("Cantidad acumulada de hallazgos")
    ax.set_ylabel("")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destino / "01_hallazgos_por_tipo.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 2. Entidades con más hallazgos acumulados (etiquetas legibles en horizontal).
    entidad = df.groupby("sujeto_auditado")["total_hallazgos"].sum().nlargest(10).sort_values()
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(entidad.index, entidad.values, color="#1F5A85")
    ax.bar_label(bars, labels=[f"{v:,.0f}".replace(",", ".") for v in entidad], padding=5)
    ax.set_title("10 sujetos auditados con más hallazgos acumulados")
    ax.set_xlabel("Hallazgos acumulados en los registros del archivo")
    ax.set_ylabel("")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destino / "02_top_sujetos_por_hallazgos.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 3. Cuantía reportada por vigencia, independiente del conteo de hallazgos.
    por_vigencia = df.dropna(subset=["vigencia"]).groupby("vigencia")["cuantia"].sum()
    por_vigencia = por_vigencia[por_vigencia > 0].sort_index()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(por_vigencia.index.astype(int).astype(str), por_vigencia.values, color="#2F7E79")
    ax.set_title("Cuantía fiscal reportada por vigencia")
    ax.set_xlabel("Vigencia")
    ax.set_ylabel("Cuantía acumulada (COP)")
    ax.ticklabel_format(axis="y", style="plain")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"${x / 1e9:.0f} mil millones")
    )
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destino / "03_cuantia_por_vigencia.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 4. Hallazgos por vigencia para distinguir volumen de cuantía.
    hallazgos_vigencia = (
        df.dropna(subset=["vigencia"])
        .groupby("vigencia")["total_hallazgos"]
        .sum()
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(hallazgos_vigencia.index.astype(int).astype(str), hallazgos_vigencia.values, color="#D39B36")
    ax.set_title("Hallazgos acumulados por vigencia")
    ax.set_xlabel("Vigencia")
    ax.set_ylabel("Cantidad acumulada de hallazgos")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destino / "04_hallazgos_por_vigencia.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 5. Modalidades con más registros y hallazgos asociados.
    modalidad = (
        df.groupby("modalidad_de_auditoria")
        .agg(registros=("total_hallazgos", "size"), hallazgos=("total_hallazgos", "sum"))
        .sort_values("registros", ascending=False)
        .head(10)
        .sort_values("registros")
    )
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(modalidad.index, modalidad["registros"], color="#B75C4B", label="Registros")
    ax.set_yticks(range(len(modalidad.index)))
    ax.set_yticklabels([textwrap.fill(str(label), width=28) for label in modalidad.index])
    ax.set_title("Registros por modalidad de auditoría")
    ax.set_xlabel("Cantidad de registros")
    ax.set_ylabel("")
    ax.bar_label(ax.containers[0], padding=4)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(destino / "05_registros_por_modalidad.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def crear_informe(df: pd.DataFrame, ruta: Path, archivo_fuente: str) -> None:
    total_hallazgos = int(df["total_hallazgos"].sum())
    registros_con_hallazgos = int(df["total_hallazgos"].gt(0).sum())
    por_tipo = {etiqueta: int(df[columna].sum()) for etiqueta, columna in HALLAZGOS.items()}
    por_vigencia_h = df.groupby("vigencia")["total_hallazgos"].sum().dropna()
    por_vigencia_c = df.groupby("vigencia")["cuantia"].sum().dropna()
    por_sujeto_h = df.groupby("sujeto_auditado")["total_hallazgos"].sum()
    por_sujeto_c = df.groupby("sujeto_auditado")["cuantia"].sum()
    por_modalidad = df.groupby("modalidad_de_auditoria").agg(
        registros=("total_hallazgos", "size"), hallazgos=("total_hallazgos", "sum")
    )
    modalidad_top = por_modalidad.sort_values("registros", ascending=False).iloc[0]
    vigencia_top_h = por_vigencia_h.idxmax() if not por_vigencia_h.empty else "No disponible"
    vigencia_top_c = por_vigencia_c.idxmax() if not por_vigencia_c.empty else "No disponible"
    sujeto_top_h = por_sujeto_h.idxmax() if not por_sujeto_h.empty else "No disponible"
    sujeto_top_c = por_sujeto_c.idxmax() if not por_sujeto_c.empty else "No disponible"
    cantidad_con_cuantia = int(df["cuantia"].gt(0).sum())
    hallazgos_formateados = f"{total_hallazgos:,}".replace(",", ".")
    registros_formateados = f"{registros_con_hallazgos:,}".replace(",", ".")
    porcentaje_con_hallazgos = f"{registros_con_hallazgos / len(df) * 100:.1f}".replace(".", ",")
    registros_con_cuantia_formateados = f"{cantidad_con_cuantia:,}".replace(",", ".")
    filas_formateadas = f"{len(df):,}".replace(",", ".")
    sujetos_formateados = f"{df['sujeto_auditado'].nunique():,}".replace(",", ".")

    lineas = [
        "# Análisis exploratorio de Contraloría",
        "",
        f"**Fuente:** `{archivo_fuente}`. Se analizaron {filas_formateadas} registros y "
        f"{sujetos_formateados} sujetos auditados distintos, después de retirar "
        "filas vacías y duplicados exactos.",
        "",
        "## Hallazgos principales",
        "",
        f"- Se acumulan **{hallazgos_formateados} hallazgos**; "
        f"{registros_formateados} registros ({porcentaje_con_hallazgos}%) reportan al menos uno.",
        "- Composición: " + "; ".join(
            f"{nombre.lower()}: **{valor:,}**".replace(",", ".") for nombre, valor in por_tipo.items()
        ) + ".",
        f"- La entidad con mayor suma de hallazgos es **{sujeto_top_h}** "
        f"({int(por_sujeto_h.loc[sujeto_top_h]):,}).".replace(",", "."),
        f"- La mayor cuantía acumulada por sujeto corresponde a **{sujeto_top_c}** "
        f"({formato_cop(float(por_sujeto_c.loc[sujeto_top_c]))}).",
        f"- La vigencia con más hallazgos es **{vigencia_top_h}** "
        f"({int(por_vigencia_h.loc[vigencia_top_h]):,}); la mayor cuantía reportada corresponde a "
        f"**{vigencia_top_c}** ({formato_cop(float(por_vigencia_c.loc[vigencia_top_c]))}).".replace(",", "."),
        f"- La modalidad con más registros es **{modalidad_top.name}** "
        f"({int(modalidad_top['registros']):,} registros; {int(modalidad_top['hallazgos']):,} hallazgos).".replace(",", "."),
        f"- La cuantía acumulada del archivo es **{formato_cop(float(df['cuantia'].sum()))}**; "
        f"{registros_con_cuantia_formateados} registros con valor mayor que cero reportan cuantía.",
        "",
        "## Gráficas",
        "",
        "1. `graficas/contraloria/01_hallazgos_por_tipo.png`: composición por tipo.",
        "2. `graficas/contraloria/02_top_sujetos_por_hallazgos.png`: sujetos con más hallazgos acumulados.",
        "3. `graficas/contraloria/03_cuantia_por_vigencia.png`: cuantía fiscal reportada por vigencia.",
        "4. `graficas/contraloria/04_hallazgos_por_vigencia.png`: hallazgos acumulados por vigencia.",
        "5. `graficas/contraloria/05_registros_por_modalidad.png`: registros por modalidad de auditoría.",
        "",
        "### Hallazgos por tipo",
        "",
        "![Hallazgos reportados por tipo](graficas/contraloria/01_hallazgos_por_tipo.png)",
        "",
        "### Sujetos auditados con más hallazgos",
        "",
        "![Top de sujetos auditados por hallazgos](graficas/contraloria/02_top_sujetos_por_hallazgos.png)",
        "",
        "### Cuantía fiscal reportada por vigencia",
        "",
        "![Cuantía fiscal por vigencia](graficas/contraloria/03_cuantia_por_vigencia.png)",
        "",
        "### Hallazgos por vigencia",
        "",
        "![Hallazgos por vigencia](graficas/contraloria/04_hallazgos_por_vigencia.png)",
        "",
        "### Registros por modalidad de auditoría",
        "",
        "![Registros por modalidad](graficas/contraloria/05_registros_por_modalidad.png)",
        "",
        "## Alcance e interpretación",
        "",
        "Los conteos y las cuantías son descriptivos del archivo analizado. Una fila puede representar "
        "un registro de auditoría y no necesariamente un caso independiente; los montos reportados no "
        "equivalen por sí solos a dinero recuperado ni probado como detrimento. Los valores sirven para "
        "orientar una revisión de los informes fuente y no establecen responsabilidad jurídica.",
        "",
    ]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="Ruta al CSV de resultados de Contraloría")
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).resolve().parent / "contraloria",
        help="Carpeta de salida de las gráficas (por defecto: graficas/contraloria)",
    )
    parser.add_argument(
        "--report", type=Path, default=None,
        help="Ruta opcional para generar un informe Markdown resumido",
    )
    args = parser.parse_args()
    df = leer_datos(args.csv)
    crear_graficas(df, args.output_dir)
    if args.report:
        crear_informe(df, args.report, args.csv.name)
        print(f"Informe guardado en: {args.report}")
    print(f"Análisis terminado: {len(df)} registros.")
    print(f"Gráficas guardadas en: {args.output_dir}")


if __name__ == "__main__":
    main()
