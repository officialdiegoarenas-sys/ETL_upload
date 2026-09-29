import sys
import os
import logging

# Aseguramos que la ruta de (src) sea reconocida por Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from extract.extract_fiscalia_api import extraer_datos_api
from transform.clean_data import transformar_datos
from load.load_database import generar_capa_gold

# Importamos las funciones del nuevo módulo de Procuraduría
from extract.extract_procuraduria import extraer_datos_procuraduria
from transform.transform_procuraduria import transformar_datos_procuraduria
from load.load_procuraduria import procesar_capa_gold as generar_gold_procuraduria

# Configuración de la carpeta de Logs 
# esta automatizacion la logramos hacer con IA, para que cada vez que se ejecute el main, este log se actualice. 

os.makedirs("logs", exist_ok=True)
log_path = os.path.join("logs", "pipeline.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"), # Guarda los registros en logs/pipeline.log
        logging.StreamHandler(sys.stdout)             # Muestra los mensajes en la terminal en tiempo real
    ]
)

def ejecutar_pipeline_completo():
    logging.info("=======================================================")
    logging.info("     INICIANDO PIPELINE ETL: CONTROL Y FISCALÍA        ")
    logging.info("=======================================================")
    
    # Definimos las rutas estándar
    url_api = "https://www.datos.gov.co/resource/p6dx-8zbt.json?$limit=100"
    bronze_path = "data/bronze/contratos_fiscalia_raw.csv"
    silver_path = "data/silver/contratos_fiscalia_clean.csv"
    gold_path = "data/gold/resumen_contratos_gold.csv"
    
    # Capa Bronze (Extracción)
    logging.info("[1/3] Ejecutando Capa Bronze (Extracción)...")
    df_bronze = extraer_datos_api(url_api, bronze_path)
    if df_bronze is None:
        logging.error("❌ Error crítico en la Capa Bronze.")
        return
        
    # Capa Silver (Transformación y Limpieza)
    logging.info("[2/3] Ejecutando Capa Silver (Transformación)...")
    df_silver = transformar_datos(bronze_path, silver_path)
    if df_silver is None:
        logging.error("❌ Error crítico en la Capa Silver.")
        return
        
    # Capa Gold (Agregación y Analítica)
    logging.info("[3/3] Ejecutando Capa Gold (Analítica / KPIs)...")
    df_gold = generar_capa_gold(silver_path, gold_path)
    if df_gold is None:
        logging.error("❌ Error crítico en la Capa Gold.")
        return
        
    # --- PROCESO AÑADIDO: MÓDULO PROCURADURÍA ---
    logging.info("--- INICIANDO MÓDULO PROCURADURÍA ---")
    url_csv_proc = "https://www.datos.gov.co/resource/iaeu-rcn6.csv?$limit=1000&$order=fecha_efectos_juridicos%20DESC"
    bronze_proc = "data/bronze/procuraduria_raw.csv"
    silver_proc = "data/silver/procuraduria_clean.csv"
    gold_proc = "data/gold/resumen_procuraduria_gold.csv"

    logging.info("Ejecutando Capa Bronze (Procuraduría)...")
    if extraer_datos_procuraduria(url_csv_proc, bronze_proc) is None:
        logging.error("❌ Error crítico en la Capa Bronze de Procuraduría.")
        return

    logging.info("Ejecutando Capa Silver (Procuraduría)...")
    if transformar_datos_procuraduria(bronze_proc, silver_proc) is None:
        logging.error("❌ Error crítico en la Capa Silver de Procuraduría.")
        return

    logging.info("Ejecutando Capa Gold (Procuraduría)...")
    if generar_gold_procuraduria(silver_proc, gold_proc) is None:
        logging.error("❌ Error crítico en la Capa Gold de Procuraduría.")
        return

    logging.info("=======================================================")
    logging.info("  ¡PIPELINE ETL EJECUTADO DE PUNTA A PUNTA CON ÉXITO!  ")
    logging.info("=======================================================")

if __name__ == "__main__":
    ejecutar_pipeline_completo()
    
