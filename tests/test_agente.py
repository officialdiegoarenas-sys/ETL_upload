"""Pruebas unitarias para el Agente Analítico de Integración de Entidades."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RUTA_TEST = Path(__file__).resolve().parent
RUTA_PROYECTO = RUTA_TEST.parent
RUTA_SRC = RUTA_PROYECTO / "src"
RUTA_APP = RUTA_PROYECTO / "App"

sys.path.insert(0, str(RUTA_SRC))
sys.path.insert(0, str(RUTA_APP))
sys.path.insert(0, str(RUTA_PROYECTO))

from agente.agente_entidades import AgenteEntidadesControl  # noqa: E402
from api.main import app  # noqa: E402


@pytest.fixture
def agente():
    return AgenteEntidadesControl()


@pytest.fixture
def cliente_api():
    return TestClient(app)


def test_deteccion_filtros(agente):
    f_gen = agente.detectar_filtros("Muéstrame el panorama general de las 3 entidades")
    assert f_gen["es_resumen_general"] is True

    f_pol = agente.detectar_filtros("¿Qué sanciones tiene la Policía Nacional?")
    assert f_pol["entidad_buscada"] == "POLICIA NACIONAL"

    f_ant = agente.detectar_filtros("Procesos en Antioquia")
    assert f_ant["departamento"] == "ANTIOQUIA"

    f_bog = agente.detectar_filtros("Delitos en Bogotá D.C.")
    assert f_bog["departamento"] == "BOGOTA"


def test_agente_cruce_general(agente):
    res = agente.consultar("Panorama general de las entidades")
    assert "pregunta" in res
    assert "alerta" in res
    assert res["alerta"]["score"] > 0
    assert "kpis" in res
    assert len(res["kpis"]) == 4
    assert "narrativa" in res
    assert "Fiscalía" in res["narrativa"]
    assert "Procuraduría" in res["narrativa"]
    assert "Contraloría" in res["narrativa"]
    assert "graficas" in res
    assert "comparativa_entidades" in res["graficas"]


def test_agente_entidad_policia(agente):
    res = agente.consultar("Policía Nacional")
    assert res["filtros"]["entidad_buscada"] == "POLICIA NACIONAL"
    assert res["procuraduria"]["total_sanciones_filtro"] > 0
    assert len(res["procuraduria"]["coincidencias"]) > 0
    assert "POLICIA" in res["narrativa"]


def test_agente_departamento_antioquia(agente):
    res = agente.consultar("Situación en Antioquia")
    assert res["filtros"]["departamento"] == "ANTIOQUIA"
    di = res["fiscalia"].get("departamento_info")
    assert di is not None
    assert di["departamento"] == "ANTIOQUIA"
    assert di["total_procesos"] > 0


def test_agente_graficas_validas(agente):
    res = agente.consultar("General")
    graficas = res["graficas"]
    assert len(graficas) >= 2
    for clave, g in graficas.items():
        assert "titulo" in g
        assert "fig" in g
        # Verificar que sea un objeto go.Figure o tenga layout
        assert hasattr(g["fig"], "layout")


def test_api_agente_endpoints(cliente_api):
    # Endpoint de sugerencias
    resp_sug = cliente_api.get("/agente/sugerencias")
    assert resp_sug.status_code == 200
    sug_data = resp_sug.json()
    assert isinstance(sug_data, list)
    assert len(sug_data) >= 4

    # Endpoint de consulta
    resp_cons = cliente_api.get("/agente/consulta?q=Policia")
    assert resp_cons.status_code == 200
    data = resp_cons.json()
    assert "alerta" in data
    assert "kpis" in data
    assert "narrativa" in data
    assert "graficas" in data


def test_ollama_verificacion(agente):
    ok, modelos = agente.verificar_ollama()
    assert isinstance(ok, bool)
    assert isinstance(modelos, list)


def test_agente_modo_ia_y_fallback(agente):
    # Prueba con IA desactivada (debe retornar modo_ia=False de forma determinística)
    res_no_ia = agente.consultar("Panorama general", usar_ia=False)
    assert res_no_ia["modo_ia"] is False
    assert len(res_no_ia["narrativa"]) > 100

    # Prueba con IA activada (si Ollama está online, funcionará o caerá limpiamente en fallback)
    res_ia = agente.consultar("Panorama general", usar_ia=True)
    assert isinstance(res_ia["modo_ia"], bool)
    assert len(res_ia["narrativa"]) > 100


def test_api_agente_ollama_estado(cliente_api):
    resp = cliente_api.get("/agente/ollama/estado")
    assert resp.status_code == 200
    data = resp.json()
    assert "activo" in data
    assert "modelos" in data

