import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import pandas as pd

from src.extract.extract_datos_fiscalia import extraer_datos_api
from src.load.load_datos_fiscalia import generar_datos_gold
from src.transform.transform_datos_fiscalia import transformar_datos


class TestDatosFiscaliaPipeline(unittest.TestCase):
    def test_extractor_paginates_and_saves_complete_json(self):
        filas = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        session = Mock()
        session.get.side_effect = [
            _respuesta(filas[:2]),
            _respuesta(filas[2:]),
            _respuesta([]),
        ]

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta) / "bronze.json"
            total = extraer_datos_api(
                "https://api.test/dataset",
                salida,
                page_size=2,
                session=session,
            )

            self.assertEqual(total, 3)
            self.assertEqual(json.loads(salida.read_text(encoding="utf-8")), filas)
            self.assertEqual(
                [llamada.kwargs["params"]["$offset"] for llamada in session.get.call_args_list],
                [0, 2, 3],
            )

    def test_extractor_stops_at_maximum_records(self):
        session = Mock()
        session.get.side_effect = [
            _respuesta([{"id": "1"}, {"id": "2"}]),
            _respuesta([{"id": "3"}, {"id": "4"}]),
        ]

        with tempfile.TemporaryDirectory() as carpeta:
            salida = Path(carpeta) / "bronze.json"
            total = extraer_datos_api(
                "https://api.test/dataset",
                salida,
                page_size=2,
                max_records=3,
                session=session,
            )

            self.assertEqual(total, 3)
            self.assertEqual(
                json.loads(salida.read_text(encoding="utf-8")),
                [{"id": "1"}, {"id": "2"}, {"id": "3"}],
            )
            self.assertEqual(session.get.call_count, 2)
            self.assertEqual(
                [llamada.kwargs["params"]["$offset"] for llamada in session.get.call_args_list],
                [0, 2],
            )

    def test_fiscalia_transform_deduplicates_and_reports_numeric_quality(self):
        filas = [
            {
                "proceso_anonimizado": "p1",
                "delito": "Estafa",
                "estado": "Inactivo",
                "etapa": "Indagación",
                "deli_id": "771",
                "a_o_hecho_origen": "2010",
                "fecha_actualizacion_datos": "30/09/2026",
                ":id": "row-1",
            },
            {
                "proceso_anonimizado": "p1",
                "delito": "Estafa",
                "estado": "Inactivo",
                "etapa": "Indagación",
                "deli_id": "771",
                "a_o_hecho_origen": "2010",
                "fecha_actualizacion_datos": "30/09/2026",
                ":id": "row-2",
            },
            {
                "proceso_anonimizado": "p2",
                "delito": "Hurto",
                "estado": "Activo",
                "etapa": "Indagación",
                "deli_id": "dato-invalido",
                "a_o_hecho_origen": "2022",
                "fecha_actualizacion_datos": "fecha-invalida",
                ":id": "row-3",
            },
            {":id": "row-empty"},
        ]
        with tempfile.TemporaryDirectory() as carpeta:
            origen = Path(carpeta) / "bronze.json"
            salida = Path(carpeta) / "silver.csv"
            calidad = Path(carpeta) / "quality.csv"
            origen.write_text(json.dumps(filas), encoding="utf-8")

            df = transformar_datos(origen, salida, "fiscalia", calidad)
            reporte = pd.read_csv(calidad).set_index("columna")

            self.assertEqual(len(df), 2)
            self.assertNotIn(":id", df.columns)
            self.assertEqual(str(df.loc[0, "fecha_actualizacion_datos"]), "2026-09-30")
            self.assertEqual(reporte.loc["deli_id", "valores_invalidos"], 1)
            self.assertEqual(
                reporte.loc["fecha_actualizacion_datos", "valores_invalidos"], 1
            )
            self.assertEqual(reporte.loc["delito", "filas_entrada"], 4)
            self.assertEqual(reporte.loc["delito", "duplicados_eliminados"], 1)
            self.assertEqual(reporte.loc["delito", "registros_vacios_eliminados"], 1)

    def test_secop_gold_aggregates_counts_and_prices(self):
        with tempfile.TemporaryDirectory() as carpeta:
            origen = Path(carpeta) / "silver.csv"
            salida = Path(carpeta) / "gold.csv"
            pd.DataFrame(
                [
                    {
                        "id_del_proceso": "p1",
                        "entidad": "Entidad A",
                        "modalidad_de_contratacion": "Directa",
                        "estado_del_procedimiento": "Seleccionado",
                        "precio_base": 100.0,
                    },
                    {
                        "id_del_proceso": "p1",
                        "entidad": "Entidad A",
                        "modalidad_de_contratacion": "Directa",
                        "estado_del_procedimiento": "Seleccionado",
                        "precio_base": 100.0,
                    },
                    {
                        "id_del_proceso": "p2",
                        "entidad": "Entidad A",
                        "modalidad_de_contratacion": "Directa",
                        "estado_del_procedimiento": "Seleccionado",
                        "precio_base": 300.0,
                    },
                ]
            ).to_csv(origen, index=False)

            gold = generar_datos_gold(origen, salida, "secop")

            self.assertEqual(gold.loc[0, "total_procesos"], 2)
            self.assertEqual(gold.loc[0, "precio_base_total"], 500.0)
            self.assertEqual(gold.loc[0, "precio_base_promedio"], 500.0 / 3)


def _respuesta(payload):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


if __name__ == "__main__":
    unittest.main()
