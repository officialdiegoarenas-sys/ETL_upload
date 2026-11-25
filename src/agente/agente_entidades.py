"""Motor del Agente Analítico de Integración de Entidades de Control.

Cruza la información de las 3 entidades principales de control y justicia en Colombia:
1. Fiscalía General de la Nación (procesos penales y delitos contra la adm. pública)
2. Procuraduría General de la Nación (sanciones disciplinarias e inhabilidades a servidores)
3. Contraloría General de la República (auditorías, hallazgos fiscales/penales/disciplinarios y cuantía)
Además integra datos de contratación pública (SECOP II) para complementar el panorama interinstitucional.
"""
from __future__ import annotations

import re
import os
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Rutas estándar del proyecto
RUTA_BASE = Path(__file__).resolve().parent.parent.parent
RUTA_DB_DEFAULT = RUTA_BASE / "data_warehouse" / "warehouse.db"
RUTA_GOLD_DEFAULT = RUTA_BASE / "data" / "gold"

# Colores institucionales alineados con el proyecto
AZUL = "#0A3D91"
AZUL_OSC = "#062A66"
AMARILLO = "#FFD100"
ROJO = "#C8102E"
VERDE = "#00875A"
GRIS = "#5B6575"

OLLAMA_URL_DEFAULT = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
MODELOS_OLLAMA_PREFERIDOS = ["qwen2.5:1.5b", "llama3.1:latest", "llama3.1", "qwen2.5"]

DEPARTAMENTOS_COLOMBIA = [
    "AMAZONAS", "ANTIOQUIA", "ARAUCA", "ATLANTICO", "BOGOTA", "BOLIVAR",
    "BOYACA", "CALDAS", "CAQUETA", "CASANARE", "CAUCA", "CESAR", "CHOCO",
    "CORDOBA", "CUNDINAMARCA", "GUAINIA", "GUAVIARE", "HUILA", "LA GUAJIRA",
    "MAGDALENA", "META", "NARINO", "NORTE DE SANTANDER", "PUTUMAYO", "QUINDIO",
    "RISARALDA", "SAN ANDRES", "SANTANDER", "SUCRE", "TOLIMA", "VALLE DEL CAUCA",
    "VAUPES", "VICHADA"
]

DELITOS_COMUNES = {
    "CELEBRACION INDEBIDA DE CONTRATOS": ["CONTRAT", "LICITACION", "ADJUDICAC"],
    "PECULADO POR APROPIACION": ["PECULADO", "APROPIACION", "DESVIO"],
    "PREVARICATO": ["PREVARICATO", "RESOLUCION MANIFIESTAMENTE CONTRARIA"],
    "CONCUSION": ["CONCUSION", "EXIGIR DINERO"],
    "COHECHO": ["COHECHO", "SOBORNO"],
    "ENRIQUECIMIENTO ILICITO": ["ENRIQUECIMIENTO"],
}


def norm_str(texto: Any) -> str:
    """Normaliza texto eliminando acentos, espacios múltiples y pasando a mayúsculas."""
    if texto is None:
        return ""
    t = "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip().upper()


def fmt_numero(n: float | int, decimales: int = 0) -> str:
    """Formatea números con separador de miles en punto (estilo colombiano)."""
    try:
        val = float(n)
        res = f"{val:,.{decimales}f}"
        return res.replace(",", "§").replace(".", ",").replace("§", ".")
    except (ValueError, TypeError):
        return str(n)


def fmt_dinero(valor: float | int) -> str:
    """Formatea cuantías monetarias en pesos colombianos."""
    try:
        v = float(valor)
        if abs(v) >= 1e12:
            return "$" + fmt_numero(v / 1e12, 2) + " billones COP"
        if abs(v) >= 1e9:
            return "$" + fmt_numero(v / 1e9, 1) + " mil millones COP"
        if abs(v) >= 1e6:
            return "$" + fmt_numero(v / 1e6, 0) + " millones COP"
        return "$" + fmt_numero(v) + " COP"
    except (ValueError, TypeError):
        return "$0 COP"


def _valor_consulta(datos: Dict[str, Any], clave_filtro: str, clave_total: str) -> Any:
    """Respeta un resultado filtrado igual a cero; solo usa el total si no hubo filtro."""
    return datos[clave_filtro] if clave_filtro in datos else datos.get(clave_total, 0)


class AgenteEntidadesControl:
    """Agente que analiza y unifica la información de las 3 entidades de control."""

    def __init__(self, db_path: Path | str | None = None, gold_dir: Path | str | None = None):
        self.db_path = Path(db_path or RUTA_DB_DEFAULT)
        self.gold_dir = Path(gold_dir or RUTA_GOLD_DEFAULT)

    def _conectar(self) -> Optional[sqlite3.Connection]:
        if self.db_path.exists():
            con = sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            return con
        return None

    def _leer_gold_csv(self, nombre_csv: str) -> Optional[pd.DataFrame]:
        archivo = self.gold_dir / nombre_csv
        if archivo.exists():
            try:
                return pd.read_csv(archivo, encoding="utf-8")
            except Exception:
                return None
        return None

    def detectar_filtros(self, pregunta: str) -> Dict[str, Any]:
        """Detecta entidades, departamentos, tipos de delito o intención general en la pregunta."""
        norm = norm_str(pregunta)
        filtros: Dict[str, Any] = {
            "pregunta_original": pregunta,
            "pregunta_norm": norm,
            "departamento": None,
            "entidad_buscada": None,
            "tema_delito": None,
            "es_resumen_general": False,
            "palabras_clave": [],
        }

        # Detección de departamento
        for dep in DEPARTAMENTOS_COLOMBIA:
            if re.search(rf"\b{dep}\b", norm):
                filtros["departamento"] = dep
                break
        if not filtros["departamento"]:
            if "BOGOTA" in norm:
                filtros["departamento"] = "BOGOTA"
            elif "MEDELLIN" in norm or "ANTIOQUIA" in norm:
                filtros["departamento"] = "ANTIOQUIA"
            elif "CALI" in norm or "VALLE" in norm:
                filtros["departamento"] = "VALLE DEL CAUCA"
            elif "BARRANQUILLA" in norm:
                filtros["departamento"] = "ATLANTICO"

        # Detección de entidades emblemáticas
        entidades_clave = [
            ("POLICIA NACIONAL", ["POLICIA", "PONAL", "PATRULLERO", "POLICIA NACIONAL DE COLOMBIA"]),
            ("MINISTERIO DE DEFENSA", ["MINDEFENSA", "MINISTERIO DE DEFENSA", "FUERZAS MILITARES", "EJERCITO"]),
            ("INPEC", ["INPEC", "INSTITUTO NACIONAL PENITENCIARIO"]),
            ("ALCALDIA MAYOR DE BOGOTA", ["ALCALDIA DE BOGOTA", "ALCALDIA MAYOR"]),
            ("ALCALDIA DE MEDELLIN", ["ALCALDIA DE MEDELLIN"]),
            ("GOBERNACION DE ANTIOQUIA", ["GOBERNACION DE ANTIOQUIA"]),
            ("SENA", ["SENA", "SERVICIO NACIONAL DE APRENDIZAJE"]),
            ("ICBF", ["ICBF", "INSTITUTO COLOMBIANO DE BIENESTAR FAMILIAR"]),
            ("CONTRALORIA GENERAL", ["CONTRALORIA GENERAL", "CGR"]),
            ("PROCURADURIA GENERAL", ["PROCURADURIA GENERAL", "PGN"]),
            ("FISCALIA GENERAL", ["FISCALIA GENERAL", "FGN"]),
            ("DIAN", ["DIAN", "DIRECCION DE IMPUESTOS"]),
            ("REGISTRADURIA", ["REGISTRADURIA"]),
            ("MINISTERIO DE EDUCACION", ["MINEDUCACION", "MINISTERIO DE EDUCACION"]),
            ("MINISTERIO DE SALUD", ["MINSALUD", "MINISTERIO DE SALUD"]),
        ]

        for nombre_oficial, alias in entidades_clave:
            if any(a in norm for a in alias):
                filtros["entidad_buscada"] = nombre_oficial
                break

        # Si no se detectó una de las fijas, buscar palabras genéricas de entidad (ej. "ALCALDIA", "HOSPITAL")
        if not filtros["entidad_buscada"]:
            m = re.search(r"\b(ALCALDIA|GOBERNACION|HOSPITAL|SECRETARIA|INSTITUTO|UNIVERSIDAD|CONCEJO)\b\s+([A-ZÁÉÍÓÚÑ]+)", norm)
            if m:
                filtros["entidad_buscada"] = m.group(0)

        # Detección de tema penal o tipo de irregularidad
        for delito, patrones in DELITOS_COMUNES.items():
            if any(p in norm for p in patrones):
                filtros["tema_delito"] = delito
                break

        # ¿Es pregunta general o de cruce macro?
        frases_generales = ["GENERAL", "TODO", "RESUMEN", "MACRO", "COMPARAR", "CRUCE", "3 ENTIDADES", "TRES ENTIDADES", "PANORAMA", "ESTADO"]
        if any(f in norm for f in frases_generales) or (not filtros["departamento"] and not filtros["entidad_buscada"] and not filtros["tema_delito"]):
            filtros["es_resumen_general"] = True

        return filtros

    def _consultar_fiscalia(self, filtros: Dict[str, Any], con: Optional[sqlite3.Connection]) -> Dict[str, Any]:
        """Extrae métricas de la Fiscalía (procesos penales, departamentos y top delitos)."""
        res: Dict[str, Any] = {
            "nombre": "Fiscalía General de la Nación",
            "alcance": "Procesos penales por delitos contra la adm. pública (datos anonimizados)",
            "total_procesos": 0,
            "procesos_activos": 0,
            "pct_activos": 0.0,
            "departamento_info": None,
            "top_delitos": [],
            "datos_grafica": {},
        }

        dep_filtro = filtros.get("departamento")

        if con:
            try:
                filas_dep = con.execute("SELECT * FROM fiscalia_procesos_departamento").fetchall()
                deps_dict = {}
                tot_proc = 0
                tot_act = 0
                for r in filas_dep:
                    t_proc = int(float(r["total_procesos"] or 0))
                    t_act = int(float(r["procesos_activos"] or 0))
                    p_act = float(r["pct_activos"] or 0)
                    tot_proc += t_proc
                    tot_act += t_act
                    d_data = dict(r)
                    d_data["total_procesos"] = t_proc
                    d_data["procesos_activos"] = t_act
                    d_data["pct_activos"] = p_act
                    deps_dict[norm_str(r["departamento_hecho"])] = d_data

                res["total_procesos"] = tot_proc
                res["procesos_activos"] = tot_act
                res["pct_activos"] = round((tot_act / tot_proc * 100), 1) if tot_proc else 0.0

                if dep_filtro and dep_filtro in deps_dict:
                    d = deps_dict[dep_filtro]
                    res["departamento_info"] = {
                        "departamento": d["departamento_hecho"],
                        "total_procesos": d["total_procesos"],
                        "procesos_activos": d["procesos_activos"],
                        "pct_activos": d["pct_activos"],
                    }

                # Top delitos
                filas_del = con.execute("SELECT delito, articulo, capitulo_delito, total FROM fiscalia_top_delitos ORDER BY CAST(total AS INTEGER) DESC LIMIT 7").fetchall()
                del_list = []
                for r in filas_del:
                    rd = dict(r)
                    rd["total"] = int(float(r["total"] or 0))
                    del_list.append(rd)
                res["top_delitos"] = del_list

                # Top departamentos para gráficas
                top_deps = con.execute("SELECT departamento_hecho, total_procesos, procesos_activos FROM fiscalia_procesos_departamento ORDER BY CAST(total_procesos AS INTEGER) DESC LIMIT 10").fetchall()
                res["datos_grafica"]["top_departamentos"] = [
                    {"departamento_hecho": r["departamento_hecho"], "total_procesos": int(float(r["total_procesos"] or 0)), "procesos_activos": int(float(r["procesos_activos"] or 0))}
                    for r in top_deps
                ]
            except Exception:
                pass
        else:
            # Fallback a CSV Gold
            df_dep = self._leer_gold_csv("fiscalia_procesos_departamento_gold.csv")
            if df_dep is not None:
                tot_proc = int(df_dep["total_procesos"].sum())
                tot_act = int(df_dep["procesos_activos"].sum())
                res["total_procesos"] = tot_proc
                res["procesos_activos"] = tot_act
                res["pct_activos"] = round((tot_act / tot_proc * 100), 1) if tot_proc else 0.0
                if dep_filtro:
                    sub = df_dep[df_dep["departamento_hecho"].str.upper().str.contains(dep_filtro, na=False)]
                    if not sub.empty:
                        row = sub.iloc[0]
                        res["departamento_info"] = {
                            "departamento": row["departamento_hecho"],
                            "total_procesos": int(row["total_procesos"]),
                            "procesos_activos": int(row["procesos_activos"]),
                            "pct_activos": float(row["pct_activos"]),
                        }

        return res

    def _consultar_procuraduria(self, filtros: Dict[str, Any], con: Optional[sqlite3.Connection]) -> Dict[str, Any]:
        """Extrae sanciones disciplinarias de la Procuraduría (SIRI)."""
        res: Dict[str, Any] = {
            "nombre": "Procuraduría General de la Nación",
            "alcance": "Sanciones disciplinarias ejecutoriadas e inhabilidades a servidores públicos",
            "total_sanciones": 0,
            "entidades_top": [],
            "tipos_sancion": [],
            "coincidencias": [],
            "cargos_frecuentes": [],
        }

        dep_filtro = filtros.get("departamento")
        ent_filtro = filtros.get("entidad_buscada")
        pregunta_norm = filtros.get("pregunta_norm", "")

        if con:
            try:
                # Total general
                tot = con.execute("SELECT COUNT(*) FROM gold_consulta_sanciones").fetchone()[0]
                res["total_sanciones"] = tot

                # Si hay filtro de entidad o departamento específico
                condiciones = []
                params: List[Any] = []

                if ent_filtro:
                    condiciones.append("UPPER(entidad) LIKE ?")
                    params.append(f"%{ent_filtro}%")
                elif dep_filtro:
                    condiciones.append("UPPER(departamento) LIKE ?")
                    params.append(f"%{dep_filtro}%")
                elif not filtros.get("es_resumen_general"):
                    # Extraer términos significativos
                    terminos = [w for w in pregunta_norm.split() if len(w) > 3 and w not in ["SOBRE", "DIME", "CUANTAS", "CUANTOS", "TIENE", "ESTA", "ESTE", "COMO", "CUAL", "CUALES"]]
                    if terminos:
                        subc = " OR ".join(["UPPER(entidad) LIKE ?" for _ in terminos])
                        condiciones.append(f"({subc})")
                        params.extend([f"%{t}%" for t in terminos])

                where_sql = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""

                # Conteo específico según filtros
                if where_sql:
                    cnt_especifico = con.execute(f"SELECT COUNT(*) FROM gold_consulta_sanciones {where_sql}", params).fetchone()[0]
                    res["total_sanciones_filtro"] = cnt_especifico

                    # Muestra de sanciones encontradas
                    filas_muestras = con.execute(
                        f"SELECT id_norm, nombre, cargo, entidad, departamento, municipio, sanciones, duracion, fecha_efectos, numero_proceso "
                        f"FROM gold_consulta_sanciones {where_sql} LIMIT 10", params
                    ).fetchall()
                    res["coincidencias"] = [dict(r) for r in filas_muestras]

                    # Tipos de sanción en este subconjunto
                    filas_tipos = con.execute(
                        f"SELECT sanciones, COUNT(*) as cantidad FROM gold_consulta_sanciones {where_sql} "
                        f"GROUP BY sanciones ORDER BY cantidad DESC LIMIT 6", params
                    ).fetchall()
                    res["tipos_sancion"] = [dict(r) for r in filas_tipos]

                    # Cargos más sancionados
                    filas_cargos = con.execute(
                        f"SELECT cargo, COUNT(*) as cantidad FROM gold_consulta_sanciones {where_sql} "
                        f"GROUP BY cargo ORDER BY cantidad DESC LIMIT 5", params
                    ).fetchall()
                    res["cargos_frecuentes"] = [dict(r) for r in filas_cargos]
                else:
                    # Resumen general: top entidades
                    top_e = con.execute(
                        "SELECT entidad, COUNT(*) as total FROM gold_consulta_sanciones GROUP BY entidad ORDER BY total DESC LIMIT 7"
                    ).fetchall()
                    res["entidades_top"] = [dict(r) for r in top_e]

                    # Tipos generales
                    filas_tipos = con.execute(
                        "SELECT sanciones, COUNT(*) as cantidad FROM gold_consulta_sanciones GROUP BY sanciones ORDER BY cantidad DESC LIMIT 5"
                    ).fetchall()
                    res["tipos_sancion"] = [dict(r) for r in filas_tipos]
            except Exception:
                pass
        else:
            # Fallback a CSV Gold
            df_proc = self._leer_gold_csv("resumen_procuraduria_gold.csv")
            if df_proc is not None:
                res["total_sanciones"] = int(df_proc["total_sanciones"].sum())
                top_df = df_proc.sort_values("total_sanciones", ascending=False).head(7)
                res["entidades_top"] = top_df.to_dict(orient="records")

        return res

    def _consultar_contraloria(self, filtros: Dict[str, Any], con: Optional[sqlite3.Connection]) -> Dict[str, Any]:
        """Extrae auditorías, hallazgos administrativos/disciplinarios/fiscales/penales y cuantía."""
        res: Dict[str, Any] = {
            "nombre": "Contraloría General de la República",
            "alcance": "Ejecución del plan de vigilancia y control fiscal a sujetos auditados",
            "total_sujetos": 0,
            "total_auditorias": 0,
            "hallazgos_fiscales": 0,
            "hallazgos_penales": 0,
            "hallazgos_disciplinarios": 0,
            "hallazgos_administrativos": 0,
            "cuantia_total": 0.0,
            "coincidencias": [],
            "top_entidades_cuantia": [],
        }

        dep_filtro = filtros.get("departamento")
        ent_filtro = filtros.get("entidad_buscada")
        pregunta_norm = filtros.get("pregunta_norm", "")

        if con:
            try:
                # Totales globales de Contraloría
                row_tot = con.execute(
                    "SELECT COUNT(*) as sujetos, SUM(registros) as aud, SUM(fiscales) as fisc, "
                    "SUM(penales) as pen, SUM(disciplinarios) as disc, SUM(administrativos) as adm, SUM(cuantia) as cuan "
                    "FROM gold_consulta_contraloria"
                ).fetchone()

                if row_tot and row_tot["sujetos"]:
                    res["total_sujetos"] = row_tot["sujetos"]
                    res["total_auditorias"] = row_tot["aud"] or 0
                    res["hallazgos_fiscales"] = row_tot["fisc"] or 0
                    res["hallazgos_penales"] = row_tot["pen"] or 0
                    res["hallazgos_disciplinarios"] = row_tot["disc"] or 0
                    res["hallazgos_administrativos"] = row_tot["adm"] or 0
                    res["cuantia_total"] = float(row_tot["cuan"] or 0.0)

                # Búsqueda específica
                condiciones = []
                params: List[Any] = []
                if ent_filtro:
                    condiciones.append("UPPER(nombre) LIKE ?")
                    params.append(f"%{ent_filtro}%")
                elif dep_filtro:
                    condiciones.append("UPPER(nombre) LIKE ?")
                    params.append(f"%{dep_filtro}%")
                elif not filtros.get("es_resumen_general"):
                    terminos = [w for w in pregunta_norm.split() if len(w) > 3 and w not in ["SOBRE", "DIME", "CUANTAS", "CUANTOS", "TIENE", "ESTA", "ESTE", "COMO", "CUAL", "CUALES"]]
                    if terminos:
                        subc = " OR ".join(["UPPER(nombre) LIKE ?" for _ in terminos])
                        condiciones.append(f"({subc})")
                        params.extend([f"%{t}%" for t in terminos])

                if condiciones:
                    where_sql = f"WHERE {' AND '.join(condiciones)}"
                    resumen = con.execute(
                        f"SELECT COUNT(*) AS sujetos, SUM(fiscales) AS fiscales, SUM(penales) AS penales, SUM(cuantia) AS cuantia "
                        f"FROM gold_consulta_contraloria {where_sql}", params
                    ).fetchone()
                    res["total_sujetos_filtro"] = resumen["sujetos"] or 0
                    res["hallazgos_fiscales_filtro"] = resumen["fiscales"] or 0
                    res["hallazgos_penales_filtro"] = resumen["penales"] or 0
                    res["cuantia_filtro"] = float(resumen["cuantia"] or 0.0)
                    filas = con.execute(
                        f"SELECT nombre, registros, administrativos, disciplinarios, fiscales, penales, cuantia, vigencia_desde, vigencia_hasta "
                        f"FROM gold_consulta_contraloria {where_sql} ORDER BY cuantia DESC LIMIT 10", params
                    ).fetchall()
                    res["coincidencias"] = [dict(r) for r in filas]

                # Top entidades con mayor cuantía económica de hallazgos
                top_cuan = con.execute(
                    "SELECT nombre, cuantia, fiscales, penales FROM gold_consulta_contraloria ORDER BY cuantia DESC LIMIT 6"
                ).fetchall()
                res["top_entidades_cuantia"] = [dict(r) for r in top_cuan]
            except Exception:
                pass
        else:
            # Fallback a CSV Gold
            df_cont = self._leer_gold_csv("dataset_contraloria.csv")
            if df_cont is not None:
                res["total_auditorias"] = len(df_cont)
                res["hallazgos_fiscales"] = int(pd.to_numeric(df_cont.get("hallazgos_fiscales", 0), errors="coerce").fillna(0).sum())
                res["hallazgos_penales"] = int(pd.to_numeric(df_cont.get("hallazgos_penales", 0), errors="coerce").fillna(0).sum())
                res["cuantia_total"] = float(pd.to_numeric(df_cont.get("cuantia", 0), errors="coerce").fillna(0).sum())

        return res

    def _consultar_secop(self, filtros: Dict[str, Any], con: Optional[sqlite3.Connection]) -> Dict[str, Any]:
        """Extrae muestra de contratación estatal en SECOP II."""
        res: Dict[str, Any] = {
            "nombre": "Contratación Pública (SECOP II)",
            "alcance": "Muestra de contratos adjudicados, proveedores y modalidades",
            "total_contratos": 0,
            "valor_total_adjudicado": 0.0,
            "coincidencias": [],
        }

        ent_filtro = filtros.get("entidad_buscada")
        pregunta_norm = filtros.get("pregunta_norm", "")

        if con:
            try:
                tot_row = con.execute("SELECT COUNT(*) as c FROM gold_consulta_contratos").fetchone()
                res["total_contratos"] = tot_row["c"] if tot_row else 0

                condiciones = []
                params: List[Any] = []
                if ent_filtro:
                    condiciones.append("(UPPER(entidad) LIKE ? OR UPPER(proveedor) LIKE ?)")
                    params.extend([f"%{ent_filtro}%", f"%{ent_filtro}%"])
                elif not filtros.get("es_resumen_general"):
                    terminos = [w for w in pregunta_norm.split() if len(w) > 3 and w not in ["SOBRE", "DIME", "CUANTAS", "CUANTOS", "TIENE", "ESTA", "ESTE", "COMO", "CUAL", "CUALES"]]
                    if terminos:
                        subc = " OR ".join(["UPPER(entidad) LIKE ? OR UPPER(proveedor) LIKE ?" for _ in terminos])
                        condiciones.append(f"({subc})")
                        for t in terminos:
                            params.extend([f"%{t}%", f"%{t}%"])

                if condiciones:
                    where_sql = f"WHERE {' AND '.join(condiciones)}"
                    total_filtro = con.execute(
                        f"SELECT COUNT(*) FROM gold_consulta_contratos {where_sql}", params
                    ).fetchone()[0]
                    res["total_contratos_filtro"] = total_filtro
                    filas = con.execute(
                        f"SELECT id_proceso, referencia, entidad, proveedor, modalidad, estado, valor_adjudicado, fecha_publicacion "
                        f"FROM gold_consulta_contratos {where_sql} LIMIT 5", params
                    ).fetchall()
                    res["coincidencias"] = [dict(r) for r in filas]
            except Exception:
                pass
        return res

    def calcular_indice_alerta(self, fisc: Dict[str, Any], proc: Dict[str, Any], cont: Dict[str, Any], filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula un nivel de atención / alerta interinstitucional basado en la concurrencia."""
        sanciones_cnt = proc.get("total_sanciones_filtro", len(proc.get("coincidencias", [])))
        fisc_hallazgos = cont.get("hallazgos_fiscales_filtro", cont.get("hallazgos_fiscales", 0))
        pen_hallazgos = cont.get("hallazgos_penales_filtro", cont.get("hallazgos_penales", 0))
        cuantia = cont.get("cuantia_filtro", cont.get("cuantia_total", 0.0))

        score = 0
        justificacion = []

        if sanciones_cnt > 0:
            score += min(sanciones_cnt * 3, 35)
            justificacion.append(f"{fmt_numero(sanciones_cnt)} sanción(es) disciplinaria(s) en Procuraduría")

        if fisc_hallazgos > 0:
            score += min(fisc_hallazgos * 5, 25)
            justificacion.append(f"{fmt_numero(fisc_hallazgos)} hallazgo(s) con presunta incidencia fiscal en Contraloría")

        if pen_hallazgos > 0:
            score += min(pen_hallazgos * 6, 25)
            justificacion.append(f"{fmt_numero(pen_hallazgos)} hallazgo(s) con presunto traslado penal a Fiscalía")

        if cuantia > 0:
            score += 15
            justificacion.append(f"Impacto económico auditado de {fmt_dinero(cuantia)}")

        if fisc.get("departamento_info"):
            dep_inf = fisc["departamento_info"]
            score += 10
            justificacion.append(f"{fmt_numero(dep_inf['total_procesos'])} procesos penales registrados en el departamento ({dep_inf['pct_activos']}% activos)")

        # Normalizar de 1 a 100
        score = min(max(score, 10), 100)

        if score >= 70:
            nivel = "ALTA"
            color = ROJO
            emoji = "🔴"
            mensaje = "Alta concurrencia de procesos penales, sanciones disciplinarias y/o hallazgos fiscales."
        elif score >= 40:
            nivel = "MODERADA"
            color = AMARILLO
            emoji = "🟡"
            mensaje = "Concurrencia intermedia entre entidades de control con atención requerida."
        else:
            nivel = "BAJA"
            color = VERDE
            emoji = "🟢"
            mensaje = "Bajo nivel de incidencia o información descriptiva general sin concentraciones críticas."

        return {
            "score": score,
            "nivel": nivel,
            "color": color,
            "emoji": emoji,
            "mensaje": mensaje,
            "justificacion": justificacion,
        }

    def generar_narrativa(
        self,
        filtros: Dict[str, Any],
        fisc: Dict[str, Any],
        proc: Dict[str, Any],
        cont: Dict[str, Any],
        secop: Dict[str, Any],
        alerta: Dict[str, Any],
    ) -> str:
        """Genera una explicación redactada en lenguaje claro y estructurado."""
        q_orig = filtros["pregunta_original"]
        partes = []

        # Encabezado
        if filtros.get("es_resumen_general"):
            partes.append(
                f"### 🌐 Radiografía Interinstitucional: Cruce de las 3 Entidades de Control\n\n"
                f"Al analizar la consulta **«{q_orig}»**, el Agente consolidó los registros del Data Warehouse unificando "
                f"los frentes de **Fiscalía**, **Procuraduría** y **Contraloría** (con el respaldo contractual de SECOP II):\n"
            )
        elif filtros.get("entidad_buscada"):
            ent = filtros["entidad_buscada"]
            partes.append(
                f"### 🏢 Análisis Focalizado: {ent} en las Entidades de Control\n\n"
                f"Para la entidad **«{ent}»**, se contrastaron simultáneamente las investigaciones penales, "
                f"los antecedentes disciplinarios y las auditorías de control fiscal:\n"
            )
        elif filtros.get("departamento"):
            dep = filtros["departamento"]
            partes.append(
                f"### 📍 Panorama Territorial: {dep} en las 3 Entidades de Control\n\n"
                f"Para el departamento de **«{dep}»**, se integró el comportamiento penal de la Fiscalía con las "
                f"sanciones disciplinarias registradas por la Procuraduría y el control fiscal de la Contraloría:\n"
            )
        else:
            partes.append(
                f"### 🔎 Respuesta Unificada del Agente de Control\n\n"
                f"A partir de su consulta **«{q_orig}»**, los datos integrados de las 3 entidades indican lo siguiente:\n"
            )

        # 1. Fiscalía
        if fisc.get("departamento_info"):
            di = fisc["departamento_info"]
            partes.append(
                f"1. **⚖️ Fiscalía General de la Nación:** En este territorio se contabilizan **{fmt_numero(di['total_procesos'])} procesos penales** "
                f"por delitos contra la administración pública. De ellos, el **{di['pct_activos']}%** ({fmt_numero(di['procesos_activos'])} procesos) "
                f"permanecen con trámite activo (principalmente en fase de Indagación).\n"
            )
        else:
            partes.append(
                f"1. **⚖️ Fiscalía General de la Nación:** La base consolidada registra **{fmt_numero(fisc['total_procesos'])} procesos penales** "
                f"por corrupción y delitos administrativos a nivel nacional, con un **{fisc['pct_activos']}% activos**. "
                f"Los delitos más recurrentes son *Peculado por Apropiación*, *Celebración Indebida de Contratos* y *Prevaricato*.\n"
            )

        # 2. Procuraduría
        sanc_filtro = proc.get("total_sanciones_filtro")
        if sanc_filtro is not None:
            partes.append(
                f"2. **🛡️ Procuraduría General de la Nación:** Se encontraron **{fmt_numero(sanc_filtro)} sanciones disciplinarias** "
                f"relacionadas directamente con su criterio de búsqueda. Las principales medidas comprenden destituciones, inhabilidades "
                f"y suspensiones a servidores públicos.\n"
            )
        else:
            partes.append(
                f"2. **🛡️ Procuraduría General de la Nación:** El registro disciplinario (SIRI) almacena **{fmt_numero(proc['total_sanciones'])} sanciones** "
                f"a servidores públicos en todo el país. La fuerza pública (Policía Nacional y Fuerzas Militares) y las administraciones locales "
                f"son las que concentran el mayor número de sanciones ejecutoriadas.\n"
            )

        # 3. Contraloría
        cuan_filtro = cont.get("cuantia_filtro")
        fisc_filtro = cont.get("hallazgos_fiscales_filtro")
        if cuan_filtro is not None:
            partes.append(
                f"3. **🏛️ Contraloría General de la República:** En las auditorías vinculadas se determinaron "
                f"**{fmt_numero(fisc_filtro or 0)} hallazgos fiscales** y **{fmt_numero(cont.get('hallazgos_penales_filtro', 0))} traslados penales**, "
                f"con una cuantía acumulada de presunto detrimento patrimonial estimada en **{fmt_dinero(cuan_filtro)}**.\n"
            )
        else:
            partes.append(
                f"3. **🏛️ Contraloría General de la República:** En las auditorías registradas al plan de vigilancia se han generado "
                f"**{fmt_numero(cont['hallazgos_fiscales'])} hallazgos fiscales** y **{fmt_numero(cont['hallazgos_penales'])} penales**, "
                f"alcanzando una cuantía vigilada total de **{fmt_dinero(cont['cuantia_total'])}**.\n"
            )

        # 4. SECOP II (Contratación)
        if secop.get("coincidencias"):
            partes.append(
                f"4. **📑 SECOP II:** Se identificaron **{len(secop['coincidencias'])} procesos de contratación pública** asociados, "
                f"evidenciando la actividad contractual de entidades y proveedores en las modalidades de licitación o contratación directa.\n"
            )

        # Conclusión y Recomendación
        partes.append(
            f"\n> **Alerta Interinstitucional:** {alerta['emoji']} Nivel **{alerta['nivel']}** (Índice: {alerta['score']}/100).\n"
            f"> *{alerta['mensaje']}*\n\n"
            f"*Nota metodológica:* Las cifras provienen de datos abiertos institucionales procesados en la capa Gold del Data Warehouse. "
            f"Tienen carácter estrictamente analítico y descriptivo, sin constituir juzgamiento jurídico individual."
        )

        return "".join(partes)

    @staticmethod
    def verificar_ollama(url: str = OLLAMA_URL_DEFAULT, timeout: float = 2.0) -> Tuple[bool, List[str]]:
        """Verifica si Ollama está en ejecución localmente y devuelve la lista de modelos disponibles."""
        import requests
        try:
            resp = requests.get(f"{url.rstrip('/')}/api/tags", timeout=timeout)
            if resp.status_code == 200:
                payload = resp.json()
                modelos = [m.get("name") for m in payload.get("models", []) if m.get("name")]
                return True, modelos
        except Exception:
            pass
        return False, []

    def generar_narrativa_ia(
        self,
        filtros: Dict[str, Any],
        fisc: Dict[str, Any],
        proc: Dict[str, Any],
        cont: Dict[str, Any],
        secop: Dict[str, Any],
        alerta: Dict[str, Any],
        modelo: str = "qwen2.5:1.5b",
        url_ollama: str = OLLAMA_URL_DEFAULT,
        timeout: int = 40,
    ) -> Tuple[str, bool]:
        """Genera una respuesta analítica inteligente usando el LLM local de Ollama (RAG)."""
        import requests

        q_orig = filtros["pregunta_original"]
        dep_inf = fisc.get("departamento_info") or {}
        tot_proc_fisc = dep_inf.get("total_procesos", fisc.get("total_procesos", 0))
        pct_act_fisc = dep_inf.get("pct_activos", fisc.get("pct_activos", 0))

        sanc_proc = _valor_consulta(proc, "total_sanciones_filtro", "total_sanciones")
        cargos_proc = [f"{c['cargo']} ({c['cantidad']})" for c in proc.get("cargos_frecuentes", [])[:4]]
        tipos_sanc = [f"{t['sanciones']} ({t['cantidad']})" for t in proc.get("tipos_sancion", [])[:4]]

        fisc_h = _valor_consulta(cont, "hallazgos_fiscales_filtro", "hallazgos_fiscales")
        pen_h = _valor_consulta(cont, "hallazgos_penales_filtro", "hallazgos_penales")
        cuan_h = _valor_consulta(cont, "cuantia_filtro", "cuantia_total")

        contratos_cnt = _valor_consulta(secop, "total_contratos_filtro", "total_contratos")

        datos_contexto = (
            f"DATOS VERIFICADOS DEL DATA WAREHOUSE PARA: \"{q_orig}\"\n"
            f"1. FISCALÍA GENERAL: {tot_proc_fisc} procesos penales registrados ({pct_act_fisc}% activos en indagación/juicio).\n"
            f"2. PROCURADURÍA GENERAL: {sanc_proc} sanciones disciplinarias SIRI ejecutoriadas. Tipos frecuentes: {', '.join(tipos_sanc) or 'Sin detalle disponible'}. Cargos: {', '.join(cargos_proc) or 'Sin detalle disponible'}.\n"
            f"3. CONTRALORÍA GENERAL: {fisc_h} hallazgos fiscales, {pen_h} traslados penales. Cuantía económica observada: {fmt_dinero(cuan_h)}.\n"
            f"4. SECOP II (Contratación pública): {contratos_cnt} procesos contractuales relacionados.\n"
            f"5. NIVEL DE ALERTA INTERINSTITUCIONAL: {alerta.get('nivel', 'MODERADA')} ({alerta.get('score', 0)}/100). {alerta.get('mensaje', '')}"
        )

        prompt_sistema = (
            "Eres un asistente de análisis descriptivo de datos públicos de Colombia. "
            "Responde la pregunta del usuario articulando la información disponible de Fiscalía, Procuraduría, Contraloría y SECOP II. "
            "Instrucciones obligatorias:\n"
            "- Usa únicamente cifras y hechos provistos en el contexto; no inventes datos ni relaciones entre registros.\n"
            "- Si una entidad no tiene datos específicos para el filtro, indícalo y no presentes el total nacional como si fuera del filtro.\n"
            "- No atribuyas responsabilidad ni emitas conclusiones jurídicas sobre personas o entidades.\n"
            "- Estructura tu respuesta en Markdown con subtítulos o viñetas claras.\n"
            "- Describe por separado los resultados de Fiscalía, Procuraduría, Contraloría y SECOP II; solo señala coincidencias cuando estén respaldadas por el contexto.\n"
            "- Cierra con una recomendación de verificación de datos, sin sugerir culpabilidad.\n"
            "- Redacta en español formal y conciso (entre 2 y 4 párrafos bien estructurados)."
        )

        try:
            resp = requests.post(
                f"{url_ollama.rstrip('/')}/api/chat",
                json={
                    "model": modelo,
                    "messages": [
                        {"role": "system", "content": prompt_sistema},
                        {"role": "user", "content": f"{datos_contexto}\n\nPregunta: {q_orig}\nGenera el análisis integrador:"},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 450,
                    },
                },
                timeout=timeout,
            )
            if resp.status_code == 200:
                payload = resp.json()
                contenido = payload.get("message", {}).get("content", "").strip()
                if contenido and not payload.get("error"):
                    dictamen = (
                        f"### 🤖 Análisis con IA Local (Ollama - {modelo})\n\n"
                        f"{contenido}\n\n"
                        f"> **Alerta Interinstitucional:** {alerta['emoji']} Nivel **{alerta['nivel']}** (Índice: {alerta['score']}/100).\n"
                        f"> *{alerta['mensaje']}*\n\n"
                        f"*Nota metodológica:* Síntesis analítica generada por el modelo local `{modelo}` a partir de registros consolidados en la capa Gold del Data Warehouse."
                    )
                    return dictamen, True
        except Exception:
            pass

        return self.generar_narrativa(filtros, fisc, proc, cont, secop, alerta), False

    def construir_graficas_plotly(
        self,
        filtros: Dict[str, Any],
        fisc: Dict[str, Any],
        proc: Dict[str, Any],
        cont: Dict[str, Any],
        secop: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Construye las especificaciones y figuras de Plotly para visualizaciones específicas."""
        import plotly.graph_objects as go

        graficas: Dict[str, Any] = {}

        # 1. Gráfica Comparativa Multidimensional de las 3 Entidades
        dep_inf = fisc.get("departamento_info") or {}
        val_fisc = dep_inf.get("total_procesos", fisc.get("total_procesos", 0))
        val_proc = _valor_consulta(proc, "total_sanciones_filtro", "total_sanciones")
        val_cont = _valor_consulta(cont, "hallazgos_fiscales_filtro", "hallazgos_fiscales")
        val_pen_cont = _valor_consulta(cont, "hallazgos_penales_filtro", "hallazgos_penales")

        fig_comp = go.Figure()
        categorias = ["Fiscalía (Procesos)", "Procuraduría (Sanciones)", "Contraloría (Hallazgos Fisc.)", "Contraloría (Traslados Pen.)"]
        valores = [val_fisc, val_proc, val_cont, val_pen_cont]
        colores = [AZUL, AMARILLO, ROJO, AZUL_OSC]

        fig_comp.add_trace(go.Bar(
            x=categorias,
            y=valores,
            marker_color=colores,
            text=[fmt_numero(v) for v in valores],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Total: %{text}<extra></extra>",
        ))
        fig_comp.update_layout(
            title="<b>Cruce Integral: Volumen de Registros por Entidad de Control</b>",
            paper_bgcolor="white",
            plot_bgcolor="white",
            height=340,
            margin=dict(l=20, r=20, t=50, b=20),
            font=dict(family="Segoe UI, Arial", size=13),
            yaxis=dict(showgrid=True, gridcolor="#EAECF0"),
        )
        graficas["comparativa_entidades"] = {
            "titulo": "Cruce General entre Entidades",
            "descripcion": "Comparativo del número de registros identificados en cada órgano de control.",
            "fig": fig_comp,
        }

        # 2. Gráfica Territorial (Departamentos: Fiscalía vs Procuraduría)
        top_deps_fisc = fisc.get("datos_grafica", {}).get("top_departamentos", [])
        if top_deps_fisc:
            nombres_dep = [d["departamento_hecho"] for d in top_deps_fisc[:8]]
            tot_proc_dep = [d["total_procesos"] for d in top_deps_fisc[:8]]
            act_proc_dep = [d["procesos_activos"] for d in top_deps_fisc[:8]]

            fig_dep = go.Figure()
            fig_dep.add_trace(go.Bar(
                name="Total Procesos",
                x=nombres_dep,
                y=tot_proc_dep,
                marker_color=AZUL,
                text=[fmt_numero(v) for v in tot_proc_dep],
                textposition="auto",
            ))
            fig_dep.add_trace(go.Bar(
                name="Procesos Activos",
                x=nombres_dep,
                y=act_proc_dep,
                marker_color=AMARILLO,
                text=[fmt_numero(v) for v in act_proc_dep],
                textposition="auto",
            ))
            fig_dep.update_layout(
                barmode="group",
                title="<b>Distribución Territorial: Procesos Penales por Departamento</b>",
                paper_bgcolor="white",
                plot_bgcolor="white",
                height=350,
                margin=dict(l=20, r=20, t=50, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(showgrid=True, gridcolor="#EAECF0"),
            )
            graficas["departamentos"] = {
                "titulo": "Mapa Territorial de Procesos",
                "descripcion": "Comparación de procesos totales frente a trámites activos en los principales departamentos.",
                "fig": fig_dep,
            }

        # 3. Gráfica de Tipología de Hallazgos en Contraloría
        fisc_h = _valor_consulta(cont, "hallazgos_fiscales_filtro", "hallazgos_fiscales")
        pen_h = _valor_consulta(cont, "hallazgos_penales_filtro", "hallazgos_penales")
        disc_h = cont.get("hallazgos_disciplinarios", 0)
        adm_h = cont.get("hallazgos_administrativos", 0)

        fig_hallazgos = go.Figure(go.Pie(
            labels=["Fiscales", "Penales", "Disciplinarios", "Administrativos"],
            values=[max(fisc_h, 1), max(pen_h, 1), max(disc_h, 1), max(adm_h, 1)],
            hole=0.45,
            marker_colors=[ROJO, AZUL_OSC, AMARILLO, GRIS],
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Cantidad: %{value}<br>%{percent}<extra></extra>",
        ))
        fig_hallazgos.update_layout(
            title="<b>Distribución de Hallazgos de Auditoría (Contraloría)</b>",
            paper_bgcolor="white",
            height=340,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        graficas["hallazgos_contraloria"] = {
            "titulo": "Tipología de Hallazgos (Contraloría)",
            "descripcion": "Proporción de hallazgos fiscales, penales, disciplinarios y administrativos.",
            "fig": fig_hallazgos,
        }

        # 4. Gráfica de Tipos de Sanción en Procuraduría
        tipos_sanc = proc.get("tipos_sancion", [])
        if tipos_sanc:
            nombres_sanc = [t["sanciones"] for t in tipos_sanc]
            cant_sanc = [t["cantidad"] for t in tipos_sanc]

            fig_sanc = go.Figure(go.Bar(
                x=cant_sanc,
                y=nombres_sanc,
                orientation="h",
                marker_color=AZUL,
                text=[fmt_numero(v) for v in cant_sanc],
                textposition="outside",
            ))
            fig_sanc.update_layout(
                title="<b>Sanciones Disciplinarias Más Frecuentes (Procuraduría)</b>",
                paper_bgcolor="white",
                plot_bgcolor="white",
                height=320,
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(showgrid=True, gridcolor="#EAECF0"),
                yaxis=dict(autorange="reversed"),
            )
            graficas["tipos_sancion"] = {
                "titulo": "Tipos de Sanción (Procuraduría)",
                "descripcion": "Frecuencia de inhabilidades, destituciones, suspensiones y multas impuestas.",
                "fig": fig_sanc,
            }

        # 5. Gráfica de Cuantías Económicas / Detrimento Patrimonial
        top_cuan = cont.get("top_entidades_cuantia", [])
        if top_cuan:
            nombres_cuan = [c["nombre"][:24] + "..." if len(c["nombre"]) > 24 else c["nombre"] for c in top_cuan]
            montos = [c["cuantia"] / 1e6 for c in top_cuan]  # En millones

            fig_cuan = go.Figure(go.Bar(
                x=montos,
                y=nombres_cuan,
                orientation="h",
                marker_color=ROJO,
                text=[f"${fmt_numero(m, 1)} M" for m in montos],
                textposition="outside",
            ))
            fig_cuan.update_layout(
                title="<b>Mayor Cuantía de Hallazgos Fiscales (Millones COP)</b>",
                paper_bgcolor="white",
                plot_bgcolor="white",
                height=340,
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis=dict(showgrid=True, gridcolor="#EAECF0", title="Millones de Pesos COP"),
                yaxis=dict(autorange="reversed"),
            )
            graficas["cuantia_economica"] = {
                "titulo": "Impacto Económico Fiscal (Contraloría)",
                "descripcion": "Entidades con las mayores cuantías estimadas de detrimento patrimonial.",
                "fig": fig_cuan,
            }

        return graficas

    def consultar(
        self,
        pregunta: str,
        usar_ia: bool = True,
        modelo_ia: Optional[str] = None,
        timeout_ia: int = 40,
    ) -> Dict[str, Any]:
        """Método principal: ejecuta el análisis unificado y genera datos + visualizaciones.

        Si usar_ia es True y Ollama está activo localmente, utiliza un LLM local
        (ej. qwen2.5:1.5b o llama3.1:latest) para redactar un dictamen inteligente.
        Si Ollama no está disponible o falla, utiliza automáticamente la narrativa estructurada.
        """
        filtros = self.detectar_filtros(pregunta)
        con = self._conectar()

        try:
            fisc = self._consultar_fiscalia(filtros, con)
            proc = self._consultar_procuraduria(filtros, con)
            cont = self._consultar_contraloria(filtros, con)
            secop = self._consultar_secop(filtros, con)
        finally:
            if con:
                con.close()

        alerta = self.calcular_indice_alerta(fisc, proc, cont, filtros)

        # Verificación y generación con Ollama si está activo
        ollama_disponible, modelos_disponibles = self.verificar_ollama()
        modo_ia_aplicado = False
        modelo_elegido = None

        if usar_ia and ollama_disponible:
            if modelo_ia and modelo_ia in modelos_disponibles:
                modelo_elegido = modelo_ia
            else:
                for pref in MODELOS_OLLAMA_PREFERIDOS:
                    if pref in modelos_disponibles:
                        modelo_elegido = pref
                        break
                if not modelo_elegido and modelos_disponibles:
                    modelo_elegido = modelos_disponibles[0]

            if modelo_elegido:
                narrativa, modo_ia_aplicado = self.generar_narrativa_ia(
                    filtros, fisc, proc, cont, secop, alerta, modelo=modelo_elegido, timeout=timeout_ia
                )

        if not modo_ia_aplicado:
            narrativa = self.generar_narrativa(filtros, fisc, proc, cont, secop, alerta)

        graficas = self.construir_graficas_plotly(filtros, fisc, proc, cont, secop)

        # KPIs clave para tarjetas del frontend
        dep_info = fisc.get("departamento_info") or {}
        kpis = [
            {
                "entidad": "Fiscalía",
                "etiqueta": "Procesos Penales",
                "valor": fmt_numero(dep_info.get("total_procesos", fisc["total_procesos"])),
                "subtexto": f"{dep_info.get('pct_activos', fisc['pct_activos'])}% con trámite activo",
                "icono": "⚖️",
            },
            {
                "entidad": "Procuraduría",
                "etiqueta": "Sanciones Disciplinarias",
                "valor": fmt_numero(_valor_consulta(proc, "total_sanciones_filtro", "total_sanciones")),
                "subtexto": "Servidores sancionados (SIRI)",
                "icono": "🛡️",
            },
            {
                "entidad": "Contraloría",
                "etiqueta": "Hallazgos de Auditoría",
                "valor": fmt_numero(_valor_consulta(cont, "hallazgos_fiscales_filtro", "hallazgos_fiscales") + _valor_consulta(cont, "hallazgos_penales_filtro", "hallazgos_penales")),
                "subtexto": f"Cuantía: {fmt_dinero(_valor_consulta(cont, 'cuantia_filtro', 'cuantia_total'))}",
                "icono": "🏛️",
            },
            {
                "entidad": "SECOP II",
                "etiqueta": "Contratación Pública",
                "valor": fmt_numero(_valor_consulta(secop, "total_contratos_filtro", "total_contratos")),
                "subtexto": "Muestra de contratos analizados",
                "icono": "📑",
            },
        ]

        return {
            "pregunta": pregunta,
            "filtros": filtros,
            "alerta": alerta,
            "narrativa": narrativa,
            "kpis": kpis,
            "fiscalia": fisc,
            "procuraduria": proc,
            "contraloria": cont,
            "secop": secop,
            "graficas": graficas,
            "modo_ia": modo_ia_aplicado,
            "modelo_usado": modelo_elegido if modo_ia_aplicado else None,
            "ollama_disponible": ollama_disponible,
            "modelos_disponibles": modelos_disponibles,
        }

    @staticmethod
    def obtener_sugerencias() -> List[Dict[str, str]]:
        """Preguntas sugeridas de alto impacto analítico para el usuario."""
        return [
            {
                "titulo": "Cruce General de las 3 Entidades",
                "pregunta": "Muéstrame el panorama general y cruce de datos entre Fiscalía, Procuraduría y Contraloría",
                "icono": "🌐",
            },
            {
                "titulo": "Policía Nacional en las 3 Entidades",
                "pregunta": "¿Qué información y sanciones existen sobre la Policía Nacional en las tres entidades?",
                "icono": "👮",
            },
            {
                "titulo": "Antioquia: Delitos y Sanciones",
                "pregunta": "¿Cuál es la situación de procesos penales y sanciones disciplinarias en Antioquia?",
                "icono": "📍",
            },
            {
                "titulo": "Bogotá D.C.: Radiografía Penal y Fiscal",
                "pregunta": "Radiografía de procesos penales de Fiscalía y hallazgos en Bogotá",
                "icono": "🏙️",
            },
            {
                "titulo": "Delitos de Contratación y Hallazgos",
                "pregunta": "¿Cómo se relacionan los delitos de contratación pública con los hallazgos de Contraloría?",
                "icono": "📑",
            },
            {
                "titulo": "Alcaldías y Control Disciplinario",
                "pregunta": "¿Cuáles son las sanciones y hallazgos en Alcaldías municipales?",
                "icono": "🏛️",
            },
        ]
