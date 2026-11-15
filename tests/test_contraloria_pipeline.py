import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import main as orchestrator


def test_modulo_contraloria_usa_api_aunque_haya_csv_local(tmp_path, monkeypatch):
    csv_local = tmp_path / "contraloria.csv"
    csv_local.write_text("dato\nlocal\n", encoding="utf-8")
    monkeypatch.setenv("CONTRALORIA_CSV", str(csv_local))
    monkeypatch.setattr(
        orchestrator,
        "ruta",
        lambda *partes: str(tmp_path.joinpath(*partes)),
    )
    llamadas = []

    def extraer(url, destino):
        llamadas.append(("api", url, destino))

    def transformar(entrada, salida):
        llamadas.append(("silver", entrada, salida))
        return pd.DataFrame({"dato": ["api"]})

    def generar(entrada, salida, conclusiones):
        llamadas.append(("gold", entrada, salida, conclusiones))

    monkeypatch.setattr(orchestrator, "extraer_datos_contraloria", extraer)
    monkeypatch.setattr(orchestrator, "transformar_datos_contraloria", transformar)
    monkeypatch.setattr(orchestrator, "generar_dataset_contraloria", generar)

    orchestrator.modulo_contraloria()

    assert llamadas[0][0:2] == ("api", orchestrator.URL_API_CONTRALORIA)
    assert [llamada[0] for llamada in llamadas] == ["api", "silver", "gold"]
