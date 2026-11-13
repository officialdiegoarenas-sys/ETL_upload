from pathlib import Path
import sqlite3


# Raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ubicación de la base de datos
DB_PATH = PROJECT_ROOT / "data_warehouse" / "warehouse.db"


def get_connection():
    """
    Crea y devuelve una conexión a SQLite.
    La base de datos se crea automáticamente si no existe.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    # Garantiza integridad referencial
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """
    Inicializa las tablas de control del Data Warehouse.
    Las tablas analíticas se crean dinámicamente al cargar los CSV Gold.
    """
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS _dw_load_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                target_table TEXT NOT NULL,
                rows_inserted INTEGER NOT NULL DEFAULT 0,
                rows_skipped INTEGER NOT NULL DEFAULT 0,
                loaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()