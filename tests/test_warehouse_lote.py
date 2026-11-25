"""Carga por lotes al Data Warehouse: idempotencia, lotes pequeños y coincidencia con el warehouse real."""
import sqlite3
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from data_warehouse import load_warehouse as lw  # noqa: E402


def _conexion():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row          # igual que data_warehouse.database.get_connection
    return con


def _csv(tmp_path, filas, nombre="prueba_gold.csv"):
    ruta = tmp_path / nombre
    ruta.write_text("entidad,total\n" + "\n".join(f"{e},{t}" for e, t in filas) + "\n", encoding="utf-8")
    return ruta


def test_carga_por_lotes_cuenta_insertados_y_omitidos(tmp_path, monkeypatch):
    monkeypatch.setattr(lw, "TAMANO_LOTE", 3)                     # fuerza varios lotes
    ruta = _csv(tmp_path, [(f"E{i}", i) for i in range(10)] + [("E0", 0), ("E1", 1)])   # 2 repetidas
    con = _conexion()
    tabla, ins, omi = lw.cargar_csv(con, ruta)
    assert (ins, omi) == (10, 2)
    assert con.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0] == 10


def test_carga_es_idempotente(tmp_path):
    ruta = _csv(tmp_path, [("A", 1), ("B", 2)])
    con = _conexion()
    assert lw.cargar_csv(con, ruta)[1:] == (2, 0)
    assert lw.cargar_csv(con, ruta)[1:] == (0, 2)                 # segunda corrida: nada nuevo


def test_csv_solo_encabezado(tmp_path):
    ruta = tmp_path / "vacio_gold.csv"
    ruta.write_text("entidad,total\n", encoding="utf-8")
    con = _conexion()
    assert lw.cargar_csv(con, ruta)[1:] == (0, 0)                 # caso límite


def test_gold_real_esta_contenido_en_warehouse():
    """El warehouse acumula histórico: cada fila del Gold actual debe existir (mismo hash) en él."""
    db = RAIZ / "data_warehouse" / "warehouse.db"
    gold = sorted((RAIZ / "data" / "gold").glob("*.csv"))
    if not db.exists() or not gold:
        pytest.skip("Warehouse o Gold no generados")
    nuevo = _conexion()
    esperado = sqlite3.connect(db)
    for archivo in gold:
        tabla, _, _ = lw.cargar_csv(nuevo, archivo)
        hashes_nuevos = {f[0] for f in nuevo.execute(f'SELECT _dw_row_hash FROM "{tabla}"')}
        hashes_dw = {f[0] for f in esperado.execute(f'SELECT _dw_row_hash FROM "{tabla}"')}
        assert hashes_nuevos <= hashes_dw, f"{tabla}: {len(hashes_nuevos - hashes_dw)} filas del Gold no están en el warehouse"
