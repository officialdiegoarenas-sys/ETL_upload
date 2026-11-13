import os
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Rutas del proyecto
RUTA_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_DB = os.path.join(RUTA_BASE, "data_warehouse", "warehouse.db")

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
        "rutas": ["/health", "/fuentes", "/resumen", "/buscar?q=texto"],
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
