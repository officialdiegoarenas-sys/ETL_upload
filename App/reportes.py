"""Reportes del dashboard: cada uno responde una pregunta con una gráfica y su explicación."""
from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import almacen
import datos
from estilos import AMARILLO, AZUL, AZUL_OSC, GRIS, ROJO, TEXTO, fmt, fmt_cop, fmt_pct


@st.cache_data(ttl=300, show_spinner=False)
def tabla(nombre: str) -> pd.DataFrame:
    return datos.cargar(nombre)


@dataclass
class Resultado:
    titulo: str
    fig: go.Figure
    lectura: str
    ojo: str
    tabla: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class Reporte:
    id: str
    fuente: str          # fiscalia | secop | procuraduria
    pregunta: str        # pregunta en lenguaje del usuario (nombre de la pestaña)
    construir: Callable[[str], Resultado]
    datasets: tuple = ()


# Utilidades de gráfica
def _envolver(texto: str, ancho: int = 30) -> str:
    return "<br>".join(textwrap.wrap(str(texto), ancho)) or str(texto)


def _base(fig: go.Figure, altura: int) -> go.Figure:
    fig.update_layout(
        height=altura, margin=dict(l=8, r=24, t=10, b=10), paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial, sans-serif", size=15, color=TEXTO), dragmode=False,
        showlegend=False, hoverlabel=dict(font_size=15),
    )
    return fig


def barras_h(etiquetas, valores, textos, hover=None, destacar: int = 1, ancho_etiqueta: int = 30) -> go.Figure:
    n = len(etiquetas)
    fig = go.Figure(go.Bar(
        x=list(valores), y=[_envolver(e, ancho_etiqueta) for e in etiquetas], orientation="h",
        marker=dict(color=[AMARILLO if i < destacar else AZUL for i in range(n)],
                    line=dict(color=[AZUL_OSC if i < destacar else AZUL for i in range(n)], width=2)),
        text=[str(t).replace("  (", "<br>(") for t in textos],   # dos líneas: cabe también en celular
        textposition="outside", textfont=dict(size=16, color=TEXTO), cliponaxis=False,
        customdata=hover if hover is not None else list(textos),
        hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", automargin=True, tickfont=dict(size=15), showgrid=False)
    fig.update_xaxes(visible=False, range=[0, max(valores) * 1.4 if len(valores) else 1])
    return _base(fig, 62 * n + 40)


def _vacio(msg: str) -> Resultado:
    return Resultado("Aún no hay datos para mostrar", _base(go.Figure(), 120), msg, "Ejecute el ETL (python main.py) y recargue.")


# FISCALÍA
def r_etapa(ctx: str) -> Resultado:
    df = tabla("etapa")
    estado = st.radio("¿Qué procesos quiere ver?", ["Todos", "Solo activos", "Solo inactivos"], horizontal=True, key=f"{ctx}_etapa_estado")
    filtro = {"Solo activos": "Activo", "Solo inactivos": "Inactivo"}.get(estado)
    d = df if filtro is None else df[df["estado"] == filtro]
    g = d.groupby("etapa", as_index=False)["total"].sum().sort_values("total", ascending=False)
    total = g["total"].sum()
    g["pct"] = g["total"] / total * 100
    top = g.iloc[0]
    fig = barras_h(g["etapa"], g["total"], [f"{fmt(t)}  ({fmt(p)} %)" for t, p in zip(g["total"], g["pct"])])
    quien = {"Solo activos": "de los procesos activos", "Solo inactivos": "de los procesos inactivos"}.get(estado, "de los procesos")
    return Resultado(
        f"El {fmt(top.pct)} % {quien} está en {top.etapa}",
        fig,
        "Cada barra es una fase del proceso penal. <b>Indagación</b> es la primera: se reúne información para establecer "
        "si hubo un delito. <b>Investigación</b> y <b>Juicio</b> son fases posteriores; <b>Ejecución de penas</b> es la última. "
        "La barra amarilla es la fase con más procesos.",
        "Son conteos de procesos registrados por delitos contra la administración pública. Una etapa no indica por sí sola "
        "responsabilidad de nadie.",
        g.rename(columns={"etapa": "Etapa", "total": "Procesos", "pct": "% del total"}).round({"% del total": 1}),
    )


def r_departamento(ctx: str) -> Resultado:
    df = tabla("departamento")
    n = st.radio("¿Cuántos departamentos mostrar?", [5, 10, 15], index=1, horizontal=True, key=f"{ctx}_dep_n",
                 format_func=lambda x: f"Los {x} primeros")
    d = df.sort_values("total_procesos", ascending=False)
    total = d["total_procesos"].sum()
    top = d.head(n)
    hover = [f"{fmt(a)} procesos · {fmt(p, 1)} % siguen activos" for a, p in zip(top["total_procesos"], top["pct_activos"])]
    fig = barras_h(top["departamento_hecho"], top["total_procesos"],
                   [f"{fmt(v)}  ({fmt(v / total * 100)} %)" for v in top["total_procesos"]], hover=hover)
    p1 = top.iloc[0]
    return Resultado(
        f"{p1.departamento_hecho} concentra el {fmt(p1.total_procesos / total * 100)} % de los procesos del país",
        fig,
        f"Cada barra muestra cuántos procesos ocurrieron en ese departamento. El porcentaje es la parte del total nacional "
        f"({fmt(total)} procesos). Pase el cursor o toque una barra para ver cuántos siguen activos.",
        "Son cifras absolutas: los departamentos más poblados tienen más procesos. No son tasas por habitante ni comparan "
        "desempeño entre territorios.",
        top[["departamento_hecho", "total_procesos", "procesos_activos", "pct_activos"]].rename(columns={
            "departamento_hecho": "Departamento", "total_procesos": "Procesos", "procesos_activos": "Activos", "pct_activos": "% activos"}),
    )


def r_tendencia(ctx: str) -> Resultado:
    df = tabla("anio_capitulo")
    caps = ["Todos los delitos"] + sorted(df["capitulo_delito"].unique())
    cap = st.selectbox("¿Qué grupo de delitos quiere ver?", caps, key=f"{ctx}_tend_cap")
    d = df if cap == "Todos los delitos" else df[df["capitulo_delito"] == cap]
    g = d.groupby("año_creacion", as_index=False)["total_procesos"].sum().sort_values("año_creacion")
    if g.empty:
        return _vacio("No hay procesos para ese grupo de delitos.")
    parcial = int(g["año_creacion"].max()) == date.today().year
    completos = g.iloc[:-1] if parcial and len(g) > 1 else g
    pico = completos.loc[completos["total_procesos"].idxmax()]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=completos["año_creacion"], y=completos["total_procesos"], mode="lines+markers",
                             line=dict(color=AZUL, width=4), marker=dict(size=9, color=AZUL),
                             hovertemplate="<b>%{x}</b><br>%{y:,.0f} procesos<extra></extra>"))
    if parcial and len(g) > 1:
        fig.add_trace(go.Scatter(x=g["año_creacion"].iloc[-2:], y=g["total_procesos"].iloc[-2:], mode="lines+markers",
                                 line=dict(color=GRIS, width=3, dash="dot"), marker=dict(size=9, color=GRIS),
                                 hovertemplate="<b>%{x} (año en curso)</b><br>%{y:,.0f} procesos<extra></extra>"))
    fig.add_trace(go.Scatter(x=[pico["año_creacion"]], y=[pico["total_procesos"]], mode="markers+text",
                             marker=dict(size=18, color=AMARILLO, line=dict(color=AZUL_OSC, width=3)),
                             text=[f"{int(pico['año_creacion'])}: {fmt(pico['total_procesos'])}"], textposition="top center",
                             textfont=dict(size=16, color=AZUL_OSC), hoverinfo="skip"))
    fig.update_xaxes(dtick=2, showgrid=False, tickfont=dict(size=15))
    fig.update_yaxes(rangemode="tozero", gridcolor="#E7EBF3", tickformat=",.0f", tickfont=dict(size=14))
    fig.update_layout(margin=dict(l=8, r=16, t=40, b=10))
    fig = _base(fig, 400)
    nombre = "los delitos" if cap == "Todos los delitos" else f"«{cap}»"
    return Resultado(
        f"Los procesos por {nombre} llegaron a su nivel más alto en {int(pico['año_creacion'])}",
        fig,
        "La línea muestra cuántos procesos se abrieron cada año. El punto amarillo marca el año con más procesos "
        "completos; si la línea baja, ese año se abrieron menos.",
        ("El último punto (línea punteada) es el año en curso y todavía está incompleto: no es una caída real. "
         if parcial else "") + "El año se refiere a la creación del proceso en el registro de la Fiscalía.",
        g.rename(columns={"año_creacion": "Año", "total_procesos": "Procesos"}),
    )


def r_delitos(ctx: str) -> Resultado:
    df = tabla("top_delitos").sort_values("total", ascending=False)
    n = st.radio("¿Cuántos delitos mostrar?", [5, 10], index=0, horizontal=True, key=f"{ctx}_del_n", format_func=lambda x: f"Los {x} primeros")
    top = df.head(n)
    total = df["total"].sum()
    p1 = top.iloc[0]
    fig = barras_h(top["delito"], top["total"], [f"{fmt(v)}" for v in top["total"]],
                   hover=[f"{c}" for c in top["capitulo_delito"]], ancho_etiqueta=34)
    return Resultado(
        f"El delito más frecuente es «{p1.delito.split(' Art.')[0]}»: {fmt(p1.total)} procesos",
        fig,
        f"Cada barra es un delito del Código Penal (el artículo aparece en el nombre). Los {n} primeros suman "
        f"{fmt_pct(top['total'].sum() / total * 100)} de los {fmt(total)} procesos de la lista. Al pasar el cursor verá el grupo de delitos al que pertenece.",
        "Un mismo proceso puede registrar varios delitos, por eso las barras no suman el total de procesos.",
        top[["articulo", "delito", "capitulo_delito", "total"]].rename(columns={
            "articulo": "Artículo", "delito": "Delito", "capitulo_delito": "Grupo de delitos", "total": "Procesos"}),
    )


def r_condena(ctx: str) -> Resultado:
    df = tabla("sentencias")
    d = df[(df["capitulo_delito"] != "Sin registrar") & (df["total_procesados"] >= 500)].sort_values("pct_condena", ascending=False)
    top = d.head(8)
    p1 = top.iloc[0]
    hover = [f"{fmt(c)} condenados · {fmt(a)} absueltos · {fmt(t)} procesados"
             for c, a, t in zip(top["condenados"], top["absueltos"], top["total_procesados"])]
    fig = barras_h(top["capitulo_delito"], top["pct_condena"], [fmt_pct(p, 1) for p in top["pct_condena"]], hover=hover, ancho_etiqueta=32)
    return Resultado(
        f"En «{p1.capitulo_delito}» {fmt(p1.pct_condena)} de cada 100 procesados fue condenado: el nivel más alto",
        fig,
        "Cada barra indica cuántas personas condenadas hay por cada 100 procesadas en ese grupo de delitos. "
        "Pase el cursor o toque una barra para ver condenados, absueltos y procesados.",
        "Incluye procesados cuyo caso sigue en curso, por eso el porcentaje es una referencia mínima y no una tasa final de "
        "condena. Se omiten grupos con menos de 500 procesados y los no registrados.",
        top[["capitulo_delito", "total_procesados", "condenados", "absueltos", "pct_condena"]].rename(columns={
            "capitulo_delito": "Grupo de delitos", "total_procesados": "Procesados", "condenados": "Condenados",
            "absueltos": "Absueltos", "pct_condena": "% condenados"}),
    )


_EDADES = [("14 a 17", "14 a 17 años"), ("18 a 26", "18 a 26 años"), ("27 a 59", "27 a 59 años"), ("60", "60 años o más")]


def r_perfil(ctx: str) -> Resultado:
    df = tabla("perfil")

    def grupo(txt: str) -> str:
        for clave, nombre in _EDADES:
            if clave in txt:
                return nombre
        return "Sin registrar"

    d = df.assign(edad=df["grupo_etario"].map(grupo))
    con_edad = d[d["edad"] != "Sin registrar"]
    por_edad = con_edad.groupby("edad")["total_condenados"].sum()
    top_edad = por_edad.idxmax()
    pct_top = por_edad.max() / por_edad.sum() * 100
    sin_dato = d[(d["edad"] == "Sin registrar")]["total_condenados"].sum() / d["total_condenados"].sum() * 100
    reg = con_edad[con_edad["sexo"].isin(["Hombre", "Mujer"])]
    fig = go.Figure()
    for sexo, color in (("Hombre", AZUL), ("Mujer", AMARILLO)):
        s = reg[reg["sexo"] == sexo].set_index("edad")["total_condenados"].reindex([n for _, n in _EDADES]).fillna(0)
        fig.add_bar(x=list(s.index), y=list(s.values), name=sexo, marker=dict(color=color, line=dict(color=AZUL_OSC, width=1.5)),
                    text=[fmt(v) for v in s.values], textposition="outside", textfont=dict(size=15),
                    hovertemplate=f"<b>{sexo}</b> · %{{x}}<br>%{{y:,.0f}} condenados<extra></extra>")
    fig.update_layout(barmode="group", showlegend=True, legend=dict(orientation="h", y=1.12, font=dict(size=16)))
    fig.update_yaxes(visible=False)
    fig.update_xaxes(tickfont=dict(size=15))
    fig = _base(fig, 400)
    fig.update_layout(showlegend=True, margin=dict(l=8, r=8, t=40, b=10))
    return Resultado(
        f"El {fmt(pct_top)} % de los condenados con edad registrada tiene entre {top_edad.replace(' años', '').replace(' a ', ' y ')} años"
        if top_edad != "60 años o más" else f"La mayoría de los condenados tiene {top_edad}",
        fig,
        "Cada grupo de barras es un rango de edad; el color separa hombres (azul) y mujeres (amarillo). "
        "El número sobre la barra es la cantidad de personas condenadas.",
        f"El {fmt(sin_dato)} % de los condenados no tiene edad registrada y no aparece en la gráfica. Solo se grafican personas "
        "con sexo registrado como hombre o mujer.",
        reg.rename(columns={"sexo": "Sexo", "edad": "Edad", "total_condenados": "Condenados"})[["Sexo", "Edad", "Condenados"]],
    )


# CONTRATACIÓN PÚBLICA (SECOP II)
def _muestra_secop() -> int:
    return int(tabla("secop")["total_procesos"].sum())


def r_secop_modalidad(ctx: str) -> Resultado:
    df = tabla("secop")
    g = df.groupby("modalidad_de_contratacion", as_index=False)["total_procesos"].sum().sort_values("total_procesos", ascending=False)
    total = g["total_procesos"].sum()
    top = g.head(6)
    p1 = top.iloc[0]
    fig = barras_h(top["modalidad_de_contratacion"], top["total_procesos"],
                   [f"{fmt(v)}  ({fmt(v / total * 100)} %)" for v in top["total_procesos"]], ancho_etiqueta=34)
    return Resultado(
        f"«{p1.modalidad_de_contratacion}» es la forma de contratar más usada: {fmt(p1.total_procesos / total * 100)} % de la muestra",
        fig,
        "Cada barra es una forma de contratar (modalidad). La contratación directa y la de régimen especial no exigen "
        "competencia abierta entre varios proponentes; la licitación pública sí.",
        f"Muestra de {fmt(total)} procesos publicados en SECOP II, no el universo completo. Una modalidad frecuente no es, "
        "por sí sola, señal de irregularidad.",
        g.rename(columns={"modalidad_de_contratacion": "Modalidad", "total_procesos": "Procesos"}),
    )


def r_secop_entidades(ctx: str) -> Resultado:
    df = tabla("secop")
    g = df.groupby("entidad", as_index=False)["precio_base_total"].sum().sort_values("precio_base_total", ascending=False)
    top = g.head(8)
    p1 = top.iloc[0]
    fig = barras_h(top["entidad"], top["precio_base_total"], [fmt_cop(v) for v in top["precio_base_total"]], ancho_etiqueta=34)
    return Resultado(
        f"{p1.entidad} tiene el mayor valor base en la muestra: {fmt_cop(p1.precio_base_total)}",
        fig,
        "Cada barra suma el precio base (el valor estimado antes de contratar) de los procesos de una entidad. "
        "La barra amarilla es la de mayor valor.",
        f"Es el precio base publicado, no lo adjudicado ni lo pagado. Muestra de {fmt(_muestra_secop())} procesos: un solo "
        "proceso grande puede dominar la gráfica.",
        g.rename(columns={"entidad": "Entidad", "precio_base_total": "Precio base total ($)"}).round(0),
    )


def r_secop_estado(ctx: str) -> Resultado:
    df = tabla("secop")
    g = df.groupby("estado_del_procedimiento", as_index=False)["total_procesos"].sum().sort_values("total_procesos", ascending=False)
    total = g["total_procesos"].sum()
    p1 = g.iloc[0]
    fig = barras_h(g["estado_del_procedimiento"], g["total_procesos"],
                   [f"{fmt(v)}  ({fmt(v / total * 100)} %)" for v in g["total_procesos"]])
    return Resultado(
        f"El {fmt(p1.total_procesos / total * 100)} % de los procesos de la muestra figura como «{p1.estado_del_procedimiento}»",
        fig,
        "Cada barra es el estado en que se encuentra el proceso de contratación: <b>Publicado</b> (abierto), "
        "<b>Evaluación</b> (se revisan ofertas), <b>Seleccionado</b> (hay proveedor escogido) o <b>Cancelado</b>.",
        "Es el estado publicado en SECOP II; no prueba por sí mismo adjudicación, ejecución ni irregularidad.",
        g.rename(columns={"estado_del_procedimiento": "Estado", "total_procesos": "Procesos"}),
    )


# PROCURADURÍA
def r_procuraduria(ctx: str) -> Resultado:
    df = tabla("procuraduria")
    incluir = st.checkbox("Incluir Policía, Ejército y demás Fuerza Pública", value=False, key=f"{ctx}_procu_fp",
                          help="Por defecto se muestran solo entidades civiles, que es el foco del proyecto.")
    d = df if incluir else df[~df["fuerza_publica"]]
    top = d.sort_values("total_sanciones", ascending=False).head(8)
    total = d["total_sanciones"].sum()
    p1 = top.iloc[0]
    fig = barras_h(top["entidad_sancionado"], top["total_sanciones"], [fmt(v) for v in top["total_sanciones"]], ancho_etiqueta=34)
    alcance = "todas las entidades" if incluir else "entidades civiles"
    return Resultado(
        f"{p1.entidad_sancionado} es la entidad con más sanciones disciplinarias ({alcance}): {fmt(p1.total_sanciones)}",
        fig,
        f"Cada barra es la cantidad de sanciones disciplinarias registradas por la Procuraduría a servidores de esa entidad. "
        f"Entre {alcance} suman {fmt(total)} sanciones.",
        "Se unificaron escrituras distintas de la misma entidad (p. ej. INPEC). Son cifras agregadas: no se muestran nombres "
        "ni documentos de personas. Corresponde a toda la base de sanciones de la Procuraduría a la fecha de la última actualización.",
        top.rename(columns={"entidad_sancionado": "Entidad", "total_sanciones": "Sanciones"})[["Entidad", "Sanciones"]],
    )


# CONTRALORÍA (resultado de las auditorías)
_TIPOS_HALLAZGO = [("hallazgos_administrativos", "Administrativos"), ("hallazgos_disciplinarios", "Disciplinarios"),
                   ("hallazgos_fiscales", "Fiscales"), ("hallazgos_penales", "Penales")]
_COLUMNAS_HALLAZGO = [c for c, _ in _TIPOS_HALLAZGO]


def r_contraloria_tipo(ctx: str) -> Resultado:
    df = tabla("contraloria")
    g = pd.DataFrame({"tipo": [n for _, n in _TIPOS_HALLAZGO], "total": [int(df[c].sum()) for c, _ in _TIPOS_HALLAZGO]})
    g = g.sort_values("total", ascending=False)
    total = g["total"].sum()
    top = g.iloc[0]
    fig = barras_h(g["tipo"], g["total"], [f"{fmt(t)}  ({fmt(t / total * 100, 1)} %)" for t in g["total"]])
    return Resultado(
        f"El {fmt(top.total / total * 100)} % de los hallazgos de las auditorías son {top.tipo.lower()}",
        fig,
        "Cada barra es un tipo de hallazgo. <b>Administrativos:</b> fallas de gestión. <b>Disciplinarios:</b> posible falta "
        "disciplinaria. <b>Fiscales:</b> posible daño al patrimonio público. <b>Penales:</b> posible delito. "
        f"En total son {fmt(total)} hallazgos.",
        "Un hallazgo es una observación del auditor, no una sanción ni una sentencia: los casos disciplinarios, fiscales y "
        "penales se trasladan a otras entidades para que decidan.",
        g.rename(columns={"tipo": "Tipo de hallazgo", "total": "Hallazgos"}),
    )


def r_contraloria_vigencia(ctx: str) -> Resultado:
    df = tabla("contraloria").copy()
    df["hallazgos"] = df[_COLUMNAS_HALLAZGO].sum(axis=1)
    medida = st.radio("¿Qué quiere ver?", ["Cantidad de hallazgos", "Cuantía de los hallazgos fiscales"], horizontal=True,
                      key=f"{ctx}_vig_medida")
    columna, etiqueta = ("hallazgos", "hallazgos") if medida.startswith("Cantidad") else ("cuantia", "de cuantía")
    g = df.groupby("vigencia", as_index=False)[columna].sum().sort_values("vigencia")
    pico = g.loc[g[columna].idxmax()]
    textos = [fmt(v) if columna == "hallazgos" else fmt_cop(v) for v in g[columna]]
    colores = [AMARILLO if v == pico["vigencia"] else AZUL for v in g["vigencia"]]
    fig = go.Figure(go.Bar(x=[str(int(v)) for v in g["vigencia"]], y=g[columna], marker=dict(color=colores, line=dict(color=AZUL_OSC, width=1.5)),
                           text=textos, textposition="outside", textfont=dict(size=15), cliponaxis=False,
                           hovertemplate="<b>Vigencia %{x}</b><br>%{text}<extra></extra>"))
    fig.update_yaxes(visible=False, range=[0, g[columna].max() * 1.2])
    fig.update_xaxes(tickfont=dict(size=15))
    fig = _base(fig, 380)
    valor = fmt(pico[columna]) if columna == "hallazgos" else fmt_cop(pico[columna])
    return Resultado(
        f"La vigencia {int(pico['vigencia'])} tuvo el mayor valor {'de hallazgos' if columna == 'hallazgos' else 'en cuantía'}: {valor}",
        fig,
        "Cada barra es una vigencia (el año auditado). La barra amarilla es la de mayor valor. "
        + ("Los hallazgos se suman sobre todas las auditorías de ese año." if columna == "hallazgos"
           else "La cuantía es el valor estimado de los hallazgos fiscales; puede concentrarse en pocos casos grandes."),
        "La vigencia es el año auditado, no el año en que se hizo la auditoría. Las cifras vienen de la Auditoría General de la República.",
        g.rename(columns={"vigencia": "Vigencia", "hallazgos": "Hallazgos", "cuantia": "Cuantía ($)"}),
    )


def r_contraloria_sujetos(ctx: str) -> Resultado:
    df = tabla("contraloria").copy()
    df["hallazgos"] = df[_COLUMNAS_HALLAZGO].sum(axis=1)
    g = (df.groupby("sujeto_auditado", as_index=False).agg(hallazgos=("hallazgos", "sum"), auditorias=("hallazgos", "size"), cuantia=("cuantia", "sum"))
         .sort_values("hallazgos", ascending=False))
    top = g.head(8)
    p1 = top.iloc[0]
    hover = [f"{fmt(a)} auditorías · cuantía {fmt_cop(c)}" for a, c in zip(top["auditorias"], top["cuantia"])]
    fig = barras_h(top["sujeto_auditado"], top["hallazgos"], [fmt(v) for v in top["hallazgos"]], hover=hover, ancho_etiqueta=34)
    return Resultado(
        f"{p1.sujeto_auditado} es la entidad con más hallazgos: {fmt(p1.hallazgos)}",
        fig,
        f"Cada barra suma los hallazgos de todas las auditorías de una entidad (hay {fmt(len(g))} en total). "
        "Pase el cursor o toque una barra para ver cuántas auditorías tuvo y su cuantía.",
        "Tener más hallazgos puede deberse a que fue auditada más veces o con mayor alcance; no mide por sí solo la calidad de su gestión.",
        top.rename(columns={"sujeto_auditado": "Entidad", "hallazgos": "Hallazgos", "auditorias": "Auditorías", "cuantia": "Cuantía ($)"}),
    )


# Catálogo
REPORTES: list[Reporte] = [
    Reporte("fis_etapa", "fiscalia", "¿En qué etapa están los procesos?", r_etapa, ("etapa",)),
    Reporte("fis_departamento", "fiscalia", "¿Dónde ocurren?", r_departamento, ("departamento",)),
    Reporte("fis_tendencia", "fiscalia", "¿Cómo ha cambiado con los años?", r_tendencia, ("anio_capitulo",)),
    Reporte("fis_delitos", "fiscalia", "¿Qué delitos son más comunes?", r_delitos, ("top_delitos",)),
    Reporte("fis_condena", "fiscalia", "¿Cuántos terminan en condena?", r_condena, ("sentencias",)),
    Reporte("fis_perfil", "fiscalia", "¿Quiénes son los condenados?", r_perfil, ("perfil",)),
    Reporte("sec_modalidad", "secop", "¿Cómo se está contratando?", r_secop_modalidad, ("secop",)),
    Reporte("sec_entidades", "secop", "¿Qué entidades contratan más valor?", r_secop_entidades, ("secop",)),
    Reporte("sec_estado", "secop", "¿En qué estado están los procesos?", r_secop_estado, ("secop",)),
    Reporte("pro_entidades", "procuraduria", "¿Qué entidades tienen más sanciones?", r_procuraduria, ("procuraduria",)),
    Reporte("con_tipo", "contraloria", "¿Qué tipo de hallazgos hay?", r_contraloria_tipo, ("contraloria",)),
    Reporte("con_vigencia", "contraloria", "¿Cómo cambia por año?", r_contraloria_vigencia, ("contraloria",)),
    Reporte("con_sujetos", "contraloria", "¿Qué entidades tienen más hallazgos?", r_contraloria_sujetos, ("contraloria",)),
]
POR_ID = {r.id: r for r in REPORTES}


def de_fuente(fuente: str) -> list[Reporte]:
    return [r for r in REPORTES if r.fuente == fuente]


# Presentación de un reporte (con estrella de favoritos)
def _alternar(correo: str, rid: str) -> None:
    almacen.alternar_favorito(correo, rid)


def mostrar_reporte(r: Reporte, correo: str, ctx: str) -> None:
    faltan = [d for d in r.datasets if not datos.disponible(d)]
    st.markdown(f'<span class="pregunta">{r.pregunta}</span>', unsafe_allow_html=True)
    if faltan:
        st.warning("Este reporte aún no tiene datos. Pida a soporte ejecutar el ETL (python main.py).")
        return
    try:
        res = r.construir(f"{ctx}_{r.id}")
    except datos.DatoNoDisponible as e:
        st.warning(str(e))
        return
    fav = almacen.es_favorito(correo, r.id)
    c1, c2 = st.columns([3, 1.4])
    c1.markdown(f'<div class="rep-titulo">{res.titulo}</div>', unsafe_allow_html=True)
    c2.button("⭐ Guardado (quitar)" if fav else "☆ Guardar en favoritos", key=f"fav_{ctx}_{r.id}", on_click=_alternar,
              args=(correo, r.id), type="primary" if fav else "secondary", width="stretch",
              help="Los reportes guardados aparecen en «Mis favoritos».")
    st.plotly_chart(res.fig, config={"displayModeBar": False}, width="stretch", key=f"graf_{ctx}_{r.id}")
    st.markdown(f'<div class="lectura">📖 <b>Cómo leer esta gráfica.</b> {res.lectura}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ojo">⚠️ <b>Tenga en cuenta:</b> {res.ojo}</div>', unsafe_allow_html=True)
    if not res.tabla.empty:
        with st.expander("Ver los números en una tabla"):
            st.dataframe(res.tabla, hide_index=True, width="stretch")
