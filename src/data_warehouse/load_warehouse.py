import csv
import hashlib
import json
import re
from pathlib import Path

from data_warehouse.database import (
    PROJECT_ROOT,
    get_connection,
    initialize_database,
)


GOLD_DIR = PROJECT_ROOT / "data" / "gold"


# Nombres controlados de las tablas del Data Warehouse.
# Si el archivo no está en este diccionario, se genera el nombre
# automáticamente a partir de su nombre de archivo.
TABLE_NAMES = {
    "fiscalia_perfil_condenados": "fiscalia_perfil_condenados",
    "fiscalia_procesados_sentencias": "fiscalia_procesados_sentencias",
    "fiscalia_procesos_anio_capitulo": "fiscalia_procesos_anio_capitulo",
    "fiscalia_procesos_departamento": "fiscalia_procesos_departamento",
    "fiscalia_procesos_etapa": "fiscalia_procesos_etapa",
    "fiscalia_top_delitos": "fiscalia_top_delitos",
    "resumen_contratos": "resumen_contratos",
    "resumen_procuraduria": "resumen_procuraduria",
}


def normalizar_nombre(nombre):
    """
    Convierte nombres de columnas o tablas en identificadores
    compatibles con SQLite.
    """
    nombre = str(nombre).strip().lower()
    nombre = re.sub(r"[^a-zA-Z0-9_]", "_", nombre)
    nombre = re.sub(r"_+", "_", nombre)
    nombre = nombre.strip("_")

    if not nombre:
        nombre = "columna"

    if nombre[0].isdigit():
        nombre = f"col_{nombre}"

    return nombre


def obtener_nombre_tabla(archivo):
    """
    Obtiene el nombre de la tabla según el nombre del CSV.
    """
    nombre = archivo.stem.lower()

    if nombre.endswith("_gold"):
        nombre = nombre[:-5]

    nombre = normalizar_nombre(nombre)

    return TABLE_NAMES.get(nombre, nombre)


def normalizar_columnas(columnas):
    """
    Normaliza los nombres de las columnas y evita nombres repetidos.
    """
    resultado = []
    utilizadas = set()

    for columna in columnas:
        nombre = normalizar_nombre(columna)
        original = nombre
        contador = 2

        while nombre in utilizadas:
            nombre = f"{original}_{contador}"
            contador += 1

        utilizadas.add(nombre)
        resultado.append(nombre)

    return resultado


def calcular_hash(registro):
    """
    Calcula una huella única del contenido de una fila.
    Permite evitar que se inserten registros idénticos.
    """
    contenido = json.dumps(
        registro,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def crear_tabla(connection, tabla, columnas):
    """
    Crea la tabla si no existe y agrega columnas nuevas
    cuando el CSV presenta cambios de estructura.
    """
    columnas_sql = ", ".join(
        f'"{columna}" TEXT'
        for columna in columnas
    )

    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS "{tabla}" (
            _dw_row_hash TEXT PRIMARY KEY,
            _dw_loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            {columnas_sql}
        )
    """)

    # Detectar columnas existentes
    existentes = {
        fila["name"]
        for fila in connection.execute(
            f'PRAGMA table_info("{tabla}")'
        ).fetchall()
    }

    # Incorporar columnas nuevas sin borrar las anteriores
    for columna in columnas:
        if columna not in existentes:
            connection.execute(
                f'ALTER TABLE "{tabla}" ADD COLUMN "{columna}" TEXT'
            )


def cargar_csv(connection, archivo):
    """
    Carga un CSV Gold en su tabla correspondiente.
    Devuelve el número de filas insertadas y omitidas.
    """
    tabla = obtener_nombre_tabla(archivo)

    with open(
        archivo,
        mode="r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as csv_file:

        muestra = csv_file.read(4096)
        csv_file.seek(0)

        try:
            dialecto = csv.Sniffer().sniff(
                muestra,
                delimiters=",;|\t",
            )
        except csv.Error:
            dialecto = csv.excel

        lector = csv.DictReader(csv_file, dialect=dialecto)

        if not lector.fieldnames:
            print(f"[AVISO] El archivo {archivo.name} no tiene encabezados.")
            return tabla, 0, 0

        columnas_originales = lector.fieldnames
        columnas = normalizar_columnas(columnas_originales)

        crear_tabla(connection, tabla, columnas)

        insertados = 0
        omitidos = 0

        placeholders = ", ".join("?" for _ in range(len(columnas) + 1))

        columnas_insert = ", ".join(
            [f'"{columna}"' for columna in columnas]
            + ["_dw_row_hash"]
        )

        sql = f"""
            INSERT OR IGNORE INTO "{tabla}"
            ({columnas_insert})
            VALUES ({placeholders})
        """

        for fila in lector:
            valores = [
                fila.get(columna_original)
                for columna_original in columnas_originales
            ]

            registro = dict(zip(columnas, valores))
            row_hash = calcular_hash(registro)

            cursor = connection.execute(
                sql,
                valores + [row_hash],
            )

            if cursor.rowcount == 1:
                insertados += 1
            else:
                omitidos += 1

    return tabla, insertados, omitidos


def cargar_gold_al_warehouse():
    """
    Busca todos los CSV de data/gold y los carga al Data Warehouse.
    Cada ejecución agrega registros nuevos y omite filas idénticas.
    """
    print("\n" + "=" * 60)
    print("INICIANDO CARGA AL DATA WAREHOUSE")
    print("=" * 60)

    if not GOLD_DIR.exists():
        print(f"[ERROR] No existe el directorio Gold: {GOLD_DIR}")
        return

    archivos = sorted(GOLD_DIR.glob("*.csv"))

    if not archivos:
        print("[AVISO] No se encontraron archivos CSV en Gold.")
        return

    initialize_database()

    total_insertados = 0
    total_omitidos = 0

    # Una transacción para toda la ejecución:
    # si falla una carga, se revierte el conjunto completo.
    try:
        with get_connection() as connection:
            for archivo in archivos:
                tabla, insertados, omitidos = cargar_csv(
                    connection,
                    archivo,
                )

                connection.execute("""
                    INSERT INTO _dw_load_history (
                        source_file,
                        target_table,
                        rows_inserted,
                        rows_skipped
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    archivo.name,
                    tabla,
                    insertados,
                    omitidos,
                ))

                total_insertados += insertados
                total_omitidos += omitidos

                print(
                    f"[OK] {archivo.name} -> {tabla} | "
                    f"Insertados: {insertados} | "
                    f"Omitidos: {omitidos}"
                )

            connection.commit()

    except Exception as error:
        print(f"\n[ERROR] Falló la carga al Data Warehouse: {error}")
        raise

    print("\n" + "-" * 60)
    print(f"Total de registros nuevos: {total_insertados}")
    print(f"Total de registros omitidos: {total_omitidos}")
    print(f"Base de datos: {PROJECT_ROOT / 'data_warehouse' / 'warehouse.db'}")
    print("CARGA FINALIZADA")
    print("=" * 60)