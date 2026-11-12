import os
import re
import pandas as pd
import datetime  # Capturar la fecha y hora de ejecución
import psutil


MAPA_DEPARTAMENTOS = {
    "BOGOTA": "BOGOTA, D. C.",
    "BOGOTA D.C.": "BOGOTA, D. C.",
    "BOGOTA, D.C.": "BOGOTA, D. C.",
    "GUAJIRA": "LA GUAJIRA",
    "VALLE": "VALLE DEL CAUCA",
    "SAN ANDRES": "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA",
}


def registrar_log(etapa: str):
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
            f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};{etapa};{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n"
        )


def quitar_tildes(serie: pd.Series) -> pd.Series:
    return (
        serie.astype("string")
        .str.normalize("NFKD")
        .str.encode("ascii", "ignore")
        .str.decode("ascii")
        .str.upper()
        .str.strip()
    )


def clasificar_capitulo(articulo: object) -> str:
    if pd.isna(articulo):
        return "NO REGISTRADO"
    match = re.match(r"^(\d+)", str(articulo).strip())
    if not match:
        return "NO REGISTRADO"
    num = int(match.group(1))
    if 397 <= num <= 403:
        return "Del Peculado"
    if num == 404:
        return "De La Concusion"
    if 405 <= num <= 407:
        return "Del Cohecho"
    if 408 <= num <= 410:
        return "De La Celebracion Indebida De Contratos"
    if num == 411:
        return "Del Trafico De Influencias"
    if num == 412:
        return "Del Enriquecimiento Ilicito"
    if 413 <= num <= 415:
        return "Del Prevaricato"
    if 416 <= num <= 424:
        return "Del Abuso De Autoridad Y Otras Infracciones"
    if 425 <= num <= 428:
        return "De La Usurpacion Y Abuso De Funciones Publicas"
    if 429 <= num <= 430:
        return "De Los Delitos Contra Los Servidores Publicos"
    if 431 <= num <= 434:
        return "De La Utilizacion Indebida De Informacion Y De Influencias Derivadas Del Ejercicio De Funcion Publica"
    return "NO REGISTRADO"


def normalizar_dane_5(serie: pd.Series) -> pd.Series:
    limpia = serie.astype("string").str.replace(r"\D", "", regex=True)

    def _convertir(val):
        if pd.isna(val) or val == "":
            return pd.NA
        if len(val) in (4, 5):
            return val.zfill(5)
        if len(val) in (7, 8):
            return val.zfill(8)[:5]
        return val[:5].zfill(5)

    return limpia.map(_convertir)


def transformar_datos_policia(ruta_entrada: str, ruta_salida: str):
    print("Iniciando transformación de datos (Capa Silver - Policía Nacional)...")
    registrar_log("Transformando datos Policia capturas")

    if not os.path.exists(ruta_entrada):
        print(f"Error: No se encontró el archivo crudo en {ruta_entrada}")
        return None

    try:
        df = pd.read_csv(ruta_entrada, dtype=str)
        print(f"Registros cargados desde Bronze: {len(df)}")

        # Limpieza inicial de filas vacías y duplicados exactos
        df = df.dropna(how="all")
        df = df.drop_duplicates().copy()

        # Estandarizar nombres de columnas
        df.columns = [col.strip().lower().replace(" ", "_").replace(".", "") for col in df.columns]

        # Reemplazar marcadores de vacío por nulos
        df = df.replace(["Sin Información", "SIN INFORMACION", "NO REPORTADO", "NO REGISTRADO", "-", ""], pd.NA)

        # Normalizar departamento y municipio sin tildes
        if "departamento" in df.columns:
            df["departamento"] = quitar_tildes(df["departamento"]).replace(MAPA_DEPARTAMENTOS)
            df = df.rename(columns={"departamento": "departamento_hecho"})

        if "municipio" in df.columns:
            df["municipio"] = (
                quitar_tildes(df["municipio"])
                .str.replace(r"\s*\(CT\)$", "", regex=True)
                .str.strip()
            )
            df = df.rename(columns={"municipio": "municipio_hecho"})

        # Normalizar código DANE municipal a 5 dígitos (estándar cruzable con Fiscalía)
        if "codigo_dane" in df.columns:
            df["cod_dane_hecho"] = normalizar_dane_5(df["codigo_dane"])
            df = df.drop(columns=["codigo_dane"])
        elif "cod_dane_hecho" in df.columns:
            df["cod_dane_hecho"] = normalizar_dane_5(df["cod_dane_hecho"])

        # Parsear fechas y extraer año y mes del hecho
        if "fecha_hecho" in df.columns:
            fechas = pd.to_datetime(df["fecha_hecho"], format="%d/%m/%Y", errors="coerce")
            faltantes = fechas.isna() & df["fecha_hecho"].notna()
            if faltantes.any():
                fechas.loc[faltantes] = pd.to_datetime(df.loc[faltantes, "fecha_hecho"], errors="coerce")
            df["fecha_hecho"] = fechas.dt.strftime("%Y-%m-%d")
            df["año_hecho"] = fechas.dt.year.astype("Int64")
            df["mes_hecho"] = fechas.dt.month.astype("Int64")
            fuera_rango = df["año_hecho"].notna() & ~df["año_hecho"].between(2010, 2030)
            df.loc[fuera_rango, ["fecha_hecho", "año_hecho", "mes_hecho"]] = pd.NA

        # Extraer artículo del Código Penal, delito limpio y capítulo del Título XV
        col_conducta = "descripcion_conducta_captura" if "descripcion_conducta_captura" in df.columns else "delito"
        conducta_norm = quitar_tildes(df[col_conducta])
        df["articulo"] = (
            conducta_norm.str.extract(r"(?:ARTICULO|ART\.?)\s*(\d+\s*[A-Z]?)", expand=False)
            .str.replace(" ", "", regex=False)
        )
        df["delito"] = (
            conducta_norm.str.replace(r"^(?:ARTICULO|ART\.?)\s*\d+\s*[A-Z]?\.?\s*", "", regex=True)
            .str.strip()
            .fillna("NO REGISTRADO")
        )
        if "descripcion_conducta_captura" in df.columns:
            df = df.drop(columns=["descripcion_conducta_captura"])

        df["capitulo_delito"] = df["articulo"].map(clasificar_capitulo)
        df["titulo_delito"] = "Delitos Contra La Administracion Publica"
        df["categoria_delito"] = df["capitulo_delito"].map(
            lambda cap: "Contra Servidores Publicos"
            if cap == "De Los Delitos Contra Los Servidores Publicos"
            else "Corrupcion Y Funcion Publica"
        )

        # Normalizar perfil del capturado (género y grupo etario)
        for col in ["genero", "grupo_etario"]:
            if col in df.columns:
                df[col] = quitar_tildes(df[col]).fillna("NO REGISTRADO")
                df[col] = df[col].replace(["NAN", "NONE", "NAT", "<NA>"], "NO REGISTRADO")

        # Convertir cantidad a numérico entero
        if "cantidad" in df.columns:
            df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(1).astype(int)
        else:
            df["cantidad"] = 1

        # Eliminar duplicados remanentes tras la estandarización de textos y códigos
        df = df.drop_duplicates().copy()

        carpeta = os.path.dirname(ruta_salida)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        df.to_csv(ruta_salida, index=False, encoding="utf-8")
        print(f"¡Transformación exitosa! Datos limpios almacenados en {ruta_salida}")
        print(f"Registros resultantes en Silver: {len(df)}")
        return df

    except Exception as e:
        print(f"Error en la transformación de la Capa Silver (Policía): {e}")
        return None


if __name__ == "__main__":
    transformar_datos_policia("data/bronze/policia_capturas_raw.csv", "data/silver/policia_capturas_clean.csv")
