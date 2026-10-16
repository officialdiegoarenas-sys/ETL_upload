"""Descarga paginada y preservación de respuestas de datos.gov.co."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

URL_DATOS_FISCALIA = "https://www.datos.gov.co/api/v3/views/piva-db2c/query.json"
URL_DATOS_SECOP = "https://www.datos.gov.co/api/v3/views/p6dx-8zbt/query.json"
MAX_REGISTROS_MUESTRA = 1_000


def extraer_datos_api(
    url: str,
    ruta_salida: str | os.PathLike[str],
    *,
    page_size: int = 1000,
    max_records: int = MAX_REGISTROS_MUESTRA,
    timeout_seconds: int = 60,
    max_retries: int = 3,
    session: requests.Session | None = None,
) -> int:
    """Guarda todas las filas como JSON Bronze y devuelve la cantidad descargada."""
    if page_size < 1:
        raise ValueError("page_size debe ser mayor que cero.")
    if max_records < 1:
        raise ValueError("max_records debe ser mayor que cero.")
    if max_retries < 1:
        raise ValueError("max_retries debe ser mayor que cero.")

    salida = Path(ruta_salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    propia_sesion = session is None
    cliente = session or requests.Session()
    temporal: str | None = None
    total = 0
    offset = 0
    paginas_vistas: set[str] = set()

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=salida.parent,
            prefix=f".{salida.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = archivo.name
            archivo.write("[")
            primera_fila = True

            while total < max_records:
                payload = _obtener_pagina(
                    cliente,
                    url,
                    offset,
                    min(page_size, max_records - total),
                    timeout_seconds,
                    max_retries,
                )
                if not payload:
                    break

                huella_pagina = hashlib.sha256(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                if huella_pagina in paginas_vistas:
                    raise RuntimeError(
                        f"La API repitió una página en offset {offset}; "
                        "se detiene la extracción para evitar un ciclo."
                    )
                paginas_vistas.add(huella_pagina)

                for fila in payload[: max_records - total]:
                    if not isinstance(fila, dict):
                        raise ValueError(
                            f"La API devolvió una fila que no es un objeto JSON "
                            f"(offset {offset})."
                        )
                    if not primera_fila:
                        archivo.write(",")
                    json.dump(fila, archivo, ensure_ascii=False, separators=(",", ":"))
                    primera_fila = False
                    total += 1

                offset += len(payload)
                logger.info("API %s: %s filas descargadas.", url, total)

            if total == 0:
                raise ValueError(f"La API no devolvió registros: {url}")
            archivo.write("]")

        os.replace(temporal, salida)
        temporal = None
        logger.info("Bronze guardado en %s (%s registros).", salida, total)
        return total
    finally:
        if propia_sesion:
            cliente.close()
        if temporal and os.path.exists(temporal):
            os.unlink(temporal)


def _obtener_pagina(
    session: requests.Session,
    url: str,
    offset: int,
    page_size: int,
    timeout_seconds: int,
    max_retries: int,
) -> list[dict[str, Any]]:
    params = {"$limit": page_size, "$offset": offset}
    for intento in range(max_retries):
        try:
            respuesta = session.get(url, params=params, timeout=timeout_seconds)
        except (requests.Timeout, requests.ConnectionError):
            if intento + 1 == max_retries:
                raise
            espera = min(2**intento, 10)
            logger.warning(
                "Error de conexión en offset %s; reintento en %s segundos.",
                offset,
                espera,
            )
            time.sleep(espera)
            continue

        if respuesta.status_code == 429 or respuesta.status_code >= 500:
            if intento + 1 == max_retries:
                respuesta.raise_for_status()
            espera = min(2**intento, 10)
            logger.warning(
                "La API respondió %s en offset %s; reintento en %s segundos.",
                respuesta.status_code,
                offset,
                espera,
            )
            time.sleep(espera)
            continue

        respuesta.raise_for_status()
        payload = respuesta.json()
        if not isinstance(payload, list):
            raise ValueError(
                f"Se esperaba una lista JSON en offset {offset}; "
                f"se recibió {type(payload).__name__}."
            )
        if not all(isinstance(fila, dict) for fila in payload):
            raise ValueError(f"La API devolvió filas inválidas en offset {offset}.")
        return payload

    raise RuntimeError(f"No se pudo obtener la página con offset {offset}.")
