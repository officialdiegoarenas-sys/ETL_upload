"""Pipeline medallón para procesos anonimizados de Fiscalía y datos SECOP."""

from __future__ import annotations

import logging
from pathlib import Path

from extract.extract_datos_fiscalia import (
    MAX_REGISTROS_MUESTRA,
    URL_DATOS_FISCALIA,
    URL_DATOS_SECOP,
    extraer_datos_api,
)
from load.load_datos_fiscalia import generar_datos_gold
from transform.transform_datos_fiscalia import transformar_datos

logger = logging.getLogger(__name__)
_RAIZ_PROYECTO = Path(__file__).resolve().parents[2]


def ejecutar_pipeline_datos_fiscalia() -> dict[str, int]:
    """Ejecuta las capas Bronze, Silver y Gold para las dos APIs solicitadas."""
    resultados: dict[str, int] = {}
    for nombre, url in (
        ("datos_fiscalia", URL_DATOS_FISCALIA),
        ("datos_secop", URL_DATOS_SECOP),
    ):
        bronze = _RAIZ_PROYECTO / "data" / "bronze" / f"{nombre}_raw.json"
        silver = _RAIZ_PROYECTO / "data" / "silver" / f"{nombre}_silver.csv"
        gold = _RAIZ_PROYECTO / "data" / "gold" / f"{nombre}_gold.csv"
        calidad = _RAIZ_PROYECTO / "data" / "quality" / f"{nombre}_quality.csv"
        tipo_dataset = nombre.removeprefix("datos_")

        logger.info("[%s] Extrayendo Bronze desde %s", nombre, url)
        filas_extraidas = extraer_datos_api(
            url, bronze, max_records=MAX_REGISTROS_MUESTRA
        )
        logger.info("[%s] Transformando Silver y validando calidad", nombre)
        df_silver = transformar_datos(
            bronze, silver, tipo_dataset, calidad
        )
        logger.info("[%s] Generando agregados Gold", nombre)
        df_gold = generar_datos_gold(silver, gold, tipo_dataset)

        resultados[nombre] = len(df_silver)
        logger.info(
            "[%s] Finalizado: %s registros Bronze/Silver y %s agregados Gold.",
            nombre,
            filas_extraidas,
            len(df_gold),
        )
    return resultados
