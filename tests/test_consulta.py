"""Consulta unificada por cédula / número de proceso: capa Gold de consulta, API y cliente de la app."""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "App"))
sys.path.insert(0, str(RAIZ))

from data_warehouse import consulta  # noqa: E402

PROCURADURIA = (
    "numero_siri,tipo_inhabilidad,calidad_persona,tipo_identificacion,nombre_tipo_identificacion,numero_identificacion,"
    "primer_apellido,segundo_apellido,primer_nombre,segundo_nombre,cargo,lugar_hechos_departamento,lugar_hechos_municipio,"
    "sanciones,duracion_anos,duracion_mes,duracion_dias,providencia,autoridad,fecha_efectos_juridicos,numero_proceso,"
    "entidad_sancionado,entidad_departamento,entidad_municipio\n"
    "100,Inhabilidad,SERVIDOR PÚBLICO,1,Cédula de Ciudadanía,1130456789,PEREZ,GOMEZ,MARIA,,ALCALDESA,VALLE,CALI,"
    "DESTITUCION,5,0,0,Fallo,Procuraduría,31/12/2025,  2023-0272   ,ALCALDIA DE CALI,VALLE,CALI\n"
    "101,Inhabilidad,SERVIDOR PÚBLICO,1,Cédula de Ciudadanía,1130456789,PEREZ,GOMEZ,MARIA,,CONCEJALA,VALLE,CALI,"
    "SUSPENSION,0,3,1,Fallo,Procuraduría,01/01/2024,2021-9999,CONCEJO DE CALI,VALLE,CALI\n"
)
SECOP = (
    "id_del_proceso,referencia_del_proceso,entidad,nit_entidad,nombre_del_proveedor,nit_del_proveedor_adjudicado,"
    "modalidad_de_contratacion,estado_del_procedimiento,adjudicado,precio_base,valor_total_adjudicacion,"
    "fecha_de_publicacion_del,urlproceso\n"
    "CO1.REQ.1,CD-55-2021,SECRETARIA X,890,PROVEEDOR UNO SAS,900123456,Contratación directa,Seleccionado,Si,1000,900,2024-01-01,http://x\n"
    "CO1.REQ.2,CD-56-2021,SECRETARIA Y,891,No Definido,No Definido,Mínima cuantía,Publicado,No,500,,2024-02-01,http://y\n"
)


CONTRALORIA = (
    "sujeto_auditado,modalidad_de_auditoria,hallazgos_administrativos,hallazgos_disciplinarios,hallazgos_penales,"
    "hallazgos_fiscales,cuantia,vigencia\n"
    "Contraloría General de Medellín,Regular,22,4,0,2,16355215.0,2019\n"
    "Contraloría General de Medellín,Regular,10,1,1,0,500.0,2021\n"
    "Contraloría Distrital de Santa Marta,AFG,5,0,0,0,0.0,2020\n"
)


@pytest.fixture()
def db(tmp_path):
    silver = tmp_path / "silver"; silver.mkdir()
    (silver / "procuraduria_clean.csv").write_text(PROCURADURIA, encoding="utf-8")
    (silver / "datos_secop_silver.csv").write_text(SECOP, encoding="utf-8")
    (silver / "contraloria_clean.csv").write_text(CONTRALORIA, encoding="utf-8")
    ruta = tmp_path / "w.db"
    assert consulta.construir_tablas(ruta, silver) == {
        "gold_consulta_sanciones": 2, "gold_consulta_contratos": 2, "gold_consulta_contraloria": 2}
    return ruta


def test_busca_por_cedula_con_puntos(db):
    r = consulta.buscar("1.130.456.789", db)
    assert len(r["sanciones"]) == 2 and r["contratos"] == []
    assert r["sanciones"][0]["nombre"] == "Maria Perez Gomez"
    assert r["sanciones"][0]["coincide_por"] == "número de identificación"


def test_busca_por_numero_de_proceso_ignorando_espacios_y_mayusculas(db):
    r = consulta.buscar("2023-0272", db)
    assert [s["entidad"] for s in r["sanciones"]] == ["ALCALDIA DE CALI"]
    assert r["sanciones"][0]["duracion"] == "5 años"
    assert consulta.buscar(" 2023-0272 ", db)["total"] == 1


def test_duracion_compuesta(db):
    r = consulta.buscar("2021-9999", db)
    assert r["sanciones"][0]["duracion"] == "3 meses, 1 día"


@pytest.mark.parametrize("q,esperado", [
    ("1130456789", "1130456789"), ("1.130.456.789", "1130456789"), ("900.123.456-7", "900123456"),
    ("900123456-7", "900123456"), ("2023-0272", ""), ("EE-DEATA-2022-151", ""), ("1234", ""), ("CD-55-2021", ""),
])
def test_deteccion_de_identificacion(q, esperado):
    assert consulta._identificacion(q) == esperado


def test_numero_de_proceso_no_se_confunde_con_cedula(tmp_path):
    silver = tmp_path / "s"; silver.mkdir()
    # ambas filas tienen la cédula 20230272, cuyos dígitos coinciden con el proceso 2023-0272 de una sola
    (silver / "procuraduria_clean.csv").write_text(PROCURADURIA.replace("1130456789", "20230272"), encoding="utf-8")
    (silver / "datos_secop_silver.csv").write_text(SECOP, encoding="utf-8")
    ruta = tmp_path / "w.db"; consulta.construir_tablas(ruta, silver)
    r = consulta.buscar("2023-0272", ruta)
    assert [s["numero_proceso"] for s in r["sanciones"]] == ["2023-0272"]       # solo la del número de proceso
    assert [s["coincide_por"] for s in r["sanciones"]] == ["número de proceso o SIRI"]


def test_busca_proveedor_en_secop_y_por_id_de_proceso(db):
    assert consulta.buscar("900123456", db)["contratos"][0]["proveedor"] == "PROVEEDOR UNO SAS"
    assert consulta.buscar("co1.req.1", db)["total"] == 1
    assert consulta.buscar("CD-55-2021", db)["total"] == 1


def test_nit_no_definido_no_se_puede_buscar(db):
    assert consulta.buscar("No Definido", db)["contratos"] == []


def test_busca_contraloria_por_nombre_sin_tildes_ni_mayusculas(db):
    for q in ("Contraloría General de Medellín", "contraloria general de medellin", "MEDELLIN"):
        r = consulta.buscar(q, db)
        assert [c["nombre"] for c in r["contraloria"]] == ["Contraloría General de Medellín"], q
    m = consulta.buscar("medellin", db)["contraloria"][0]
    assert (m["registros"], m["administrativos"], m["disciplinarios"], m["fiscales"], m["penales"]) == (2, 32, 5, 2, 1)
    assert (m["vigencia_desde"], m["vigencia_hasta"], m["cuantia"]) == ("2019", "2021", 16355715.0)
    assert m["coincide_por"] == "nombre de la entidad auditada"


def test_contraloria_palabras_en_cualquier_orden_y_sin_articulos(db):
    for q in ("Contraloría de Medellín", "medellin contraloria", "contraloria general medellin"):
        assert [c["nombre"] for c in consulta.buscar(q, db)["contraloria"]] == ["Contraloría General de Medellín"], q
    assert consulta.buscar("contraloria santa marta", db)["contraloria"][0]["nombre"] == "Contraloría Distrital de Santa Marta"
    assert consulta.buscar("contraloria cali", db)["contraloria"] == []        # una palabra que no está


def test_contraloria_varias_coincidencias_y_total(db):
    r = consulta.buscar("contraloria", db)
    assert len(r["contraloria"]) == 2 and r["total"] == 2
    assert r["contraloria"][0]["nombre"] == "Contraloría General de Medellín"    # ordenadas por hallazgos


def test_cedula_o_proceso_no_se_busca_como_nombre(db):
    assert consulta.buscar("1130456789", db)["contraloria"] == []
    assert consulta.buscar("2023-0272", db)["contraloria"] == []


def test_contraloria_es_opcional_si_la_tabla_no_existe(tmp_path):
    silver = tmp_path / "s"; silver.mkdir()
    (silver / "procuraduria_clean.csv").write_text(PROCURADURIA, encoding="utf-8")
    (silver / "datos_secop_silver.csv").write_text(SECOP, encoding="utf-8")
    ruta = tmp_path / "w.db"; consulta.construir_tablas(ruta, silver)
    assert consulta.buscar("contraloria de medellin", ruta)["contraloria"] == []


def test_sin_resultados(db):
    assert consulta.buscar("99999999", db)["total"] == 0


@pytest.mark.parametrize("q", ["", "abc", "   12 "])
def test_consulta_demasiado_corta(db, q):
    with pytest.raises(ValueError):
        consulta.buscar(q, db)


@pytest.mark.parametrize("q", ["' OR 1=1 --", "%", "_", "*", "1130456789' OR '1'='1"])
def test_no_hay_comodines_ni_inyeccion(db, q):
    if len(q) < 4:
        pytest.skip("demasiado corta: la rechaza la validación")
    assert consulta.buscar(q, db)["total"] == 0


def test_sin_capa_de_consulta(tmp_path):
    import sqlite3
    ruta = tmp_path / "vacia.db"; sqlite3.connect(ruta).close()
    with pytest.raises(consulta.ConsultaNoDisponible):
        consulta.buscar("1130456789", ruta)
    with pytest.raises(consulta.ConsultaNoDisponible):
        consulta.buscar("1130456789", tmp_path / "no_existe.db")


def test_reconstruir_no_duplica(db, tmp_path):
    silver = tmp_path / "silver"
    assert consulta.construir_tablas(db, silver)["gold_consulta_sanciones"] == 2
    assert len(consulta.buscar("1130456789", db)["sanciones"]) == 2


# ---------------- API ----------------
def test_api_consulta(db, tmp_path, monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from api import main as api_main

    monkeypatch.setattr(api_main, "RUTA_DB", str(db))
    cli = TestClient(api_main.app)
    r = cli.get("/consulta", params={"q": "1130456789"})
    assert r.status_code == 200 and r.json()["total"] == 2
    assert cli.get("/consulta", params={"q": "ab"}).status_code == 422
    assert cli.get("/consulta").status_code == 422
    monkeypatch.setattr(api_main, "RUTA_DB", str(tmp_path / "no_existe.db"))
    assert cli.get("/consulta", params={"q": "1130456789"}).status_code == 503


def test_cliente_de_la_app_api_apagada(monkeypatch):
    import datos
    monkeypatch.setenv("APP_API_URL", "http://127.0.0.1:9")
    with pytest.raises(datos.ApiNoDisponible):
        datos.consultar("1130456789", timeout=1)
