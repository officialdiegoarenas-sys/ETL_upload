import sys
import os
import logging
import datetime
import socket
import psutil

# Ruta base del proyecto y carpeta src para los imports
RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(RUTA_BASE, 'src'))

# Los logs se guardan siempre dentro del proyecto
os.makedirs(os.path.join(RUTA_BASE, "logs"), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(RUTA_BASE, "logs", "pipeline.log"),
            encoding="utf-8"
        ),
        logging.StreamHandler(sys.stdout)
    ]
)

# Importaciones de Procuraduría
from extract.extract_procuraduria import extraer_datos_procuraduria
from transform.transform_procuraduria import transformar_datos_procuraduria
from load.load_procuraduria import procesar_capa_gold as generar_gold_procuraduria

# Importaciones de Contraloría
from extract.extract_contraloria import extraer_datos_contraloria
from transform.transform_contraloria import transformar_datos_contraloria
from load.load_contraloria import generar_dataset_contraloria

# Pipeline Fiscalía y SECOP
from pipeline.datos_fiscalia import ejecutar_pipeline_datos_fiscalia

# Data Warehouse SQLite
from data_warehouse import cargar_gold_al_warehouse


def ruta(*partes):
    return os.path.join(RUTA_BASE, *partes)


# ==========================================================
# MÓDULOS
# ==========================================================

def hay_conexion(host="www.datos.gov.co", puerto=443, espera=5):
    """Revisa rápido si se puede llegar al portal de datos abiertos."""
    try:
        socket.create_connection((host, puerto), timeout=espera).close()
        return True
    except OSError:
        return False


def modulo_fiscalia():
    if not hay_conexion():
        raise ConnectionError("Sin conexión a datos.gov.co, se omite.")
    ejecutar_pipeline_datos_fiscalia()


def buscar_fuente_contraloria():
    """
    Busca el CSV de Contraloría. Primero la variable de entorno
    CONTRALORIA_CSV, luego data/raw y por último la carpeta Descargas.
    """
    nombre = "Resultado_de_la_Ejecución_del_Plan_de_Vigilancia_y_Control_Fiscal"

    env = os.environ.get("CONTRALORIA_CSV")
    if env and os.path.isfile(env):
        return env

    carpetas = [
        ruta("data", "raw"),
        ruta("data"),
        os.path.join(os.path.expanduser("~"), "Downloads"),
        os.path.join(os.path.expanduser("~"), "Descargas"),
    ]

    for carpeta in carpetas:
        if not os.path.isdir(carpeta):
            continue
        for archivo in sorted(os.listdir(carpeta), reverse=True):
            if archivo.startswith(nombre) and archivo.endswith(".csv"):
                return os.path.join(carpeta, archivo)

    return None


def modulo_contraloria():
    fuente = buscar_fuente_contraloria()
    bronze = ruta("data", "bronze", "contraloria_raw.csv")
    silver = ruta("data", "silver", "contraloria_clean.csv")
    gold = ruta("data", "gold", "dataset_contraloria.csv")
    conclusiones = ruta("conclusiones_contraloria.md")

    if fuente is None:
        # Si ya hay bronze de una corrida anterior se sigue desde ahí
        if not os.path.isfile(bronze):
            raise FileNotFoundError(
                "No se encontró el CSV de Contraloría. Ponlo en data/raw "
                "o define la variable CONTRALORIA_CSV."
            )
        logging.warning("Sin CSV fuente, se usa el bronze existente.")
    else:
        logging.info("[Contraloría 1/3] Extrayendo: %s", fuente)
        extraer_datos_contraloria(fuente, bronze)

    logging.info("[Contraloría 2/3] Transformando datos...")
    df = transformar_datos_contraloria(bronze, silver)

    logging.info("[Contraloría 3/3] Generando dataset y conclusiones...")
    generar_dataset_contraloria(silver, gold, conclusiones)

    logging.info("Contraloría procesada: %s registros.", len(df))


def modulo_procuraduria():
    if not hay_conexion():
        raise ConnectionError("Sin conexión a datos.gov.co, se omite.")
    url = (
        "https://www.datos.gov.co/resource/iaeu-rcn6.csv"
        "?$limit=1000&$order=fecha_efectos_juridicos%20DESC"
    )
    bronze = ruta("data", "bronze", "procuraduria_raw.csv")
    silver = ruta("data", "silver", "procuraduria_clean.csv")
    gold = ruta("data", "gold", "resumen_procuraduria_gold.csv")

    if extraer_datos_procuraduria(url, bronze) is None:
        raise RuntimeError("Falló la capa Bronze de Procuraduría.")

    if transformar_datos_procuraduria(bronze, silver) is None:
        raise RuntimeError("Falló la capa Silver de Procuraduría.")

    if generar_gold_procuraduria(silver, gold) is None:
        raise RuntimeError("Falló la capa Gold de Procuraduría.")


def ejecutar_modulo(nombre, funcion):
    """
    Ejecuta un módulo sin que su error detenga el resto del pipeline.
    Devuelve True si terminó bien.
    """
    logging.info("--- INICIANDO MÓDULO %s ---", nombre)
    try:
        funcion()
        logging.info("Módulo %s terminado.", nombre)
        return True
    except Exception as error:
        logging.error(
            "Falló el módulo %s: %s: %s",
            nombre, type(error).__name__, str(error)[:300]
        )
        return False


# ==========================================================
# PIPELINE ETL COMPLETO
# ==========================================================

def ejecutar_pipeline_completo():
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

    log_txt = ruta("logs", "logs.txt")

    with open(log_txt, 'a', encoding='utf-8') as f:
        f.write(
            f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};"
            f"Abriendo Orquestador ETL;{nombre_equipo};{ruta_ejecucion};"
            f"RAM:{ram_uso}%;Temp:{temp_uso}\n"
        )

    logging.info("=======================================================")
    logging.info("     INICIANDO PIPELINE ETL: CONTROL Y FISCALÍA        ")
    logging.info("=======================================================")

    resultados = {
        "FISCALÍA Y SECOP": ejecutar_modulo("FISCALÍA Y SECOP", modulo_fiscalia),
        "CONTRALORÍA": ejecutar_modulo("CONTRALORÍA", modulo_contraloria),
        "PROCURADURÍA": ejecutar_modulo("PROCURADURÍA", modulo_procuraduria),
    }

    # ======================================================
    # DATA WAREHOUSE
    # ======================================================

    logging.info("=======================================================")
    logging.info("       INICIANDO CARGA AL DATA WAREHOUSE SQLITE        ")
    logging.info("=======================================================")

    cargado = False
    try:
        cargar_gold_al_warehouse()
        cargado = True
        logging.info("Los archivos Gold fueron cargados al Data Warehouse.")
    except Exception:
        logging.exception("Error durante la carga al Data Warehouse")

    # ======================================================
    # RESUMEN
    # ======================================================

    logging.info("=======================================================")
    for modulo, ok in resultados.items():
        logging.info("  %-18s %s", modulo, "OK" if ok else "FALLÓ")
    logging.info("  %-18s %s", "DATA WAREHOUSE", "OK" if cargado else "FALLÓ")
    logging.info("=======================================================")

    with open(log_txt, 'a', encoding='utf-8') as f:
        f.write(
            f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};"
            f"Cerrando Orquestador ETL;{nombre_equipo};{ruta_ejecucion};"
            f"RAM:{psutil.virtual_memory().percent}%;Temp:{temp_uso}\n"
        )


if __name__ == "__main__":
    ejecutar_pipeline_completo()
