"""Componente de interfaz gráfica (UI) para el Agente Analítico de Entidades de Control."""
from __future__ import annotations

import html
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Acceso al core del agente y estilos
RUTA_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUTA_BASE / "src"))

try:
    from agente.agente_entidades import AgenteEntidadesControl, fmt_dinero, fmt_numero
except ImportError:
    from src.agente.agente_entidades import AgenteEntidadesControl, fmt_dinero, fmt_numero

import datos
import estilos
from estilos import AZUL, AZUL_OSC, AMARILLO, ROJO

VERDE = "#00875A"


def consultar_agente(pregunta: str, usar_ia: bool = True, modelo_ia: Optional[str] = None) -> Dict[str, Any]:
    """Consulta al agente a través de la API si está disponible, o directamente vía Python."""
    if datos.fuente_datos() == "api":
        import requests
        try:
            url = f"{datos.api_url()}/agente/consulta"
            params = {"q": pregunta, "usar_ia": usar_ia}
            if modelo_ia:
                params["modelo"] = modelo_ia
            resp = requests.get(url, params=params, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                graficas = {}
                for k, g_info in data.get("graficas", {}).items():
                    fig_dict = g_info.get("figura") or g_info.get("fig") or {}
                    fig = go.Figure(fig_dict)
                    graficas[k] = {
                        "titulo": g_info.get("titulo", k),
                        "descripcion": g_info.get("descripcion", ""),
                        "fig": fig,
                    }
                data["graficas"] = graficas
                return data
        except Exception:
            pass  # Fallback a ejecución local si la API no responde

    # Ejecución directa local (warehouse.db o Gold CSVs)
    agente = AgenteEntidadesControl()
    return agente.consultar(pregunta, usar_ia=usar_ia, modelo_ia=modelo_ia)


def renderizar_agente(correo_usuario: str = "") -> None:
    """Renderiza la pantalla completa del Agente Analítico con soporte de IA (Ollama)."""
    # Estado de sesión para la consulta
    if "agente_pregunta" not in st.session_state:
        st.session_state["agente_pregunta"] = "Muéstrame el panorama general y cruce de datos entre Fiscalía, Procuraduría y Contraloría"
    if "agente_resultado" not in st.session_state:
        st.session_state["agente_resultado"] = None

    # Verificación de Ollama
    ollama_online, modelos_ollama = AgenteEntidadesControl.verificar_ollama()

    st.markdown("""
        <div style="background: linear-gradient(120deg, #062A66 0%, #0A3D91 100%);
                    color: white; border-radius: 16px; padding: 1.5rem 1.8rem;
                    margin-bottom: 1.2rem; box-shadow: 0 6px 18px rgba(6,42,102,.25);">
            <div style="text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.82rem; color: #FFF6C7; font-weight: 700; margin-bottom: 0.3rem;">
                Inteligencia Analítica Interinstitucional (RAG + Ollama)
            </div>
            <h1 style="color: white; margin: 0 0 0.5rem 0; font-size: 1.9rem; font-weight: 800;">
                🤖 Agente de Integración de Entidades
            </h1>
            <p style="margin: 0; font-size: 1.05rem; opacity: 0.95; line-height: 1.4;">
                Consulte y cruce en un solo lugar la información penal de la <b>Fiscalía</b>, disciplinaria de la <b>Procuraduría</b>
                y fiscal de la <b>Contraloría</b> (junto con la contratación de <b>SECOP II</b>), asistido por un modelo de lenguaje local.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Panel de control de IA (Ollama Local)
    usar_ia = False
    modelo_elegido = None

    if ollama_online and modelos_ollama:
        with st.container(border=True):
            col_ia1, col_ia2 = st.columns([3, 2], vertical_alignment="center")
            with col_ia1:
                usar_ia = st.toggle("🧠 **Activar síntesis lógica con IA (Ollama Local)**", value=True, key="agente_toggle_ia")
            with col_ia2:
                idx_default = 0
                if "qwen2.5:1.5b" in modelos_ollama:
                    idx_default = modelos_ollama.index("qwen2.5:1.5b")
                modelo_elegido = st.selectbox(
                    "Modelo LLM local:",
                    options=modelos_ollama,
                    index=idx_default,
                    key="agente_sel_modelo",
                    help="qwen2.5:1.5b es ultrarrápido; llama3.1 ofrece razonamiento más extenso.",
                )
    else:
        st.info(
            "ℹ️ **Modo analítico clásico activo:** Ollama no responde en `localhost:11434`. "
            "Para habilitar la síntesis local, abra una terminal y ejecute `ollama serve`; "
            "si todavía no tiene el modelo, ejecute antes `ollama pull qwen2.5:1.5b`. "
            "Luego vuelva a cargar esta página. El análisis determinístico sigue disponible mientras tanto."
        )

    # Sugerencias rápidas
    sugerencias = AgenteEntidadesControl.obtener_sugerencias()
    st.markdown("**💡 Preguntas frecuentes recomendadas (haga clic para consultar):**")
    cols_sug = st.columns(len(sugerencias))
    for col, sug in zip(cols_sug, sugerencias):
        if col.button(f"{sug['icono']} {sug['titulo']}", width="stretch", key=f"sug_{sug['titulo']}"):
            st.session_state["agente_pregunta"] = sug["pregunta"]
            with st.spinner(f"Analizando datos de las 3 entidades{' con IA (' + modelo_elegido + ')' if usar_ia else ''}..."):
                st.session_state["agente_resultado"] = consultar_agente(sug["pregunta"], usar_ia=usar_ia, modelo_ia=modelo_elegido)
            st.rerun()

    # Formulario de pregunta abierta
    with st.form("form_agente"):
        st.markdown("### 💬 Pregúntele al Agente")
        c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
        pregunta_input = c1.text_input(
            "Escriba una pregunta, nombre de entidad o departamento:",
            value=st.session_state["agente_pregunta"],
            placeholder="Ej.: ¿Qué información hay sobre la Policía Nacional? o ¿Cómo está Antioquia en las 3 entidades?",
        )
        enviar = c2.form_submit_button("Consultar 🤖", type="primary", width="stretch")

    if enviar and pregunta_input.strip():
        st.session_state["agente_pregunta"] = pregunta_input.strip()
        with st.spinner(f"El Agente está cruzando la información{' con IA local' if usar_ia else ''}..."):
            st.session_state["agente_resultado"] = consultar_agente(pregunta_input.strip(), usar_ia=usar_ia, modelo_ia=modelo_elegido)
        st.rerun()

    # Si aún no hay resultado, inicializar
    if st.session_state["agente_resultado"] is None:
        with st.spinner("Inicializando agente con el panorama general..."):
            st.session_state["agente_resultado"] = consultar_agente(st.session_state["agente_pregunta"], usar_ia=usar_ia, modelo_ia=modelo_elegido)

    res = st.session_state["agente_resultado"]
    if not res:
        st.warning("No se pudo obtener respuesta del agente. Verifique que los datos estén cargados.")
        return

    alerta = res.get("alerta", {})
    kpis = res.get("kpis", [])
    narrativa = res.get("narrativa", "")
    graficas = res.get("graficas", {})
    fisc = res.get("fiscalia", {})
    proc = res.get("procuraduria", {})
    cont = res.get("contraloria", {})
    secop = res.get("secop", {})
    modo_ia = res.get("modo_ia", False)
    modelo_usado = res.get("modelo_usado", "")

    st.write("")

    # 1. Alerta Interinstitucional
    st.markdown(f"""
        <div style="background-color: white; border-left: 6px solid {alerta.get('color', AZUL)};
                    padding: 1rem 1.3rem; border-radius: 8px; margin-bottom: 1.2rem;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 1.15rem; font-weight: 700; color: #062A66;">
                    {alerta.get('emoji', '⚠️')} Nivel de Alerta Interinstitucional: <span style="color: {alerta.get('color', AZUL)};">{alerta.get('nivel', 'MODERADA')}</span>
                </span>
                <span style="background-color: {alerta.get('color', AZUL)}; color: white; padding: 3px 12px; border-radius: 12px; font-weight: 700; font-size: 0.9rem;">
                    Índice: {alerta.get('score', 0)}/100
                </span>
            </div>
            <p style="margin: 0.4rem 0 0.2rem 0; font-size: 0.98rem; color: #333;">
                {alerta.get('mensaje', '')}
            </p>
        </div>
    """, unsafe_allow_html=True)

    # 2. KPIs de las 3 entidades (+ SECOP II)
    if kpis:
        st.markdown("### 📊 Indicadores Consolidados de las Entidades")
        cols_kpi = st.columns(len(kpis))
        for col, k in zip(cols_kpi, kpis):
            with col:
                st.markdown(f"""
                    <div style="background: white; border: 1px solid #E2E8F0; border-radius: 10px;
                                padding: 1rem; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                        <div style="font-size: 1.4rem; margin-bottom: 0.2rem;">{k['icono']}</div>
                        <div style="font-size: 0.82rem; text-transform: uppercase; color: #5B6575; font-weight: 700;">{k['entidad']}</div>
                        <div style="font-size: 1.5rem; font-weight: 800; color: #0A3D91; margin: 0.2rem 0;">{k['valor']}</div>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #1B2433;">{k['etiqueta']}</div>
                        <div style="font-size: 0.78rem; color: #718096; margin-top: 0.2rem;">{k['subtexto']}</div>
                    </div>
                """, unsafe_allow_html=True)

    st.write("")

    # 3. Narrativa analítica del Agente (con badge si fue generada con IA)
    with st.container(border=True):
        if modo_ia:
            st.markdown(
                f'<div style="margin-bottom:0.8rem;">'
                f'<span style="background-color: #E6F4EA; color: #137333; font-weight: 700; '
                f'padding: 4px 12px; border-radius: 14px; font-size: 0.88rem; border: 1px solid #A8DAB5;">'
                f'✨ Respuesta sintetizada con IA (Ollama {modelo_usado})</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown(narrativa)

    st.write("")

    # 4. Sección de Gráficas Específicas Dinámicas
    st.markdown("### 📈 Visualizaciones Específicas Dinámicas")
    st.caption("Seleccione qué aspecto específico desea inspeccionar en detalle con gráficas interactivas:")

    if graficas:
        opciones_graficas = {k: v["titulo"] for k, v in graficas.items()}
        sel_clave = st.selectbox(
            "Seleccione la visualización:",
            options=list(opciones_graficas.keys()),
            format_func=lambda k: f"📊 {opciones_graficas[k]} — {graficas[k].get('descripcion', '')}",
        )

        if sel_clave and sel_clave in graficas:
            g_sel = graficas[sel_clave]
            st.plotly_chart(g_sel["fig"], use_container_width=True)
            st.info(f"ℹ️ **Explicación técnica:** {g_sel.get('descripcion', '')}")
    else:
        st.info("No hay gráficas disponibles para este criterio específico.")

    st.write("")

    # 5. Desglose detallado por entidad (Tabs)
    st.markdown("### 📋 Registro Detallado por Entidad")
    t1, t2, t3, t4 = st.tabs([
        "⚖️ Fiscalía General",
        "🛡️ Procuraduría General",
        "🏛️ Contraloría General",
        "📑 Contratación (SECOP II)",
    ])

    with t1:
        st.markdown("#### Procesos Penales de la Fiscalía")
        if fisc.get("departamento_info"):
            di = fisc["departamento_info"]
            st.success(f"**Departamento consultado:** {di['departamento']} | Total procesos: {fmt_numero(di['total_procesos'])} | Procesos activos: {fmt_numero(di['procesos_activos'])} ({di['pct_activos']}%)")
        if fisc.get("top_delitos"):
            st.markdown("**Delitos más investigados por corrupción y administración pública:**")
            df_del = pd.DataFrame(fisc["top_delitos"])
            st.dataframe(df_del.rename(columns={"delito": "Delito", "articulo": "Artículo", "capitulo_delito": "Capítulo", "total": "Total Registros"}), use_container_width=True, hide_index=True)
        else:
            st.write("Sin registros adicionales de Fiscalía.")

    with t2:
        st.markdown("#### Sanciones Disciplinarias de la Procuraduría")
        if proc.get("coincidencias"):
            st.write(f"Se encontraron **{len(proc['coincidencias'])} sanciones** vinculadas a la búsqueda:")
            df_proc = pd.DataFrame(proc["coincidencias"])
            cols_ver = [c for c in ["nombre", "cargo", "entidad", "departamento", "municipio", "sanciones", "duracion", "fecha_efectos"] if c in df_proc.columns]
            st.dataframe(df_proc[cols_ver], use_container_width=True, hide_index=True)
        elif proc.get("entidades_top"):
            st.markdown("**Entidades con mayor volumen de sanciones a nivel nacional:**")
            df_top = pd.DataFrame(proc["entidades_top"])
            st.dataframe(df_top, use_container_width=True, hide_index=True)
        else:
            st.write("Sin coincidencias en sanciones disciplinarias.")

    with t3:
        st.markdown("#### Auditorías y Hallazgos de la Contraloría")
        if cont.get("coincidencias"):
            st.write(f"Se identificaron **{len(cont['coincidencias'])} registros de auditoría**:")
            df_cont = pd.DataFrame(cont["coincidencias"])
            st.dataframe(df_cont.rename(columns={
                "nombre": "Entidad Auditada", "registros": "Auditorías",
                "fiscales": "Hallazgos Fiscales", "penales": "Traslados Penales",
                "disciplinarios": "Disciplinarios", "administrativos": "Administrativos",
                "cuantia": "Cuantía ($ COP)",
            }), use_container_width=True, hide_index=True)
        elif cont.get("top_entidades_cuantia"):
            st.markdown("**Entidades con mayor cuantía económica observada:**")
            df_top_cuan = pd.DataFrame(cont["top_entidades_cuantia"])
            st.dataframe(df_top_cuan.rename(columns={"nombre": "Entidad Auditada", "cuantia": "Cuantía ($ COP)", "fiscales": "Hallazgos Fiscales", "penales": "Penales"}), use_container_width=True, hide_index=True)
        else:
            st.write("Sin hallazgos específicos registrados para este criterio.")

    with t4:
        st.markdown("#### Procesos de Contratación Pública en SECOP II")
        if secop.get("coincidencias"):
            df_secop = pd.DataFrame(secop["coincidencias"])
            st.dataframe(df_secop.rename(columns={
                "id_proceso": "ID Proceso", "referencia": "Referencia",
                "entidad": "Entidad", "proveedor": "Proveedor Adjudicado",
                "modalidad": "Modalidad", "valor_adjudicado": "Valor",
                "fecha_publicacion": "Fecha Publicación",
            }), use_container_width=True, hide_index=True)
        else:
            st.info("Sin contratos adjudicados directamente en la muestra disponible de SECOP II.")

    # 6. Descarga del Informe Analítico
    st.write("")
    informe_texto = (
        f"# INFORME ANALÍTICO DE INTEGRACIÓN DE ENTIDADES DE CONTROL\n\n"
        f"Fecha de consulta: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}\n"
        f"Usuario: {correo_usuario or 'Institucional'}\n"
        f"Consulta: {res.get('pregunta', '')}\n"
        f"Modo: {'IA Local (Ollama - ' + str(modelo_usado) + ')' if modo_ia else 'Motor Analítico Determinístico'}\n\n"
        f"Nivel de Alerta: {alerta.get('nivel', '')} ({alerta.get('score', 0)}/100)\n\n"
        f"{narrativa}\n"
    )
    st.download_button(
        "📥 Descargar Dictamen Analítico (.md)",
        data=informe_texto,
        file_name=f"informe_agente_control_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    )
