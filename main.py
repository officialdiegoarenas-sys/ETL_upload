import sys
import os
import logging

# Aseguramos que la ruta de (src) sea reconocida por Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from extract.extract_fiscalia_api import extraer_datos_api
from transform.clean_data import transformar_datos
from load.load_database import generar_capa_gold

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
        
    logging.info("=======================================================")
    logging.info("  ¡PIPELINE ETL EJECUTADO DE PUNTA A PUNTA CON ÉXITO!  ")
    logging.info("=======================================================")

if __name__ == "__main__":
    ejecutar_pipeline_completo()