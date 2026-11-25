"""Colores, estilos CSS y formato de números del dashboard."""
from __future__ import annotations

import streamlit as st

AZUL = "#0A3D91"
AZUL_OSC = "#062A66"
AZUL_CLARO = "#DCE7F8"
AMARILLO = "#FFD100"
AMARILLO_CLARO = "#FFF6C7"
ROJO = "#C8102E"
TEXTO = "#1B2433"
GRIS = "#5B6575"
FONDO = "#F4F6FA"

ESCALAS = {"Normal": 112.5, "Grande": 125, "Muy grande": 140}


# Formato de números en español
def _es(texto: str) -> str:
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt(n, decimales: int = 0) -> str:
    """109775 -> '109.775' ; 2.83 -> '2,8' (decimales=1)."""
    return _es(f"{float(n):,.{decimales}f}")


def fmt_pct(n, decimales: int = 0) -> str:
    return f"{fmt(n, decimales)} %"


def fmt_cop(valor) -> str:
    v = float(valor)
    if abs(v) >= 1e9:
        return "$" + fmt(v / 1e9, 1) + " mil millones"
    if abs(v) >= 1e6:
        return "$" + fmt(v / 1e6, 0) + " millones"
    return "$" + fmt(v)


# CSS
def _css(escala: float) -> str:
    return f"""
<style>
html {{ font-size: {escala}%; }}
.stApp {{ background: {FONDO}; color: {TEXTO}; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1200px; padding-top: 4.6rem; }}
[data-testid="stSidebar"][aria-expanded="true"] {{ min-width: 290px !important; width: 290px !important; }}
[data-testid="stPageLink"] a p, .stButton > button p {{ white-space: normal; text-align: center; line-height: 1.2; }}
#MainMenu, footer, .stAppDeployButton, [data-testid="stHeaderActionElements"] {{ visibility: hidden; display: none; }}
h1, h2, h3 {{ color: {AZUL_OSC}; letter-spacing: -0.01em; }}
:focus-visible {{ outline: 3px solid {AZUL} !important; outline-offset: 2px; }}

/* ----- Encabezado ----- */
.hero {{
  background: linear-gradient(120deg, {AZUL_OSC} 0%, {AZUL} 100%);
  color: #fff; border-radius: 16px; padding: 1.4rem 1.6rem 1.2rem;
  margin-bottom: 1.1rem; position: relative; overflow: hidden;
  box-shadow: 0 6px 18px rgba(6,42,102,.25);
}}
.hero::after {{ /* franja tricolor */
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 8px;
  background: linear-gradient(90deg, {AMARILLO} 0 50%, {AZUL_CLARO} 50% 75%, {ROJO} 75% 100%);
}}
.hero .sup {{ font-size: .8rem; letter-spacing: .14em; text-transform: uppercase; color: {AMARILLO}; font-weight: 700; }}
.hero h1 {{ color: #fff; margin: .15rem 0 .2rem; font-size: 2rem; line-height: 1.2; }}
.hero p {{ margin: 0; color: #E6EEFC; font-size: 1.02rem; }}

/* ----- Tarjetas de cifras ----- */
.kpi {{
  background: #fff; border-radius: 14px; padding: 1rem 1.1rem; height: 100%;
  border-left: 10px solid {AZUL}; box-shadow: 0 2px 10px rgba(10,61,145,.10);
}}
.kpi.am {{ border-left-color: {AMARILLO}; }} .kpi.ro {{ border-left-color: {ROJO}; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }}
.kpi .num {{ font-size: 2.3rem; font-weight: 800; color: {AZUL_OSC}; line-height: 1.1; overflow-wrap: normal; }}
.kpi .eti {{ font-size: 1.02rem; font-weight: 700; margin-top: .15rem; }}
.kpi .nota {{ font-size: .88rem; color: {GRIS}; margin-top: .25rem; }}

/* ----- Reportes ----- */
.pregunta {{
  display: inline-block; background: {AMARILLO}; color: {AZUL_OSC}; font-weight: 800;
  border-radius: 999px; padding: .2rem .85rem; font-size: .95rem; margin-bottom: .35rem;
}}
.rep-titulo {{ font-size: 1.55rem; font-weight: 800; color: {AZUL_OSC}; line-height: 1.25; margin: .1rem 0 .4rem; }}
.lectura {{
  background: {AMARILLO_CLARO}; border-left: 8px solid {AMARILLO}; border-radius: 10px;
  padding: .75rem 1rem; font-size: 1.02rem; margin: .4rem 0 .5rem;
}}
.ojo {{ color: {GRIS}; font-size: .92rem; margin-bottom: .6rem; }}
.historia {{
  background: #fff; border-radius: 14px; padding: 1.05rem 1.3rem; font-size: 1.12rem; line-height: 1.6;
  border-top: 6px solid {AMARILLO}; box-shadow: 0 2px 10px rgba(10,61,145,.10);
}}
.historia b.y {{ color: {AZUL}; }} .historia b.p {{ color: {ROJO}; }} .historia b.l {{ color: {AZUL_OSC}; }}
.aviso {{ background: {AZUL_CLARO}; border-radius: 10px; padding: .7rem 1rem; font-size: .95rem; color: {AZUL_OSC}; }}
.pie {{ color: {GRIS}; font-size: .85rem; margin-top: 1.6rem; border-top: 1px solid #D5DBE6; padding-top: .7rem; }}

/* ----- Controles grandes y fáciles de pulsar ----- */
.stButton > button, .stFormSubmitButton > button, [data-testid="stPageLink"] a {{
  min-height: 3rem; border-radius: 10px; font-weight: 700; font-size: 1rem;
  border: 2px solid {AZUL}; color: {AZUL_OSC}; background: #fff;
}}
.stButton > button:hover, [data-testid="stPageLink"] a:hover {{ background: {AZUL_CLARO}; border-color: {AZUL_OSC}; }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
.stFormSubmitButton > button, button[kind="primaryFormSubmit"] {{
  background: {AZUL}; color: #fff; border-color: {AZUL};
}}
.stButton > button[kind="primary"]:hover {{ background: {AZUL_OSC}; color: #fff; }}
[data-testid="stPageLink"] a {{ justify-content: center; text-decoration: none; background: #fff; box-shadow: 0 2px 8px rgba(10,61,145,.10); }}
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{ font-size: 1.05rem; }}
.stTextInput input {{ min-height: 2.9rem; }}
button[data-baseweb="tab"] {{ font-size: 1.02rem; font-weight: 700; padding: .7rem 1rem; color: {AZUL_OSC}; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {AZUL_OSC}; }}
div[data-baseweb="tab-highlight"] {{ background-color: {ROJO}; height: 4px; }}
[data-testid="stSidebar"] {{ background: #fff; border-right: 6px solid {AMARILLO}; }}

/* ----- Calendario: 7 columnas siempre, también en celular ----- */
.st-key-cuadricula [data-testid="stHorizontalBlock"], .st-key-navmes [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: .3rem; }}
.st-key-cuadricula [data-testid="stColumn"], .st-key-navmes [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; }}
.st-key-navmes .stButton > button p {{ font-size: 1.3rem; }}
.solo-movil {{ display: none; }}
.st-key-cuadricula .stButton > button {{ min-height: 3.1rem; padding: 0; width: 100%; font-size: 1.05rem; }}
.st-key-cuadricula .stButton > button p {{ font-size: 1.15rem; font-weight: 800; }}
.cal-sem {{ text-align: center; font-weight: 800; color: {AZUL_OSC}; font-size: .95rem; }}
.cal-sem.fin {{ color: {ROJO}; }}
.evento {{ background: #fff; border-radius: 10px; padding: .6rem .9rem; margin-bottom: .45rem; border-left: 8px solid {AZUL}; }}
.evento.fest {{ border-left-color: {ROJO}; }} .evento.etl {{ border-left-color: {AMARILLO}; }}
.evento small {{ color: {GRIS}; }}

/* ----- Celular y tableta ----- */
@media (max-width: 900px) {{
  .solo-movil {{ display: block; }}
  .hero h1 {{ font-size: 1.7rem; }}
  .kpi .num {{ font-size: 2rem; }}
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 4rem .75rem 3rem; }}
  .hero {{ padding: 1rem 1rem .9rem; }}
  .hero h1 {{ font-size: 1.4rem; }}
  .rep-titulo {{ font-size: 1.3rem; }}
  .kpi {{ margin-bottom: .6rem; }}
  .st-key-cuadricula .stButton > button {{ min-height: 2.6rem; font-size: .95rem; }}
  button[data-baseweb="tab"] {{ padding: .55rem .7rem; }}
}}
</style>
"""


def aplicar(escala_nombre: str = "Normal") -> None:
    """Inyecta el CSS institucional. Debe llamarse en cada ejecución de la página."""
    st.markdown(_css(ESCALAS.get(escala_nombre, 112.5)), unsafe_allow_html=True)


def regla_dia(iso: str, *, hoy: bool, festivo: bool, con_evento: bool) -> str:
    """CSS puntual para un día del calendario (clave del botón: cal_AAAA-MM-DD)."""
    reglas = []
    if con_evento:
        reglas.append(f"background:{AMARILLO_CLARO};border-color:{AMARILLO};")
    if festivo:
        reglas.append(f"color:{ROJO};")
    if hoy:
        reglas.append(f"box-shadow:0 0 0 4px {AMARILLO};")
    return f".st-key-cal_{iso} button{{{''.join(reglas)}}}" if reglas else ""


def tarjeta_cifra(valor: str, etiqueta: str, nota: str, color: str = "") -> str:
    return (
        f'<div class="kpi {color}"><div class="num">{valor}</div>'
        f'<div class="eti">{etiqueta}</div><div class="nota">{nota}</div></div>'
    )


def rejilla_cifras(cifras) -> str:
    """Tarjetas en rejilla que se reacomoda sola: 4 en PC, 2 en tableta, 1 en celular."""
    return '<div class="kpis">' + "".join(tarjeta_cifra(*c) for c in cifras) + "</div>"
