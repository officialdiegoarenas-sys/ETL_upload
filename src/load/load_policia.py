import os
import pandas as pd
import datetime  # Capturar la fecha y hora de ejecución
import psutil


def _fmt(valor: int) -> str:
    return f"{int(valor):,}".replace(",", ".")


def _generar_informe_conclusiones(
    df: pd.DataFrame,
    por_depto: pd.DataFrame,
    top_delitos: pd.DataFrame,
    por_año: pd.DataFrame,
    perfil: pd.DataFrame,
    ruta_conclusiones: str,
):
    total_registros = len(df)
    total_capturas = int(df["cantidad"].sum()) if total_registros else 0

    df_corrupcion = df[df["categoria_delito"] == "Corrupcion Y Funcion Publica"]
    capturas_corrupcion = int(df_corrupcion["cantidad"].sum()) if len(df_corrupcion) else 0
    capturas_servidores = total_capturas - capturas_corrupcion
    pct_corrupcion = (capturas_corrupcion / total_capturas * 100) if total_capturas else 0.0
    pct_servidores = (capturas_servidores / total_capturas * 100) if total_capturas else 0.0

    # Top departamentos general y en corrupción propia
    top_depto_gen = por_depto.iloc[0]["departamento_hecho"] if len(por_depto) else "NO DISPONIBLE"
    top_depto_gen_val = int(por_depto.iloc[0]["total_capturas"]) if len(por_depto) else 0

    por_depto_corr = por_depto.sort_values("capturas_corrupcion", ascending=False)
    top_depto_corr = por_depto_corr.iloc[0]["departamento_hecho"] if len(por_depto_corr) else "NO DISPONIBLE"
    top_depto_corr_val = int(por_depto_corr.iloc[0]["capturas_corrupcion"]) if len(por_depto_corr) else 0

    # Top delitos de corrupción funcional y contractual
    top_corr = top_delitos[top_delitos["categoria_delito"] == "Corrupcion Y Funcion Publica"]
    lineas_top_corr = []
    for _, fila in top_corr.head(5).iterrows():
        lineas_top_corr.append(
            f"- **Art. {fila['articulo']} - {fila['delito']}** ({fila['capitulo_delito']}): **{_fmt(fila['total_capturas'])} capturas**."
        )

    # Capturas específicas por celebración indebida de contratos y peculado
    cap_contratos = int(
        df[df["capitulo_delito"] == "De La Celebracion Indebida De Contratos"]["cantidad"].sum()
    )
    cap_peculado = int(df[df["capitulo_delito"] == "Del Peculado"]["cantidad"].sum())
    cap_cohecho = int(df[df["capitulo_delito"] == "Del Cohecho"]["cantidad"].sum())
    cap_concusion = int(df[df["capitulo_delito"] == "De La Concusion"]["cantidad"].sum())

    # Año con más capturas de corrupción
    if len(df_corrupcion) and df_corrupcion["año_hecho"].notna().any():
        año_corr = (
            df_corrupcion.groupby("año_hecho")["cantidad"]
            .sum()
            .reset_index()
            .sort_values("cantidad", ascending=False)
            .iloc[0]
        )
        mejor_año_txt = f"**{int(año_corr['año_hecho'])}** (con **{_fmt(año_corr['cantidad'])} capturas**)"
    else:
        mejor_año_txt = "**NO DISPONIBLE**"

    carpeta = os.path.dirname(ruta_conclusiones)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    with open(ruta_conclusiones, "w", encoding="utf-8") as f:
        f.write("# Conclusiones del Análisis de Datos (Policía Nacional - DIJIN) - Proyecto Entidades de Control\n\n")
        f.write("## 1. Resumen Ejecutivo y Separación del Fenómeno Operativo\n\n")
        f.write(
            f"A partir de la extracción en vivo desde la API oficial de **Datos Abiertos (`datos.gov.co`, dataset `3jdh-nmwu` - Reporte Capturas Policía Nacional)**, "
            f"se aislaron las conductas pertenecientes al **Título XV del Código Penal (Delitos contra la Administración Pública, Artículos 397 al 434)**, "
            f"consolidando **{_fmt(total_registros)} registros depurados** equivalentes a **{_fmt(total_capturas)} capturas operativas** entre 2010 y 2026.\n\n"
        )
        f.write("Al igual que ocurrió en el módulo de la Procuraduría (SIRI), el primer gran hallazgo analítico consiste en **separar la operatividad de calle de los delitos de corrupción y contratación pública**:\n\n")
        f.write(
            f"- **Delitos contra los Servidores Públicos (Arts. 429 y 430 - Violencia y obstrucción):** Representan **{_fmt(capturas_servidores)} capturas ({pct_servidores:.1f}%)**. Son procedimientos policivos en flagrancia por agresiones a uniformados o funcionarios.\n"
        )
        f.write(
            f"- **Delitos de Corrupción, Función Pública y Contratación (Arts. 397 al 428 y 431 al 434):** Representan **{_fmt(capturas_corrupcion)} capturas ({pct_corrupcion:.1f}%)**, que constituyen el núcleo de interés investigativo para cruzar con la Fiscalía General de la Nación, la Contraloría y el SECOP.\n\n"
        )

        f.write("## 2. Radiografía de las Capturas por Corrupción y Contratación Estatal\n\n")
        f.write("Dentro del bloque de corrupción administrativa y delitos funcionales, las capturas de la Policía Nacional (DIJIN) se concentran en cuatro modalidades críticas:\n\n")
        f.write(f"1. **Cohecho (Sobornos - Arts. 405 al 407):** **{_fmt(cap_cohecho)} capturas**, liderado por *Cohecho por dar u ofrecer (Art. 407)*.\n")
        f.write(f"2. **Peculado (Detrimento y apropiación del erario - Arts. 397 al 403A):** **{_fmt(cap_peculado)} capturas**, encabezado por *Peculado por apropiación (Art. 397)* y *Omisión del agente retenedor o recaudador (Art. 402)*.\n")
        f.write(f"3. **Concusión (Exigencias ilegales por funcionarios - Art. 404):** **{_fmt(cap_concusion)} capturas**.\n")
        f.write(f"4. **Celebración Indebida de Contratos (Arts. 408 al 410A):** **{_fmt(cap_contratos)} capturas** directas de contratistas y ordenadores del gasto por *Contrato sin cumplimiento de requisitos legales (Art. 410)*, *Interés indebido en la celebración de contratos (Art. 409)* y *Violación del régimen de inhabilidades e incompatibilidades (Art. 408)*.\n\n")

        if lineas_top_corr:
            f.write("### Top 5 conductas de corrupción con más capturas:\n")
            f.write("\n".join(lineas_top_corr) + "\n\n")

        f.write("## 3. Distribución Geográfica y Evolución Temporal\n\n")
        f.write(
            f"- **Concentración Territorial General:** El territorio con mayor volumen total de capturas del Título XV es **{top_depto_gen}** con **{_fmt(top_depto_gen_val)} capturas**.\n"
        )
        f.write(
            f"- **Foco Territorial de Corrupción:** Al filtrar exclusivamente los delitos de corrupción y función pública, lidera **{top_depto_corr}** con **{_fmt(top_depto_corr_val)} capturas**, seguido de los principales centros administrativos y portuarios del país.\n"
        )
        f.write(
            f"- **Pico Histórico Operativo:** El año con mayor número de capturas por corrupción administrativa fue {mejor_año_txt}.\n\n"
        )

        f.write("## 4. Integración con Fiscalía, Procuraduría y Contraloría (Valor para el Proyecto)\n\n")
        f.write("La estandarización realizada en la Capa Silver (`cod_dane_hecho` a 5 dígitos, `departamento_hecho` sin tildes, extracción de `articulo` y homologación de los 11 capítulos del Título XV del Código Penal) permite conectar directamente este módulo con el resto del proyecto:\n\n")
        f.write("1. **Embudo Operativo Policía vs. Fiscalía:** Mientras la Fiscalía registra cientos de miles de noticias criminales por *Celebración Indebida de Contratos* y *Peculado*, las capturas efectivas materializadas por la Policía Nacional (DIJIN) son altamente selectivas, evidenciando que los delitos de cuello blanco rara vez se capturan en flagrancia y requieren órdenes judiciales tras largas auditorías.\n")
        f.write("2. **Cruce con Procuraduría (SIRI) y SECOP:** Las capturas por el **Artículo 408 (Violación del régimen de inhabilidades e incompatibilidades)** confirman penalmente el escenario detectado en el módulo de la Procuraduría: personas inhabilitadas que intentan contratar o posesionarse ilegalmente con el Estado.\n")
        f.write("3. **Cruce con Contraloría:** Los departamentos y vigencias con mayores hallazgos con incidencia penal y fiscal en la Contraloría sirven como insumo preventivo para focalizar las unidades investigativas de la DIJIN en delitos de *Peculado por apropiación (Art. 397)*.\n")


def generar_gold_policia(
    ruta_entrada: str,
    carpeta_gold: str,
    ruta_conclusiones: str = "conclusiones_policia.md",
):
    print("Iniciando procesamiento de la Capa Gold (Policía Nacional - Capturas)...")

    try:
        nombre_equipo = os.getlogin()
    except Exception:
        nombre_equipo = "Desconocido"
    ruta_ejecucion = os.path.abspath(__file__)
    ram_uso = psutil.virtual_memory().percent
    try:
        temp_uso = f"{psutil.sensors_temperatures()['coretemp'][0].current}°C"
    except Exception:
        temp_uso = "N/A"

    os.makedirs("logs", exist_ok=True)
    with open("logs/logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(
            f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Integrando datos Policia capturas;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n"
        )

    if not os.path.exists(ruta_entrada):
        print(f"Error: No se encontró el archivo en la capa Silver: {ruta_entrada}")
        return None

    try:
        df = pd.read_csv(ruta_entrada, dtype={"cod_dane_hecho": str, "articulo": str})
        print(f"Registros cargados desde Silver: {len(df)}")
        os.makedirs(carpeta_gold, exist_ok=True)

        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)
        df["es_corrupcion"] = (df["categoria_delito"] == "Corrupcion Y Funcion Publica").astype(int) * df["cantidad"]

        # 1. Capturas por año y capítulo del delito
        por_año = (
            df.dropna(subset=["año_hecho"])
            .groupby(["año_hecho", "capitulo_delito"], as_index=False)
            .agg(
                total_capturas=("cantidad", "sum"),
                total_registros=("cantidad", "count"),
            )
            .sort_values(["año_hecho", "total_capturas"], ascending=[True, False])
        )
        por_año.to_csv(os.path.join(carpeta_gold, "policia_capturas_año_capitulo_gold.csv"), index=False, encoding="utf-8")

        # 2. Capturas por departamento (total y corrupción propia)
        por_depto = (
            df.dropna(subset=["departamento_hecho"])
            .groupby("departamento_hecho", as_index=False)
            .agg(
                total_capturas=("cantidad", "sum"),
                capturas_corrupcion=("es_corrupcion", "sum"),
            )
        )
        por_depto["pct_corrupcion"] = (
            por_depto["capturas_corrupcion"] / por_depto["total_capturas"] * 100
        ).round(2)
        total_nac = por_depto["total_capturas"].sum()
        por_depto["pct_nacional"] = (
            (por_depto["total_capturas"] / total_nac * 100).round(2) if total_nac > 0 else 0.0
        )
        por_depto = por_depto.sort_values("total_capturas", ascending=False)
        por_depto.to_csv(os.path.join(carpeta_gold, "policia_capturas_departamento_gold.csv"), index=False, encoding="utf-8")

        # 3. Ranking de delitos y artículos con más capturas
        top_delitos = (
            df.groupby(["articulo", "delito", "capitulo_delito", "categoria_delito"], as_index=False)
            .agg(total_capturas=("cantidad", "sum"))
            .sort_values("total_capturas", ascending=False)
        )
        suma_delitos = top_delitos["total_capturas"].sum()
        top_delitos["porcentaje"] = (
            (top_delitos["total_capturas"] / suma_delitos * 100).round(2) if suma_delitos > 0 else 0.0
        )
        top_delitos.to_csv(os.path.join(carpeta_gold, "policia_top_delitos_gold.csv"), index=False, encoding="utf-8")

        # 4. Perfil demográfico de los capturados (género y grupo etario por categoría)
        perfil = (
            df.groupby(["categoria_delito", "genero", "grupo_etario"], as_index=False)
            .agg(total_capturas=("cantidad", "sum"))
            .sort_values("total_capturas", ascending=False)
        )
        suma_perfil = perfil["total_capturas"].sum()
        perfil["porcentaje"] = (
            (perfil["total_capturas"] / suma_perfil * 100).round(2) if suma_perfil > 0 else 0.0
        )
        perfil.to_csv(os.path.join(carpeta_gold, "policia_perfil_capturados_gold.csv"), index=False, encoding="utf-8")

        # Generar documento de conclusiones ejecutivas si se indica ruta
        if ruta_conclusiones:
            _generar_informe_conclusiones(df, por_depto, top_delitos, por_año, perfil, ruta_conclusiones)

        print(f"¡Capa Gold de Policía generada con éxito en {carpeta_gold}!")
        print("\n--- Vista previa: capturas por departamento ---")
        print(por_depto.head(5))
        print("\n--- Vista previa: top delitos ---")
        print(top_delitos.head(5))

        return por_depto

    except Exception as e:
        print(f"Error procesando la Capa Gold de Policía: {e}")
        return None


if __name__ == "__main__":
    generar_gold_policia(
        "data/silver/policia_capturas_clean.csv",
        "data/gold",
        "conclusiones_policia.md",
    )
