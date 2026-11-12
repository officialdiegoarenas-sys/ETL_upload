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


def tendencia_anual_corrupcion():
    df = pd.read_csv(os.path.join(GOLD, "policia_capturas_año_capitulo_gold.csv"))
    df = df[df["capitulo_delito"] != "De Los Delitos Contra Los Servidores Publicos"]
    tabla = df.pivot_table(
        index="año_hecho",
        columns="capitulo_delito",
        values="total_capturas",
        aggfunc="sum",
    ).fillna(0)
    top = tabla.sum().sort_values(ascending=False).head(5).index

    _, ax = plt.subplots(figsize=(11, 5))
    tabla[top].plot(ax=ax, marker="o")
    ax.axvspan(2025.5, 2026.5, color="grey", alpha=0.15, label="2026 (corte parcial)")
    ax.set_title("Capturas Policía Nacional por año - Top 5 capítulos de corrupción")
    ax.set_xlabel("Año del hecho")
    ax.set_ylabel("Capturas")
    ax.set_xticks(tabla.index)
    ax.legend(fontsize=8)
    guardar("policia_tendencia_anual_corrupcion.jpg")


def heatmap_año_capitulo():
    df = pd.read_csv(os.path.join(GOLD, "policia_capturas_año_capitulo_gold.csv"))
    df = df[df["capitulo_delito"] != "NO REGISTRADO"]
    tabla = df.pivot_table(
        index="capitulo_delito",
        columns="año_hecho",
        values="total_capturas",
        aggfunc="sum",
    ).fillna(0)
    tabla = tabla.loc[tabla.sum(axis=1).sort_values(ascending=False).index]
    tabla.index = [c[:45] for c in tabla.index]

    plt.figure(figsize=(14, 6))
    sns.heatmap(tabla + 1, cmap="YlOrRd", linewidths=0.3, norm=LogNorm())
    plt.title("Capturas Policía por capítulo y año (color en escala logarítmica)")
    plt.xticks(rotation=45)
    plt.xlabel("Año del hecho")
    plt.ylabel("")
    guardar("policia_heatmap_capitulo_año.jpg")


def top_departamentos():
    df = pd.read_csv(os.path.join(GOLD, "policia_capturas_departamento_gold.csv"))
    df = df.sort_values("capturas_corrupcion", ascending=False).head(15)

    _, ax = plt.subplots(figsize=(10, 6))
    ax.barh(df["departamento_hecho"], df["capturas_corrupcion"], color="steelblue")
    for i, (corr, pct) in enumerate(zip(df["capturas_corrupcion"], df["pct_corrupcion"])):
        ax.text(corr, i, f" {corr:,} ({pct}% del depto)", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Top 15 departamentos por capturas de corrupción y función pública")
    ax.set_xlabel("Capturas por corrupción (excl. Art. 429-430)")
    guardar("policia_top_departamentos.jpg")


def top_delitos_corrupcion():
    df = pd.read_csv(os.path.join(GOLD, "policia_top_delitos_gold.csv"))
    df = df[df["categoria_delito"] == "Corrupcion Y Funcion Publica"].head(10)
    etiquetas = [f"Art. {a} - {d[:38]}" for a, d in zip(df["articulo"], df["delito"])]

    _, ax = plt.subplots(figsize=(11, 5))
    ax.barh(etiquetas, df["total_capturas"], color="indianred")
    for i, total in enumerate(df["total_capturas"]):
        ax.text(total, i, f" {total:,}", va="center", fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Top 10 delitos de corrupción y contratación con más capturas (DIJIN)")
    ax.set_xlabel("Total capturas")
    guardar("policia_top_delitos_corrupcion.jpg")


def perfil_capturados():
    df = pd.read_csv(os.path.join(GOLD, "policia_perfil_capturados_gold.csv"))
    df_corr = df[df["categoria_delito"] == "Corrupcion Y Funcion Publica"]
    tabla = df_corr.pivot_table(
        index="grupo_etario",
        columns="genero",
        values="total_capturas",
        aggfunc="sum",
    ).fillna(0)

    _, ax = plt.subplots(figsize=(8, 5))
    tabla.plot(kind="bar", ax=ax, color=["#c44e52", "#4c72b0"])
    ax.set_title("Perfil demográfico de capturados por corrupción administrativa")
    ax.set_xlabel("Grupo etario")
    ax.set_ylabel("Capturas")
    plt.xticks(rotation=0)
    guardar("policia_perfil_capturados.jpg")


if __name__ == "__main__":
    tendencia_anual_corrupcion()
    heatmap_año_capitulo()
    top_departamentos()
    top_delitos_corrupcion()
    perfil_capturados()
