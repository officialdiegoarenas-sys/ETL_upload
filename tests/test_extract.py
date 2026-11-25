import os
import sys
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import extract.extract_fiscalia_api as secop
import extract.extract_fiscalia_delitos as fiscalia
import extract.extract_policia as policia
import extract.extract_contraloria as contraloria
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


def test_contraloria_api_conserva_nulos(monkeypatch):
    datos = [
        {"hallazgos_administrativos": 12, "sujeto_auditado": "Entidad A"},
        {"hallazgos_administrativos": None, "sujeto_auditado": "Entidad B"},
    ]
    monkeypatch.setattr(
        contraloria,
        "_cargar_desde_api",
        lambda url: pd.DataFrame(datos),
    )

    df = contraloria.extraer_datos_contraloria(
        contraloria.URL_API_CONTRALORIA,
        "data/bronze/contraloria.csv",
    )

    assert pd.isna(df.loc[1, "hallazgos_administrativos"])
    assert df.loc[1, "sujeto_auditado"] == "Entidad B"
    assert pd.isna(
        pd.read_csv("data/bronze/contraloria.csv").loc[
            1, "hallazgos_administrativos"
        ]
    )
    calidad = pd.read_csv("quality/contraloria_quality.csv")
    assert calidad.loc[
        calidad["columna"] == "hallazgos_administrativos",
        "valores_nulos_o_vacios",
    ].iloc[0] == 1


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


def test_procuraduria_descarga_paginada_sin_perder_ni_repetir(monkeypatch):
    import extract.extract_procuraduria as proc

    filas = [f"{i},{1000 + i}" for i in range(7)]            # 7 filas, páginas de 3 -> 3 solicitudes
    pedidos = []

    def falso_get(url, timeout=None):
        pedidos.append(url)
        offset = int(url.split("%24offset=")[1].split("&")[0])
        return RespuestaFalsa(200, texto="numero_siri,numero_identificacion\n" + "\n".join(filas[offset:offset + 3]) + "\n")

    falso_get_resp = lambda url, timeout=None: _con_raise(falso_get(url, timeout))
    monkeypatch.setattr(proc.requests, "get", falso_get_resp)

    df = proc.descargar_paginado("https://x.test/r.csv?$limit=1000&$order=fecha%20DESC", tamano_pagina=3)

    assert len(df) == 7 and df["numero_siri"].is_unique
    assert len(pedidos) == 3
    assert all("%24limit=3" in p and "%3Aid" in p for p in pedidos)       # ignora el $limit/$order original
    assert "fecha" not in pedidos[0]


def _con_raise(resp):
    resp.raise_for_status = lambda: None
    return resp
def test_policia_pagina_y_quita_columnas_internas(monkeypatch):
    encabezado = ":id,:created_at,:updated_at,:version,departamento,descripcion_conducta_captura,cantidad\n"
    paginas = [
        encabezado + "row-1,x,x,x,BOGOTA,ARTÍCULO 397. PECULADO POR APROPIACIÓN,1\nrow-2,x,x,x,ANTIOQUIA,ARTÍCULO 407. COHECHO POR DAR U OFRECER,1\n",
        encabezado + "row-3,x,x,x,VALLE,ARTÍCULO 410. CONTRATO SIN CUMPLIMIENTO DE REQUISITO LEGALES,1\n",
    ]
    llamadas = []

    def get_falso(url, params, timeout):
        llamadas.append(params["$where"])
        return RespuestaFalsa(200, texto=paginas[len(llamadas) - 1])

    monkeypatch.setattr(policia.requests, "get", get_falso)

    total = policia.extraer_datos_policia("3jdh-nmwu", "data/bronze/policia.csv", tamano_pagina=2)
    df = pd.read_csv("data/bronze/policia.csv")

    assert total == 3
    assert list(df.columns) == ["departamento", "descripcion_conducta_captura", "cantidad"]
    assert ":id > 'row-2'" in llamadas[1]


def test_policia_falla_despues_de_reintentos(monkeypatch):
    monkeypatch.setattr(policia.requests, "get", lambda url, params, timeout: RespuestaFalsa(503))
    monkeypatch.setattr(policia.time, "sleep", lambda s: None)

    assert policia.extraer_datos_policia("3jdh-nmwu", "data/bronze/policia.csv") is None
