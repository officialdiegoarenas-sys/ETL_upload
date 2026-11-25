"""Pantallas del dashboard."""
from __future__ import annotations

import html
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import acceso
import agente_ui
import almacen
import calendario
import datos
import estilos
import reportes
from estilos import fmt, fmt_cop, fmt_pct

PAGES: dict = {}          # lo llena app.py con los objetos st.Page (para los enlaces)
RAIZ = datos.BASE_DIR

AVISO_LEGAL = ("Fuente: datos abiertos de datos.gov.co (Fiscalía, SECOP II, Procuraduría y Contraloría) procesados por el pipeline ETL del proyecto. "
               "Las cifras son descriptivas y no constituyen determinaciones jurídicas.")


def correo() -> str:
    return st.session_state.get("usuario", "")


def encabezado(titulo: str, subtitulo: str, sup: str = "Tablero de Entidades de Control") -> None:
    st.markdown(f'<div class="hero"><div class="sup">{sup}</div><h1>{titulo}</h1><p>{subtitulo}</p></div>', unsafe_allow_html=True)


def pie() -> None:
    st.markdown(f'<div class="pie">{AVISO_LEGAL}</div>', unsafe_allow_html=True)


def _fecha(dt: datetime | None) -> str:
    return "sin datos" if dt is None else f"{calendario.fecha_larga(dt.date())}, {dt:%H:%M}"


# Acceso
def pagina_login() -> None:
    encabezado("Bienvenido(a)", "Consulte en un solo lugar los datos de la Fiscalía, la contratación pública y las sanciones disciplinarias.",
               "Ingreso institucional")
    _, centro, _ = st.columns([1, 2, 1])
    with centro:
        with st.form("login"):
            st.markdown("### Ingrese con su correo institucional")
            mail = st.text_input("Correo", placeholder="nombre@fiscalia.gov.co", autocomplete="email")
            clave = st.text_input("Contraseña", type="password", placeholder="Por ahora puede ser cualquiera")
            if st.form_submit_button("Ingresar", type="primary", width="stretch"):
                ok, msg = acceso.validar_acceso(mail, clave)
                if ok:
                    st.session_state["usuario"] = acceso.normalizar_correo(mail)
                    st.rerun()
                else:
                    st.error(msg)
        st.markdown('<div class="aviso">🔒 Versión de demostración: el acceso solo valida que el correo contenga «fiscalia». '
                    'La contraseña no se guarda.</div>', unsafe_allow_html=True)
    pie()


def barra_lateral() -> None:
    with st.sidebar:
        st.markdown(f"**👤 {acceso.nombre_para_mostrar(correo())}**")
        st.caption(correo())
        st.select_slider("🔎 Tamaño de letra", options=list(estilos.ESCALAS), key="escala")
        st.markdown("---")
        ult = datos.ultima_actualizacion()
        st.caption(f"📅 Datos actualizados: {_fecha(ult)}")
        if st.button("Cerrar sesión", width="stretch"):
            for k in ("usuario", "cal_anio", "cal_mes", "cal_sel"):
                st.session_state.pop(k, None)
            st.rerun()


# Inicio
def _kpis() -> list[tuple[str, str, str, str]]:
    cifras = []
    try:
        et = reportes.tabla("etapa")
        total = int(et["total"].sum())
        activos = int(et[et["estado"] == "Activo"]["total"].sum())
        cifras.append((fmt(total), "Procesos en la Fiscalía", "Delitos contra la administración pública registrados", ""))
        cifras.append((fmt_pct(activos / total * 100), "Siguen activos", f"{fmt(activos)} procesos con trámite abierto", "am"))
    except datos.DatoNoDisponible:
        pass
    try:
        se = reportes.tabla("secop")
        cifras.append((fmt(se["total_procesos"].sum()), "Procesos de contratación", "Muestra de SECOP II (no es el total del país)", ""))
    except datos.DatoNoDisponible:
        pass
    try:
        pr = reportes.tabla("procuraduria")
        civ = pr[~pr["fuerza_publica"]]
        cifras.append((fmt(civ["total_sanciones"].sum()), "Sanciones a servidores civiles", "Procuraduría, sin Policía ni Fuerzas Militares", "ro"))
    except datos.DatoNoDisponible:
        pass
    return cifras


def _historia() -> str | None:
    """Narrativa Y-PERO-POR LO TANTO calculada con los datos."""
    try:
        et = reportes.tabla("etapa")
        total = et["total"].sum()
        g = et.groupby("etapa")["total"].sum()
        top, pct = g.idxmax(), g.max() / total * 100
        act = et[et["estado"] == "Activo"]["total"].sum() / total * 100
    except datos.DatoNoDisponible:
        return None
    return (f"<b class='y'>Y</b> la Fiscalía registra <b>{fmt(total)}</b> procesos por delitos contra la administración pública, "
            f"<b class='p'>pero</b> el <b>{fmt(pct)} %</b> sigue en la etapa de <b>{top}</b> y solo el <b>{fmt(act)} %</b> tiene trámite abierto, "
            f"<b class='l'>por lo tanto</b> conviene empezar la revisión por los procesos activos en sus fases iniciales.")


def pagina_inicio() -> None:
    nombre = acceso.nombre_para_mostrar(correo()).split(" ")[0]
    hoy = date.today()
    encabezado(f"Buen día, {nombre}", f"Hoy es {calendario.fecha_larga(hoy)}. Aquí está lo más importante, explicado paso a paso.")

    st.markdown('<div class="aviso solo-movil" style="margin-bottom:.8rem">📱 <b>¿Busca el menú?</b> Toque el botón <b>»</b> '
                'arriba a la izquierda para cambiar de sección.</div>', unsafe_allow_html=True)
    historia = _historia()
    if historia:
        st.markdown(f'<div class="historia">{historia}</div>', unsafe_allow_html=True)
    else:
        st.warning("Aún no hay datos cargados. Ejecute el ETL (python main.py) y recargue esta página.")

    st.write("")
    cifras = _kpis()
    if cifras:
        st.markdown(estilos.rejilla_cifras(cifras), unsafe_allow_html=True)

    with st.form("buscar_inicio"):
        st.markdown("### 🔎 Consultar una persona o un proceso")
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        q = c1.text_input("Cédula, número de proceso o nombre de una contraloría", placeholder="Ej.: 1130456789,  2023-0272  o  Contraloría de Medellín")
        if c2.form_submit_button("Consultar", type="primary", width="stretch") and q.strip() and "consulta" in PAGES:
            st.session_state["consulta_q"] = q.strip()
            st.switch_page(PAGES["consulta"])

    st.markdown("### ¿Qué más quiere ver?")
    destinos = [("agente", "🤖", "Agente Analítico (3 Entidades)"), ("consulta", "🔎", "Consultar cédula o proceso"), ("fiscalia", "⚖️", "Procesos de la Fiscalía"), ("secop", "📑", "Contratación pública"),
                ("sanciones", "🛡️", "Sanciones disciplinarias"), ("contraloria", "🏛️", "Contraloría"), ("calendario", "📅", "Mi calendario"), ("favoritos", "⭐", "Mis favoritos")]
    cols = st.columns(len(destinos))
    for c, (clave, icono, texto) in zip(cols, destinos):
        if clave in PAGES:
            c.page_link(PAGES[clave], label=texto, icon=icono, width="stretch")

    izq, der = st.columns(2)
    with izq:
        st.markdown("### ⭐ Mis reportes frecuentes")
        favs = [reportes.POR_ID[f] for f in almacen.favoritos(correo()) if f in reportes.POR_ID]
        if favs:
            for r in favs[:5]:
                st.markdown(f"- {r.pregunta}")
            if "favoritos" in PAGES:
                st.page_link(PAGES["favoritos"], label="Abrir mis favoritos", icon="⭐")
        else:
            st.info("Aún no guardó ninguno. En cada gráfica verá el botón «☆ Guardar en favoritos».")
    with der:
        st.markdown("### 📅 Próximas fechas")
        prox = calendario.proximos_eventos(correo(), hoy, dias=45, maximo=4)
        if prox:
            st.markdown("".join(calendario.html_evento(d, e) for d, e in prox), unsafe_allow_html=True)
        else:
            st.info("No tiene recordatorios próximos.")
        if "calendario" in PAGES:
            st.page_link(PAGES["calendario"], label="Abrir calendario", icon="📅")
    pie()


# Secciones con reportes (una pestaña = una pregunta)
def _seccion(fuente: str, titulo: str, subtitulo: str) -> None:
    encabezado(titulo, subtitulo)
    lista = reportes.de_fuente(fuente)
    tabs = st.tabs([r.pregunta for r in lista])
    for tab, r in zip(tabs, lista):
        with tab:
            reportes.mostrar_reporte(r, correo(), ctx=fuente)
    pie()


def pagina_fiscalia() -> None:
    _seccion("fiscalia", "Procesos de la Fiscalía",
             "Procesos por delitos contra la administración pública. Elija una pregunta en las pestañas.")


def pagina_secop() -> None:
    _seccion("secop", "Contratación pública (SECOP II)",
             "Cómo y cuánto contratan las entidades del Estado. Cifras de una muestra de procesos publicados.")


def pagina_sanciones() -> None:
    _seccion("procuraduria", "Sanciones disciplinarias (Procuraduría)",
             "Qué entidades concentran más sanciones a sus servidores.")


def pagina_contraloria() -> None:
    _seccion("contraloria", "Contraloría: resultado de las auditorías",
             "Hallazgos de las auditorías de control fiscal a las contralorías del país.")


# Consulta por cédula / número de proceso (usa la API)
def _e(valor) -> str:
    return html.escape(str(valor or "").strip()) or "-"


def _cuadricula(filas) -> str:
    cuerpo = "".join(f"<div><small>{k}</small><br><b>{v}</b></div>" for k, v in filas)
    return f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:.5rem 1rem;margin-top:.5rem">{cuerpo}</div>'


def _tarjeta_sancion(r: dict) -> str:
    filas = [("Documento", f"{_e(r['tipo_identificacion'])} {_e(r['id_norm'])}"), ("Cargo", _e(r["cargo"])), ("Entidad", _e(r["entidad"])),
             ("Calidad", _e(r["calidad_persona"].title())), ("Sanción", _e(r["sanciones"])), ("Duración", _e(r["duracion"])),
             ("Efectos jurídicos desde", _e(r["fecha_efectos"])), ("Providencia", _e(r["providencia"])),
             ("N.º de proceso", _e(r["numero_proceso"])), ("N.º SIRI", _e(r["numero_siri"]))]
    return (f'<div class="evento fest"><div style="font-size:1.15rem;font-weight:800;color:#062A66">{_e(r["nombre"])}</div>'
            f'<small>Coincide por {_e(r["coincide_por"])}</small>{_cuadricula(filas)}</div>')


def _tarjeta_contrato(r: dict) -> str:
    filas = [("Proceso", _e(r["id_proceso"])), ("Referencia", _e(r["referencia"])), ("Entidad contratante", _e(r["entidad"])),
             ("Proveedor", f"{_e(r['proveedor'])} ({_e(r['nit_proveedor'])})"), ("Modalidad", _e(r["modalidad"])),
             ("Estado", _e(r["estado"])), ("Adjudicado", _e(r["adjudicado"])), ("Publicado", _e(r["fecha_publicacion"]))]
    return f'<div class="evento"><small>Coincide por {_e(r["coincide_por"])}</small>{_cuadricula(filas)}</div>'


def _tarjeta_contraloria(r: dict) -> str:
    filas = [("Auditorías", _e(r["registros"])), ("Vigencias", f"{_e(r['vigencia_desde'])} a {_e(r['vigencia_hasta'])}"),
             ("Hallazgos administrativos", _e(fmt(r["administrativos"]))), ("Disciplinarios", _e(fmt(r["disciplinarios"]))),
             ("Fiscales", _e(fmt(r["fiscales"]))), ("Penales", _e(fmt(r["penales"]))), ("Cuantía de hallazgos", _e(fmt_cop(r["cuantia"])))]
    return (f'<div class="evento etl"><div style="font-size:1.15rem;font-weight:800;color:#062A66">{_e(r["nombre"])}</div>'
            f'<small>Coincide por {_e(r["coincide_por"])}</small>{_cuadricula(filas)}</div>')


def pagina_consulta() -> None:
    encabezado("Consultar una persona, un proceso o una contraloría",
               "Escriba una cédula, un número de proceso o el nombre de una contraloría y vea de una vez qué registros hay.")
    with st.form("consulta"):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        q = c1.text_input("Cédula, número de proceso o nombre de una contraloría", value=st.session_state.pop("consulta_q", ""),
                          placeholder="Ej.: 1130456789,  2023-0272  o  Contraloría de Medellín")
        c2.form_submit_button("🔎 Consultar", type="primary", width="stretch")
    if not q.strip():
        st.markdown('<div class="aviso">Escriba un dato y pulse <b>Consultar</b>. Para cédulas y procesos se busca el dato exacto; '
                    'para contralorías basta con parte del nombre.</div>', unsafe_allow_html=True)
        pie()
        return
    try:
        res = datos.consultar(q)
    except (ValueError, datos.ApiNoDisponible, datos.DatoNoDisponible) as e:
        st.error(str(e))
        pie()
        return

    sanciones, contratos, contralorias = res["sanciones"], res["contratos"], res.get("contraloria", [])
    consulta_txt = html.escape(res["consulta"])
    if res["total"]:
        st.success(f"Encontramos **{res['total']} registro(s)** para «{consulta_txt}»: {len(sanciones)} en Procuraduría, "
                   f"{len(contratos)} en contratación pública (SECOP II) y {len(contralorias)} en Contraloría.")
    else:
        st.info(f"No encontramos registros para «{consulta_txt}» en las fuentes consultables (Procuraduría, SECOP II y Contraloría).")

    st.markdown("### 🛡️ Procuraduría: sanciones disciplinarias")
    st.markdown("".join(_tarjeta_sancion(r) for r in sanciones), unsafe_allow_html=True) if sanciones else st.write("Sin coincidencias en esta fuente.")
    st.markdown("### 📑 SECOP II: contratación pública")
    st.markdown("".join(_tarjeta_contrato(r) for r in contratos), unsafe_allow_html=True) if contratos else st.write("Sin coincidencias en esta fuente.")
    st.markdown("### 🏛️ Contraloría: resultado de las auditorías")
    st.markdown("".join(_tarjeta_contraloria(r) for r in contralorias), unsafe_allow_html=True) if contralorias else st.write("Sin coincidencias en esta fuente (se busca por el nombre de la contraloría).")

    st.markdown("### Fuente que todavía no se puede consultar")
    st.warning("**⚖️ Fiscalía:** los datos abiertos de la Fiscalía vienen *anonimizados* (códigos cifrados en lugar de cédula o radicado), "
               "por eso no se puede buscar una persona ni un proceso real en ellos. Para esta fuente se necesita acceso a los datos internos.")
    st.markdown('<div class="aviso">⚠️ <b>Importante:</b> que no aparezca un registro <b>no significa que la persona no tenga procesos</b>. '
                'Esta consulta no reemplaza un certificado de antecedentes ni la verificación directa con la entidad. '
                'La Procuraduría cubre toda su base pública a la fecha de actualización; SECOP II solo una muestra. '
                'La Contraloría trae resultados por entidad auditada, no por persona.</div>', unsafe_allow_html=True)
    pie()


def pagina_agente() -> None:
    agente_ui.renderizar_agente(correo())
    pie()


# Calendario, favoritos y ayuda
def pagina_calendario() -> None:
    encabezado("Mi calendario", "Anote audiencias, plazos y reuniones. Los festivos de Colombia y las fechas de actualización de datos ya aparecen solos.")
    calendario.mostrar_calendario(correo())
    pie()


def pagina_favoritos() -> None:
    encabezado("Mis favoritos", "Los reportes que guardó con la estrella, listos para consultar sin buscar.")
    favs = [reportes.POR_ID[f] for f in almacen.favoritos(correo()) if f in reportes.POR_ID]
    if not favs:
        st.info("Todavía no tiene reportes guardados. Entre a cualquier sección y pulse «☆ Guardar en favoritos» sobre la gráfica que quiera conservar.")
        c = st.columns(3)
        for col, clave, icono, texto in zip(c, ("fiscalia", "secop", "sanciones"), ("⚖️", "📑", "🛡️"),
                                              ("Procesos de la Fiscalía", "Contratación pública", "Sanciones")):
            if clave in PAGES:
                col.page_link(PAGES[clave], label=texto, icon=icono, width="stretch")
    for r in favs:
        with st.container(border=True):
            reportes.mostrar_reporte(r, correo(), ctx="fav")
    pie()


_INFORMES = [("Fiscalía", "conclusiones_fiscalia.md"), ("SECOP II", "conclusiones_secop_ii.md"),
             ("Procuraduría", "conclusiones_procuraduria.md"), ("Contraloría", "conclusiones_contraloria.md")]


def pagina_ayuda() -> None:
    encabezado("Ayuda e informes", "Cómo usar el tablero, de dónde salen los datos y las conclusiones de cada entidad.")
    st.markdown("### 🧭 Cómo usar el tablero en 3 pasos")
    st.markdown("1. **Elija una sección** en el menú superior (Fiscalía, Contratación, Sanciones).\n"
                "2. **Elija una pregunta** en las pestañas. Cada gráfica tiene un título que le dice la conclusión.\n"
                "3. **Pulse ☆** si quiere volver a ese reporte rápido: quedará en «Mis favoritos».")
    st.markdown("**¿Letra pequeña?** Use el control «Tamaño de letra» del menú lateral (en celular, el botón » arriba a la izquierda).")

    st.markdown("### 📚 Conclusiones por entidad")
    for nombre, archivo in _INFORMES:
        ruta = RAIZ / archivo
        with st.expander(nombre):
            if ruta.exists():
                st.markdown(ruta.read_text(encoding="utf-8"))
            else:
                st.info("Este informe aún no se ha generado.")

    st.markdown("### 🔧 Estado de los datos")
    est = datos.estado_pipeline()
    filas = [{"Módulo": m, "Última ejecución": f"{v['fecha']:%d/%m/%Y %H:%M}", "Resultado": "✅ Correcto" if v["ok"] else "⚠️ Con falla"}
             for m, v in est.items()]
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
    st.caption(f"Próxima actualización programada: {_fecha(datos.proxima_actualizacion())}. Fuente de datos del tablero: "
               f"{'API (FastAPI)' if datos.fuente_datos() == 'api' else 'capa Gold (archivos CSV)'}.")
    pie()
