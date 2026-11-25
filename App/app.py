"""Dashboard de Entidades de Control (Streamlit). Se ejecuta con: streamlit run app.py (desde la carpeta App)."""
import streamlit as st

import estilos
import paginas


def pagina_agente():
    """Carga segura de la página del agente analítico."""
    if hasattr(paginas, "pagina_agente"):
        paginas.pagina_agente()
    else:
        import agente_ui
        agente_ui.renderizar_agente(st.session_state.get("usuario", ""))
        paginas.pie()


st.set_page_config(page_title="Tablero de Entidades de Control", page_icon="⚖️", layout="wide",
                   initial_sidebar_state="auto")
estilos.aplicar(st.session_state.get("escala", "Normal"))

if not st.session_state.get("usuario"):
    st.navigation([st.Page(paginas.pagina_login, title="Ingreso", icon="🔒")], position="hidden").run()
else:
    pag = {
        "inicio": st.Page(paginas.pagina_inicio, title="Inicio", icon="🏠", url_path="inicio", default=True),
        "agente": st.Page(pagina_agente, title="Agente Analítico", icon="🤖", url_path="agente"),
        "consulta": st.Page(paginas.pagina_consulta, title="Consultar", icon="🔎", url_path="consultar"),
        "fiscalia": st.Page(paginas.pagina_fiscalia, title="Fiscalía", icon="⚖️", url_path="fiscalia"),
        "secop": st.Page(paginas.pagina_secop, title="Contratación", icon="📑", url_path="contratacion"),
        "sanciones": st.Page(paginas.pagina_sanciones, title="Sanciones", icon="🛡️", url_path="sanciones"),
        "contraloria": st.Page(paginas.pagina_contraloria, title="Contraloría", icon="🏛️", url_path="contraloria"),
        "calendario": st.Page(paginas.pagina_calendario, title="Calendario", icon="📅", url_path="calendario"),
        "favoritos": st.Page(paginas.pagina_favoritos, title="Favoritos", icon="⭐", url_path="favoritos"),
        "ayuda": st.Page(paginas.pagina_ayuda, title="Ayuda e informes", icon="📘", url_path="ayuda"),
    }
    paginas.PAGES.update(pag)
    paginas.barra_lateral()
    st.navigation(list(pag.values()), position="top").run()
