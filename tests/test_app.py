"""Pruebas del dashboard (carpeta App): login, datos Gold, favoritos, calendario y API.

Cada prueba documenta resultado esperado; los casos incluyen datos correctos,
incorrectos y límite (rúbrica: pruebas técnicas).
"""
import sys
from datetime import date
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "App"))

import acceso  # noqa: E402
import almacen  # noqa: E402
import calendario  # noqa: E402
import datos  # noqa: E402


# ---------------- Login ----------------
@pytest.mark.parametrize("correo,clave,esperado", [
    ("diegofiscalia@gmail.com", "cualquiera", True),          # ejemplo del enunciado
    ("  MARIA@FISCALIA.GOV.CO ", "x", True),                   # mayúsculas y espacios
    ("juan@fiscalía.gov.co", "x", True),                       # con tilde
    ("diego@gmail.com", "x", False),                           # sin la palabra clave
    ("fiscalia", "x", False),                                  # no es un correo
    ("", "x", False),                                          # vacío
    ("a@fiscalia.co", "", False),                              # sin contraseña
])
def test_validar_acceso(correo, clave, esperado):
    ok, mensaje = acceso.validar_acceso(correo, clave)
    assert ok is esperado
    assert mensaje


def test_nombre_para_mostrar():
    assert acceso.nombre_para_mostrar("maria.perez@fiscalia.gov.co") == "Maria Perez"
    assert acceso.nombre_para_mostrar("diegofiscalia@gmail.com") == "Diego"
    assert acceso.nombre_para_mostrar("fiscalia@fiscalia.gov.co") == "Fiscalia"   # caso límite: solo la palabra clave


# ---------------- Limpieza de texto ----------------
def test_acentuar_y_departamentos():
    assert datos.acentuar("Indagacion") == "Indagación"
    assert datos.acentuar("Servidor Publico") == "Servidor Público"
    assert datos.limpiar_departamento("BOGOTA, D. C.") == "Bogotá D.C."
    assert datos.limpiar_departamento("NARINO") == "Nariño"


def test_unificar_entidades_inpec():
    a = datos.unificar_entidad("INPEC")
    b = datos.unificar_entidad("INSTITUTO NACIONAL PENITENCIARIO Y CARCELARIO -INPEC-")
    assert a == b


def test_fuerza_publica():
    assert datos.es_fuerza_publica("POLICIA NACIONAL")
    assert datos.es_fuerza_publica("EJERCITO NACIONAL")
    assert not datos.es_fuerza_publica("BANCO AGRARIO DE COLOMBIA")


# ---------------- Capa Gold (integración con el ETL) ----------------
@pytest.mark.parametrize("nombre", list(datos.DATASETS_POR_DEFECTO))
def test_gold_se_carga_y_no_esta_vacio(nombre):
    if not datos.disponible(nombre):
        pytest.skip("Gold no generado: ejecute python main.py")
    df = datos.cargar(nombre)
    assert len(df) > 0
    assert not any("�" in str(v) for v in df.astype(str).to_numpy().ravel()), "texto con caracteres dañados"


def test_dataset_inexistente_da_error_controlado():
    with pytest.raises(datos.DatoNoDisponible):
        datos.leer_csv("no_existe")


def test_procuraduria_agrupa_alias(monkeypatch):
    if not datos.disponible("procuraduria"):
        pytest.skip("Gold no generado")
    df = datos.cargar("procuraduria")
    assert df["entidad_sancionado"].is_unique
    assert df["fuerza_publica"].dtype == bool


# ---------------- Favoritos y recordatorios ----------------
@pytest.fixture()
def almacen_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DATOS_USUARIO", str(tmp_path / "u.json"))
    return tmp_path


def test_favoritos_alternar(almacen_temporal):
    c = "luz@fiscalia.gov.co"
    assert almacen.favoritos(c) == []
    assert almacen.alternar_favorito(c, "fis_etapa") is True
    assert almacen.es_favorito(c, "fis_etapa")
    assert almacen.alternar_favorito(c, "fis_etapa") is False
    assert almacen.favoritos(c) == []


def test_favoritos_son_por_usuario(almacen_temporal):
    almacen.alternar_favorito("a@fiscalia.co", "r1")
    assert almacen.favoritos("B@fiscalia.co") == []
    assert almacen.favoritos("A@FISCALIA.CO") == ["r1"]   # el correo no distingue mayúsculas


def test_archivo_corrupto_no_rompe(almacen_temporal):
    (almacen_temporal / "u.json").write_text("{esto no es json", encoding="utf-8")
    assert almacen.favoritos("a@fiscalia.co") == []


def test_eventos_crear_listar_borrar(almacen_temporal):
    c = "luz@fiscalia.gov.co"
    e = almacen.agregar_evento(c, date(2026, 12, 1), "  Audiencia 123  ", "Audiencia", "sala 4")
    assert e["titulo"] == "Audiencia 123"
    assert [x["id"] for x in almacen.eventos(c)] == [e["id"]]
    assert almacen.eliminar_evento(c, e["id"]) is True
    assert almacen.eliminar_evento(c, e["id"]) is False
    assert almacen.eventos(c) == []


@pytest.mark.parametrize("titulo,tipo", [("", "Audiencia"), ("   ", "Audiencia"), ("x" * 121, "Audiencia"), ("ok", "Inventado")])
def test_evento_invalido(almacen_temporal, titulo, tipo):
    with pytest.raises(ValueError):
        almacen.agregar_evento("a@fiscalia.co", date(2026, 1, 1), titulo, tipo)


# ---------------- Calendario ----------------
def test_festivos_2026():
    esperados = {
        date(2026, 1, 1), date(2026, 1, 12), date(2026, 3, 23), date(2026, 4, 2), date(2026, 4, 3),
        date(2026, 5, 1), date(2026, 5, 18), date(2026, 6, 8), date(2026, 6, 15), date(2026, 6, 29),
        date(2026, 7, 20), date(2026, 8, 7), date(2026, 8, 17), date(2026, 10, 12), date(2026, 11, 2),
        date(2026, 11, 16), date(2026, 12, 8), date(2026, 12, 25),
    }
    assert set(calendario.festivos_colombia(2026)) == esperados


def test_festivos_2024_pascua_bisiesto():
    f = calendario.festivos_colombia(2024)
    assert date(2024, 3, 28) in f and date(2024, 3, 29) in f      # Semana Santa 2024
    assert date(2024, 5, 13) in f                                  # Ascensión


def test_sumar_dias_habiles():
    # Viernes 13/11/2026 + 1 día hábil = martes 17/11 (lunes 16 es festivo)
    assert calendario.sumar_dias_habiles(date(2026, 11, 13), 1) == date(2026, 11, 17)
    assert calendario.sumar_dias_habiles(date(2026, 11, 13), 0) == date(2026, 11, 13)   # caso límite
    with pytest.raises(ValueError):
        calendario.sumar_dias_habiles(date(2026, 11, 13), -1)


def test_es_dia_habil():
    assert calendario.es_dia_habil(date(2026, 11, 13))
    assert not calendario.es_dia_habil(date(2026, 11, 14))     # sábado
    assert not calendario.es_dia_habil(date(2026, 12, 25))     # Navidad


# ---------------- API (integración Gold -> FastAPI) ----------------
def test_api_gold():
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    sys.path.insert(0, str(RAIZ))
    from api.main import app

    cli = TestClient(app)
    listado = cli.get("/gold")
    assert listado.status_code == 200
    nombres = [x["nombre"] for x in listado.json()]
    if not nombres:
        pytest.skip("Gold no generado")
    assert "fiscalia_procesos_ano_capitulo" in nombres
    r = cli.get(f"/gold/{nombres[0]}")
    assert r.status_code == 200 and r.json()["total_registros"] > 0
    assert cli.get("/gold/no_existe").status_code == 404
    # el nombre de dataset de la app coincide con el de la API
    for archivo in datos.datasets().values():
        assert datos.nombre_api(archivo) in nombres


# ---------------- Pantallas (renderizado) ----------------
def _pantalla(nombre, **estado):
    import streamlit as st
    import paginas
    st.session_state["usuario"] = "luz@fiscalia.gov.co"
    for k, v in estado.items():
        st.session_state[k] = v
    getattr(paginas, nombre)()


@pytest.mark.parametrize("pagina", ["pagina_inicio", "pagina_fiscalia", "pagina_secop", "pagina_sanciones",
                                     "pagina_contraloria", "pagina_calendario", "pagina_favoritos", "pagina_ayuda"])
def test_las_pantallas_se_dibujan_sin_errores(pagina, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("APP_DATOS_USUARIO", str(tmp_path / "u.json"))
    if not all(datos.disponible(n) for n in datos.datasets()):
        pytest.skip("Gold no generado: ejecute python main.py")
    at = AppTest.from_function(_pantalla, args=(pagina,), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]


def test_pantalla_de_consulta_muestra_procuraduria_secop_y_contraloria(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("APP_DATOS_USUARIO", str(tmp_path / "u.json"))
    falso = {
        "consulta": "demo", "identificacion": "", "total": 3,
        "sanciones": [{"id_norm": "123", "tipo_identificacion": "CC", "nombre": "Ana Perez", "calidad_persona": "SERVIDOR PUBLICO",
                       "cargo": "ALCALDESA", "entidad": "ALCALDIA X", "departamento": "", "municipio": "", "tipo_inhabilidad": "",
                       "sanciones": "DESTITUCION", "duracion": "5 años", "providencia": "PRIMERA", "autoridad": "", "fecha_efectos": "01/01/2025",
                       "numero_proceso": "2023-0272", "proceso_norm": "2023-0272", "numero_siri": "1", "coincide_por": "número de proceso o SIRI"}],
        "contratos": [{"id_proceso": "CO1.REQ.1", "referencia": "CD-1", "entidad": "SECRETARIA X", "proveedor": "UNO SAS", "nit_proveedor": "900",
                       "modalidad": "Directa", "estado": "Seleccionado", "adjudicado": "Si", "fecha_publicacion": "2024-01-01",
                       "coincide_por": "id o referencia del proceso"}],
        "contraloria": [{"nombre": "Contraloría General de Medellín", "registros": 2, "administrativos": 32, "disciplinarios": 5, "fiscales": 2,
                         "penales": 1, "cuantia": 16355715.0, "vigencia_desde": "2019", "vigencia_hasta": "2021",
                         "coincide_por": "nombre de la entidad auditada"}],
    }
    monkeypatch.setattr(datos, "consultar", lambda q, timeout=8.0: falso)
    at = AppTest.from_function(_pantalla, args=("pagina_consulta",), kwargs={"consulta_q": "demo"}, default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    html = " ".join(m.value for m in at.markdown)
    assert "Ana Perez" in html and "UNO SAS" in html and "Contraloría General de Medellín" in html
    assert "$16 millones" in html                      # cuantía con formato en pesos
    assert any("3 registro(s)" in s.value for s in at.success)
