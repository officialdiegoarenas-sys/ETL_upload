"""DAG de Airflow para el ETL de Entidades de Control.

Ejecuta los módulos de main.py (Fiscalía/SECOP, Contraloría, Procuraduría) y luego carga el warehouse.
Nota: este archivo no se ha probado en Airflow todavía."""
import importlib.util
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

RAIZ = Path(os.environ.get("ETL_PROYECTO_DIR", Path(__file__).resolve().parent.parent))


def _cargar_orquestador():
    """Importa main.py de la raíz del proyecto sin ejecutar el pipeline."""
    sys.path.insert(0, str(RAIZ))
    sys.path.insert(0, str(RAIZ / "src"))
    spec = importlib.util.spec_from_file_location("etl_main", RAIZ / "main.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _ejecutar(nombre_modulo: str):
    main = _cargar_orquestador()
    funciones = {
        "FISCALÍA Y SECOP": main.modulo_fiscalia,
        "CONTRALORÍA": main.modulo_contraloria,
        "PROCURADURÍA": main.modulo_procuraduria,
    }
    # ejecutar_modulo devuelve False (sin lanzar) si el módulo falla: aquí se convierte en
    # error de la tarea para que Airflow lo marque, reintente y alerte.
    if not main.ejecutar_modulo(nombre_modulo, funciones[nombre_modulo]):
        raise RuntimeError(f"Falló el módulo {nombre_modulo}; revise logs/pipeline.log")


def _cargar_warehouse():
    _cargar_orquestador().cargar_gold_al_warehouse()


default_args = {
    "owner": "equipo_etl",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "etl_entidades_control",
    default_args=default_args,
    description="ETL Fiscalía, SECOP II, Procuraduría y Contraloría (Bronze, Silver, Gold) + Data Warehouse",
    schedule=timedelta(hours=24),
    start_date=datetime(2026, 11, 1),
    catchup=False,
    tags=["etl", "medallon"],
) as dag:
    t_fiscalia = PythonOperator(task_id="fiscalia_secop", python_callable=_ejecutar, op_args=["FISCALÍA Y SECOP"])
    t_contraloria = PythonOperator(task_id="contraloria", python_callable=_ejecutar, op_args=["CONTRALORÍA"])
    t_procuraduria = PythonOperator(task_id="procuraduria", python_callable=_ejecutar, op_args=["PROCURADURÍA"])
    t_warehouse = PythonOperator(task_id="data_warehouse", python_callable=_cargar_warehouse, trigger_rule="all_done")

    [t_fiscalia, t_contraloria, t_procuraduria] >> t_warehouse
