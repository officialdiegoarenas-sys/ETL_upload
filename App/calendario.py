"""Calendario: festivos de Colombia, recordatorios del usuario y fechas del ETL."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

import almacen
import datos
import estilos

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# Festivos de Colombia (Ley 51 de 1983, "Ley Emiliani")
def _pascua(año: int) -> date:
    """Domingo de Pascua (algoritmo de Meeus/Jones/Butcher)."""
    a, b, c = año % 19, año // 100, año % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(año, mes, dia)


def _lunes_siguiente(d: date) -> date:
    return d if d.weekday() == 0 else d + timedelta(days=7 - d.weekday())


def festivos_colombia(año: int) -> dict[date, str]:
    pascua = _pascua(año)
    f: dict[date, str] = {
        date(año, 1, 1): "Año Nuevo",
        date(año, 5, 1): "Día del Trabajo",
        date(año, 7, 20): "Día de la Independencia",
        date(año, 8, 7): "Batalla de Boyacá",
        date(año, 12, 8): "Inmaculada Concepción",
        date(año, 12, 25): "Navidad",
        pascua - timedelta(days=3): "Jueves Santo",
        pascua - timedelta(days=2): "Viernes Santo",
    }
    trasladables = {
        date(año, 1, 6): "Día de los Reyes Magos",
        date(año, 3, 19): "Día de San José",
        date(año, 6, 29): "San Pedro y San Pablo",
        date(año, 8, 15): "Asunción de la Virgen",
        date(año, 10, 12): "Día de la Raza",
        date(año, 11, 1): "Día de Todos los Santos",
        date(año, 11, 11): "Independencia de Cartagena",
        pascua + timedelta(days=39): "Ascensión del Señor",
        pascua + timedelta(days=60): "Corpus Christi",
        pascua + timedelta(days=68): "Sagrado Corazón",
    }
    for d, nombre in trasladables.items():
        f[_lunes_siguiente(d)] = nombre
    return f


def es_dia_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in festivos_colombia(d.year)


def sumar_dias_habiles(inicio: date, cantidad: int) -> date:
    """Fecha que resulta de contar ``cantidad`` días hábiles después de ``inicio``
    (el día de inicio no cuenta; sábados, domingos y festivos no cuentan)."""
    if cantidad < 0:
        raise ValueError("La cantidad de días debe ser cero o positiva.")
    d, restantes = inicio, cantidad
    while restantes > 0:
        d += timedelta(days=1)
        if es_dia_habil(d):
            restantes -= 1
    return d


def fecha_larga(d: date) -> str:
    return f"{DIAS_LARGOS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


# Eventos del día (festivo + fechas del ETL + recordatorios del usuario)
def eventos_etl() -> dict[date, str]:
    ev: dict[date, str] = {}
    ult, prox = datos.ultima_actualizacion(), datos.proxima_actualizacion()
    if ult:
        ev[ult.date()] = f"Última actualización de datos del ETL ({ult:%H:%M})"
    if prox:
        ev.setdefault(prox.date(), "Próxima actualización programada de datos")
    return ev


def eventos_del_dia(correo: str, d: date) -> list[dict]:
    salida = []
    fest = festivos_colombia(d.year).get(d)
    if fest:
        salida.append({"clase": "fest", "titulo": f"Festivo: {fest}", "tipo": "Festivo", "nota": "", "id": None})
    etl = eventos_etl().get(d)
    if etl:
        salida.append({"clase": "etl", "titulo": etl, "tipo": "Datos", "nota": "", "id": None})
    for e in almacen.eventos(correo):
        if e["fecha"] == d.isoformat():
            salida.append({"clase": "", **e})
    return salida


def proximos_eventos(correo: str, hoy: date | None = None, dias: int = 30, maximo: int = 5) -> list[tuple[date, dict]]:
    """Recordatorios propios y próximos festivos de los siguientes ``dias`` días."""
    hoy = hoy or date.today()
    limite = hoy + timedelta(days=dias)
    lista: list[tuple[date, dict]] = []
    for e in almacen.eventos(correo):
        d = date.fromisoformat(e["fecha"])
        if hoy <= d <= limite:
            lista.append((d, {"clase": "", **e}))
    for año in {hoy.year, limite.year}:
        for d, nombre in festivos_colombia(año).items():
            if hoy <= d <= limite:
                lista.append((d, {"clase": "fest", "titulo": f"Festivo: {nombre}", "tipo": "Festivo", "nota": "", "id": None}))
    return sorted(lista, key=lambda x: x[0])[:maximo]


def html_evento(d: date, e: dict) -> str:
    nota = f"<br><small>{e['nota']}</small>" if e.get("nota") else ""
    return (f'<div class="evento {e["clase"]}"><b>{e["titulo"]}</b><br>'
            f'<small>{e["tipo"]} · {fecha_larga(d)}</small>{nota}</div>')


# Interfaz
def _ir_mes(delta: int) -> None:
    import streamlit as st
    y, m = st.session_state.cal_anio, st.session_state.cal_mes + delta
    if m < 1:
        y, m = y - 1, 12
    elif m > 12:
        y, m = y + 1, 1
    st.session_state.cal_anio, st.session_state.cal_mes = y, m


def _ir_hoy() -> None:
    import streamlit as st
    h = date.today()
    st.session_state.cal_anio, st.session_state.cal_mes, st.session_state.cal_sel = h.year, h.month, h


def _elegir(d: date) -> None:
    import streamlit as st
    st.session_state.cal_sel = d


def mostrar_calendario(correo: str) -> None:
    import streamlit as st

    hoy = date.today()
    ss = st.session_state
    ss.setdefault("cal_anio", hoy.year)
    ss.setdefault("cal_mes", hoy.month)
    ss.setdefault("cal_sel", hoy)

    anio, mes = ss.cal_anio, ss.cal_mes
    festivos = festivos_colombia(anio)
    propios = {date.fromisoformat(e["fecha"]) for e in almacen.eventos(correo)}
    etl = eventos_etl()

    # navegación de mes
    with st.container(key="navmes"):
        c1, c2, c3 = st.columns([1, 3, 1], vertical_alignment="center")
        c1.button("◀", on_click=_ir_mes, args=(-1,), width="stretch", key="mes_ant", help="Mes anterior")
        c2.markdown(f"<h2 style='text-align:center;margin:0'>{MESES[mes - 1].capitalize()} {anio}</h2>", unsafe_allow_html=True)
        c3.button("▶", on_click=_ir_mes, args=(1,), width="stretch", key="mes_sig", help="Mes siguiente")
    st.button("📍 Ir a hoy", on_click=_ir_hoy, key="ir_hoy")

    # cuadrícula del mes
    css = []
    with st.container(key="cuadricula"):
        cols = st.columns(7)
        for i, nombre in enumerate(DIAS):
            cols[i].markdown(f"<div class='cal-sem {'fin' if i >= 5 else ''}'>{nombre}</div>", unsafe_allow_html=True)
        for semana in calendar.Calendar(firstweekday=0).monthdatescalendar(anio, mes):
            cols = st.columns(7)
            for i, d in enumerate(semana):
                if d.month != mes:
                    cols[i].write("")
                    continue
                marca = "•" if (d in propios or d in etl) else ""
                cols[i].button(
                    f"{d.day}{marca}", key=f"cal_{d.isoformat()}", on_click=_elegir, args=(d,),
                    type="primary" if d == ss.cal_sel else "secondary", width="stretch",
                )
                css.append(estilos.regla_dia(d.isoformat(), hoy=d == hoy, festivo=d in festivos or d.weekday() == 6,
                                             con_evento=d in propios or d in etl))
    st.markdown("<style>" + "".join(css) + "</style>", unsafe_allow_html=True)
    st.caption("🟡 Día con recordatorio o fecha de datos · rojo: domingo o festivo · borde amarillo grueso: hoy")

    # detalle del día elegido
    sel = ss.cal_sel
    st.markdown(f"### {fecha_larga(sel).capitalize()}")
    lista = eventos_del_dia(correo, sel)
    if not lista:
        st.info("No hay nada anotado para este día. Puede agregar un recordatorio aquí abajo.")
    for e in lista:
        a, b = st.columns([6, 1])
        a.markdown(html_evento(sel, e), unsafe_allow_html=True)
        if e.get("id") and b.button("🗑️", key=f"del_{e['id']}", help="Borrar este recordatorio"):
            almacen.eliminar_evento(correo, e["id"])
            st.rerun()

    with st.form("nuevo_recordatorio", clear_on_submit=True):
        st.markdown("**➕ Agregar recordatorio a este día**")
        titulo = st.text_input("¿Qué quiere recordar?", placeholder="Ej.: Audiencia de imputación - proceso 123")
        tipo = st.selectbox("Tipo", almacen.TIPOS_EVENTO)
        nota = st.text_area("Nota (opcional)", height=80)
        if st.form_submit_button("Guardar recordatorio", type="primary", width="stretch"):
            try:
                almacen.agregar_evento(correo, sel, titulo, tipo, nota)
                st.success("Recordatorio guardado.")
                st.rerun()
            except ValueError as err:
                st.error(str(err))

    # calculadora de plazos
    with st.expander("🧮 Calculadora de plazos en días hábiles"):
        dias = st.number_input("¿Cuántos días hábiles cuenta el plazo?", min_value=0, max_value=365, value=10, step=1)
        vence = sumar_dias_habiles(sel, int(dias))
        st.markdown(f"Contando desde **{fecha_larga(sel)}** (ese día no se cuenta), el plazo vence el "
                    f"**{fecha_larga(vence)}**.")
        st.caption("Descuenta sábados, domingos y festivos de Colombia. Es una ayuda orientativa: confirme siempre "
                   "el término legal y el día de inicio del conteo que aplique a su caso.")
