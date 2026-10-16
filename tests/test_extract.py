import os
import sys
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import extract.extract_fiscalia_api as secop
import extract.extract_fiscalia_delitos as fiscalia
from extract.extract_procuraduria import extraer_datos_procuraduria


class RespuestaFalsa:
    def __init__(self, status_code, datos=None, texto=""):
        self.status_code = status_code
        self.datos = datos
        self.text = texto

    def json(self):
        return self.datos


@pytest.fixture(autouse=True)
def carpeta_temporal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def test_secop_guarda_csv(monkeypatch):
    datos = [{"nombre_entidad": "A", "id_del_proceso": "1"}, {"nombre_entidad": "B", "id_del_proceso": "2"}]
    monkeypatch.setattr(secop.requests, "get", lambda url: RespuestaFalsa(200, datos))

    df = secop.extraer_datos_api("url", "data/bronze/secop.csv")

    assert len(df) == 2
    assert os.path.exists("data/bronze/secop.csv")


def test_secop_error_http(monkeypatch):
    monkeypatch.setattr(secop.requests, "get", lambda url: RespuestaFalsa(500))
    assert secop.extraer_datos_api("url", "data/bronze/secop.csv") is None


def test_procuraduria_lee_csv():
    pd.DataFrame({"numero_siri": [1, 2], "sanciones": ["A", "B"]}).to_csv("origen.csv", index=False)

    df = extraer_datos_procuraduria("origen.csv", "data/bronze/proc.csv")

    assert len(df) == 2
    assert os.path.exists("data/bronze/proc.csv")


def test_procuraduria_vacio():
    pd.DataFrame(columns=["numero_siri"]).to_csv("vacio.csv", index=False)
    assert extraer_datos_procuraduria("vacio.csv", "data/bronze/proc.csv") is None


def test_fiscalia_pagina_y_quita_columnas_internas(monkeypatch):
    encabezado = ":id,:created_at,:updated_at,:version,proceso_anonimizado,delito\n"
    paginas = [
        encabezado + "row-1,x,x,x,P1,Peculado\nrow-2,x,x,x,P2,Cohecho\n",
        encabezado + "row-3,x,x,x,P3,Concusion\n",
    ]
    llamadas = []

    def get_falso(url, params, timeout):
        llamadas.append(params["$where"])
        return RespuestaFalsa(200, texto=paginas[len(llamadas) - 1])

    monkeypatch.setattr(fiscalia.requests, "get", get_falso)

    total = fiscalia.extraer_datos_fiscalia("abcd-1234", "data/bronze/fiscalia.csv", tamano_pagina=2)
    df = pd.read_csv("data/bronze/fiscalia.csv")

    assert total == 3
    assert list(df.columns) == ["proceso_anonimizado", "delito"]
    assert ":id > 'row-2'" in llamadas[1]


def test_fiscalia_falla_despues_de_reintentos(monkeypatch):
    monkeypatch.setattr(fiscalia.requests, "get", lambda url, params, timeout: RespuestaFalsa(503))
    monkeypatch.setattr(fiscalia.time, "sleep", lambda s: None)

    assert fiscalia.extraer_datos_fiscalia("abcd-1234", "data/bronze/fiscalia.csv") is None
