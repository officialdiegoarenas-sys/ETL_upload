import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LogNorm

CARPETA = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(CARPETA, "..", "data", "gold")

plt.style.use("ggplot")


def guardar(nombre):
    plt.tight_layout()
    plt.savefig(os.path.join(CARPETA, nombre), dpi=150)
    plt.close()
    print(f"Grafica guardada: {nombre}")


def tendencia_anual():
    df = pd.read_csv(os.path.join(GOLD, "fiscalia_procesos_año_capitulo_gold.csv"))
    tabla = df.pivot_table(index="año_creacion", columns="capitulo_delito", values="total_procesos", aggfunc="sum").fillna(0)
    top = tabla.sum().sort_values(ascending=False).head(5).index

    _, ax = plt.subplots(figsize=(11, 5))
    tabla[top].plot(ax=ax, marker="o")
    ax.axvspan(2025.5, 2026.5, color="grey", alpha=0.15, label="2026 (corte parcial)")
    ax.set_title("Procesos por año de creación - 5 capítulos con más procesos")
    ax.set_xlabel("Año")
    ax.set_ylabel("Procesos")
    ax.set_xticks(tabla.index)
    ax.legend(fontsize=8)
    guardar("tendencia_anual_capitulos.jpg")


def heatmap_año_capitulo():
    df = pd.read_csv(os.path.join(GOLD, "fiscalia_procesos_año_capitulo_gold.csv"))
    df = df[df["capitulo_delito"] != "NO REGISTRADO"]
    tabla = df.pivot_table(index="capitulo_delito", columns="año_creacion", values="total_procesos", aggfunc="sum").fillna(0)
    tabla = tabla.loc[tabla.sum(axis=1).sort_values(ascending=False).index]
    tabla.index = [c[:45] for c in tabla.index]

    plt.figure(figsize=(14, 6))
    sns.heatmap(tabla + 1, cmap="YlOrRd", linewidths=0.3, norm=LogNorm())
    plt.title("Procesos por capítulo y año (color en escala logarítmica)")
    plt.xticks(rotation=45)
    plt.xlabel("Año de creación")
    plt.ylabel("")
    guardar("heatmap_capitulo_año.jpg")


def departamentos():
    df = pd.read_csv(os.path.join(GOLD, "fiscalia_procesos_departamento_gold.csv")).head(15)

    _, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["departamento_hecho"], df["total_procesos"], color="steelblue")
    for i, (total, pct) in enumerate(zip(df["total_procesos"], df["pct_activos"])):
        ax.text(total, i, f" {pct}% activos", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Top 15 departamentos por número de procesos")
    ax.set_xlabel("Procesos")
    guardar("top_departamentos.jpg")


def tasa_condena():
    df = pd.read_csv(os.path.join(GOLD, "fiscalia_procesados_sentencias_gold.csv"))
    df = df[(df["total_procesados"] >= 1000) & (df["capitulo_delito"] != "NO REGISTRADO")]
    df = df.sort_values("pct_condena")

    _, ax = plt.subplots(figsize=(10, 5))
    ax.barh(df["capitulo_delito"], df["pct_condena"], color="indianred")
    for i, (pct, cond) in enumerate(zip(df["pct_condena"], df["condenados"])):
        ax.text(pct, i, f" {pct}% ({cond:,})", va="center", fontsize=8)
    ax.set_title("Porcentaje de procesados condenados por capítulo")
    ax.set_xlabel("% condenados")
    guardar("tasa_condena_capitulo.jpg")


def etapas():
    df = pd.read_csv(os.path.join(GOLD, "fiscalia_procesos_etapa_gold.csv"))
    tabla = df.pivot_table(index="etapa", columns="estado", values="total", aggfunc="sum").fillna(0)
    tabla = tabla.loc[["Indagación", "Investigación", "Juicio", "Ejecución De Penas"]]

    _, ax = plt.subplots(figsize=(9, 5))
    tabla.plot(kind="bar", ax=ax, color=["#4c72b0", "#c0c0c0"])
    ax.set_yscale("log")
    ax.set_title("Procesos por etapa y estado (escala logarítmica)")
    ax.set_xlabel("")
    ax.set_ylabel("Registros")
    plt.xticks(rotation=0)
    guardar("procesos_por_etapa.jpg")


if __name__ == "__main__":
    tendencia_anual()
    heatmap_año_capitulo()
    departamentos()
    tasa_condena()
    etapas()
