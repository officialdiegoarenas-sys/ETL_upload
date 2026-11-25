import os
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Rutas del proyecto
RUTA_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_DB = os.path.join(RUTA_BASE, "data_warehouse", "warehouse.db")

# La lógica de consulta vive en src/data_warehouse (la comparten la API y el ETL)
sys.path.insert(0, os.path.join(RUTA_BASE, "src"))
from data_warehouse import consulta as consulta_unificada  # noqa: E402
from agente.agente_entidades import AgenteEntidadesControl  # noqa: E402

app = FastAPI(
    title="API ETL - Consulta de fuentes de datos",
    description="Junta los datos de Fiscalía, SECOP, Procuraduría y Contraloría en un solo lugar.",
    version="0.1.0",
)

# Para que un front (React, HTML, etc.) pueda consumir la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


FUENTES = {
    "fiscalia": {
        "nombre": "Fiscalía General de la Nación",
        "descripcion": "Procesos penales anonimizados: delitos, etapas, departamentos y sentencias.",
        "tablas": [
            "datos_fiscalia",
            "fiscalia_perfil_condenados",
            "fiscalia_procesados_sentencias",
            "fiscalia_procesos_a_o_capitulo",
            "fiscalia_procesos_departamento",
            "fiscalia_procesos_etapa",
            "fiscalia_top_delitos",
        ],
        "conclusiones": "conclusiones_fiscalia.md",
    },
    "secop": {
        "nombre": "SECOP II",
        "descripcion": "Contratación pública: procesos por entidad, modalidad y estado.",
        "tablas": ["datos_secop", "resumen_contratos"],
        "conclusiones": "conclusiones_secop_ii.md",
    },
    "procuraduria": {
        "nombre": "Procuraduría General de la Nación",
        "descripcion": "Sanciones disciplinarias por entidad.",
        "tablas": ["resumen_procuraduria"],
        "conclusiones": "conclusiones_procuraduria.md",
    },
    "contraloria": {
        "nombre": "Contraloría General de la República",
        "descripcion": "Resultado de la ejecución del plan de vigilancia y control fiscal.",
        "tablas": ["dataset_contraloria"],
        "conclusiones": "conclusiones_contraloria.md",
    },
}


def conectar():
    if not os.path.exists(RUTA_DB):
        raise HTTPException(
            status_code=503,
            detail="No existe el data warehouse. Ejecute primero main.py",
        )
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    return conexion


def existe_tabla(conexion, tabla):
    fila = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
    ).fetchone()
    return fila is not None


def columnas_tabla(conexion, tabla):
    # Se ocultan las columnas internas del warehouse (_dw_...)
    columnas = [fila["name"] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')]
    return [c for c in columnas if not c.startswith("_dw_")]


def validar_fuente(fuente):
    if fuente not in FUENTES:
        raise HTTPException(
            status_code=404,
            detail=f"Fuente '{fuente}' no existe. Opciones: {list(FUENTES)}",
        )


def validar_tabla(fuente, tabla):
    validar_fuente(fuente)
    if tabla not in FUENTES[fuente]["tablas"]:
        raise HTTPException(
            status_code=404,
            detail=f"La tabla '{tabla}' no pertenece a {fuente}. Opciones: {FUENTES[fuente]['tablas']}",
        )



@app.get("/")
def inicio():
    return {
        "proyecto": "ETL - Fiscalía, SECOP, Procuraduría y Contraloría",
        "docs": "/docs",
        "rutas": [
            "/health",
            "/fuentes",
            "/resumen",
            "/buscar?q=texto",
            "/gold",
            "/gold/{dataset}",
            "/consulta?q=cedula_o_proceso",
            "/agente/consulta?q=pregunta",
            "/agente/sugerencias",
        ],
    }


@app.get("/health")
def health():
    # Revisa que la API esté arriba y que exista la base de datos
    return {"estado": "ok", "base_de_datos": os.path.exists(RUTA_DB)}




@app.get("/fuentes")
def listar_fuentes():
    # Lista de fuentes con la cantidad de tablas que tiene cada una
    resultado = []
    for clave, info in FUENTES.items():
        resultado.append({
            "fuente": clave,
            "nombre": info["nombre"],
            "descripcion": info["descripcion"],
            "tablas": len(info["tablas"]),
        })
    return resultado


@app.get("/fuentes/{fuente}")
def detalle_fuente(fuente: str):
    validar_fuente(fuente)
    conexion = conectar()

    tablas = []
    for tabla in FUENTES[fuente]["tablas"]:
        if existe_tabla(conexion, tabla):
            total = conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
            tablas.append({
                "tabla": tabla,
                "filas": total,
                "columnas": columnas_tabla(conexion, tabla),
            })
        else:
            tablas.append({"tabla": tabla, "filas": 0, "columnas": [], "aviso": "aún no cargada"})

    conexion.close()
    return {
        "fuente": fuente,
        "nombre": FUENTES[fuente]["nombre"],
        "descripcion": FUENTES[fuente]["descripcion"],
        "tablas": tablas,
    }


@app.get("/datos/{fuente}/{tabla}")
def ver_datos(
    fuente: str,
    tabla: str,
    limite: int = Query(20, ge=1, le=500),
    desplazamiento: int = Query(0, ge=0),
):
    validar_tabla(fuente, tabla)
    conexion = conectar()

    if not existe_tabla(conexion, tabla):
        conexion.close()
        raise HTTPException(status_code=404, detail=f"La tabla '{tabla}' aún no está cargada en el warehouse.")

    columnas = columnas_tabla(conexion, tabla)
    lista_columnas = ", ".join(f'"{c}"' for c in columnas)
    total = conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]

    filas = conexion.execute(
        f'SELECT {lista_columnas} FROM "{tabla}" LIMIT ? OFFSET ?',
        (limite, desplazamiento),
    ).fetchall()
    conexion.close()

    return {
        "fuente": fuente,
        "tabla": tabla,
        "total": total,
        "limite": limite,
        "desplazamiento": desplazamiento,
        "datos": [dict(fila) for fila in filas],
    }




@app.get("/explicacion/{fuente}")
def explicacion(fuente: str):
    # Devuelve las conclusiones (archivo .md) de la fuente
    validar_fuente(fuente)
    ruta = os.path.join(RUTA_BASE, FUENTES[fuente]["conclusiones"])

    if not os.path.exists(ruta):
        raise HTTPException(status_code=404, detail="Esta fuente aún no tiene conclusiones.")

    with open(ruta, "r", encoding="utf-8") as archivo:
        texto = archivo.read()

    return {"fuente": fuente, "nombre": FUENTES[fuente]["nombre"], "conclusiones": texto}




@app.get("/resumen")
def resumen():
    # Conteo de filas por fuente, sirve para la portada del front
    conexion = conectar()
    resultado = []

    for clave, info in FUENTES.items():
        filas = 0
        cargadas = 0
        for tabla in info["tablas"]:
            if existe_tabla(conexion, tabla):
                cargadas += 1
                filas += conexion.execute(f'SELECT COUNT(*) FROM "{tabla}"').fetchone()[0]
        resultado.append({
            "fuente": clave,
            "nombre": info["nombre"],
            "tablas_cargadas": cargadas,
            "tablas_totales": len(info["tablas"]),
            "filas": filas,
        })

    conexion.close()
    return resultado


@app.get("/buscar")
def buscar(q: str = Query(..., min_length=2), max_por_tabla: int = Query(5, ge=1, le=50)):
    # Busca un texto en todas las tablas de todas las fuentes
    conexion = conectar()
    resultado = []

    for clave, info in FUENTES.items():
        for tabla in info["tablas"]:
            if not existe_tabla(conexion, tabla):
                continue

            columnas = columnas_tabla(conexion, tabla)
            lista_columnas = ", ".join(f'"{c}"' for c in columnas)
            condicion = " OR ".join(f'"{c}" LIKE ?' for c in columnas)
            parametros = [f"%{q}%"] * len(columnas) + [max_por_tabla]

            filas = conexion.execute(
                f'SELECT {lista_columnas} FROM "{tabla}" WHERE {condicion} LIMIT ?',
                parametros,
            ).fetchall()

            if filas:
                resultado.append({
                    "fuente": clave,
                    "tabla": tabla,
                    "coincidencias": [dict(fila) for fila in filas],
                })

    conexion.close()
    return {"busqueda": q, "resultados": resultado}




def _normalizar(nombre):
    # 'fiscalia_procesos_año_capitulo_gold' -> 'fiscalia_procesos_ano_capitulo'
    sin_tilde = "".join(c for c in unicodedata.normalize("NFKD", nombre) if not unicodedata.combining(c))
    return sin_tilde.lower().removesuffix("_gold")


def archivos_gold():
    carpeta = Path(RUTA_BASE) / "data" / "gold"
    if not carpeta.exists():
        return {}
    return {_normalizar(a.stem): a for a in sorted(carpeta.glob("*.csv"))}


@app.get("/gold")
def listar_gold():
    # Datasets de la capa Gold disponibles para el dashboard
    return [{"nombre": n, "archivo": a.name} for n, a in archivos_gold().items()]


@app.get("/gold/{nombre}")
def consultar_gold(nombre: str):
    # Devuelve un dataset Gold completo (lo consume el dashboard de la carpeta App)
    archivos = archivos_gold()
    if nombre not in archivos:
        raise HTTPException(status_code=404, detail=f"No existe el dataset Gold '{nombre}'. Opciones: {list(archivos)}")
    df = pd.read_csv(archivos[nombre], encoding="utf-8")
    df = df.astype(object).where(pd.notnull(df), None)
    return {
        "dataset": nombre,
        "total_registros": len(df),
        "Nombre_columnas": df.columns.tolist(),
        "Data": df.to_dict(orient="records"),
    }


@app.get("/consulta")
def consultar(q: str = Query(..., min_length=4, max_length=60, description="Cédula/NIT o número de proceso")):
    # Búsqueda unificada por cédula/NIT o número de proceso (solo coincidencias exactas)
    try:
        return consulta_unificada.buscar(q, RUTA_DB)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except consulta_unificada.ConsultaNoDisponible as error:
        raise HTTPException(status_code=503, detail=str(error))


@app.get("/cargas")
def historial_cargas(limite: int = Query(20, ge=1, le=200)):
    # Últimas cargas hechas al warehouse (para saber qué tan actuales son los datos)
    conexion = conectar()

    if not existe_tabla(conexion, "_dw_load_history"):
        conexion.close()
        return []

    filas = conexion.execute(
        "SELECT source_file, target_table, rows_inserted, rows_skipped, loaded_at "
        "FROM _dw_load_history ORDER BY id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    conexion.close()
    return [dict(fila) for fila in filas]


@app.get("/agente/consulta")
def agente_consulta(
    q: str = Query(..., min_length=2, description="Pregunta o entidad a consultar"),
    usar_ia: bool = Query(True, description="Usar modelo local Ollama si está disponible"),
    modelo: Optional[str] = Query(None, description="Modelo de Ollama (ej. qwen2.5:1.5b o llama3.1:latest)"),
):
    # Agente analítico que cruza la información de las 3 entidades de control (con IA local Ollama)
    try:
        agente = AgenteEntidadesControl(RUTA_DB)
        res = agente.consultar(q, usar_ia=usar_ia, modelo_ia=modelo)
        graficas_serializables = {}
        for k, v in res.get("graficas", {}).items():
            fig_dict = v["fig"].to_dict() if hasattr(v["fig"], "to_dict") else v["fig"]
            graficas_serializables[k] = {
                "titulo": v["titulo"],
                "descripcion": v["descripcion"],
                "figura": fig_dict,
            }
        res["graficas"] = graficas_serializables
        return res
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/agente/sugerencias")
def agente_sugerencias():
    # Preguntas recomendadas para el agente de integración
    return AgenteEntidadesControl.obtener_sugerencias()


@app.get("/agente/ollama/estado")
def agente_ollama_estado():
    # Verifica si Ollama está en línea y los modelos disponibles
    activo, modelos = AgenteEntidadesControl.verificar_ollama()
    return {"activo": activo, "modelos": modelos}

