import os
import sys
import pandas as pd
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from transform.clean_data import transformar_datos
from transform.transform_procuraduria import transformar_datos_procuraduria
from transform.transform_fiscalia_delitos import transformar_procesos, transformar_procesados
from load.load_database import generar_capa_gold
from load.load_procuraduria import procesar_capa_gold
from load.load_fiscalia_delitos import generar_gold_fiscalia


@pytest.fixture(autouse=True)
def carpeta_temporal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def proceso(**cambios):
    fila = {
        'proceso_anonimizado': 'P1', 'proceso_conexado': 'No', 'proceso_con_conexidad': 'No', 'es_ruptura': 'No',
        'estado': 'Activo', 'etapa': 'Indagación', 'ley': 'Ley 906', 'tipo_noticia': 'Denuncia',
        'procedimiento_abreviado': 'No', 'pais_hecho': 'Colombia', 'departamento_hecho': 'Bolívar',
        'municipio_hecho': 'Cartagena', 'cod_dane_hecho': '13001', 'dir_hecho_rural_urbana': 'Sin Información',
        'seccional': 'Dirección Seccional De Bolívar', 'a_o_hecho': '2019', 'mes_hecho': '03',
        'trimestre_hecho': 'Primer Trimestre', 'a_o_creacion_proceso': '2020', 'mes_creacion_proceso': '7',
        'trimestre_creacion': 'Tercer Trimestre', 'tipo_delito': 'Reparto', 'deli_id': '474',
        'delito': 'Peculado Por Apropiacion Art. 397 C.P.', 'titulo_delito': 'Delitos Contra La Administracion De Publica',
        'capitulo_delito': 'Del Peculado', 'grado_delito': 'Ninguno', 'delito_querellable': 'No',
        'fecha_corte_datos': '30/09/2026',
    }
    fila.update(cambios)
    return fila


def procesado(**cambios):
    fila = {
        'id_procesado_anonimizado': 'X1', 'proceso_anonimizado': 'P1', 'vinculacion_interviniente': 'VINCULACION_ORIGEN',
        'deli_id': '489', 'delito': 'Cohecho Por Dar U Ofrecer Art. 407 C.P.', 'titulo_delito': 'Delitos Contra La Administracion Publica',
        'capitulo_delito': 'Del Cohecho', 'grado_delito': 'Ninguno', 'proceso_conexado': 'No', 'proceso_con_conexidad': 'No',
        'es_ruptura': 'No', 'estado': 'Inactivo', 'etapa': 'Juicio', 'tipo_noticia': 'Denuncia', 'procedimiento_abreviado': 'No',
        'seccional': 'Dirección Seccional De Bogotá', 'departamento_hecho_origen': 'Bogotá, D. C.',
        'municipio_hecho_origen': 'Bogotá, D.C.', 'cod_dane_hecho_origen': '11001', 'a_o_hecho_origen': '2015',
        'mes_hecho_origen': '7', 'trimestre_hecho_origen': 'Tercer Trimestre', 'a_o_creacion_origen': '2015',
        'mes_creacion_origen': '9', 'trimestre_creacion_origen': 'Tercer Trimestre', 'sexo': 'Hombre', 'aplica_lgbti': 'No',
        'identidad_genero_orient_sexual': 'Sin Información', 'grupo_etario': 'Sin Información', 'pais_nacimiento': 'Colombia',
        'nivel_educativo': 'Universitario', 'etnia': 'Sin Información', 'comunidad_indigena': 'Sin Información',
        'religioso': 'No', 'periodista': 'No', 'profesor': 'No', 'ddhh': 'No', 'discapacidad': 'Sin Información',
        'categoria_procesado': 'Sentenciado', 'tipo_sentencia': 'Condenado', 'fecha_actualizacion_datos': '30/09/2026',
    }
    fila.update(cambios)
    return fila


def test_secop_limpieza():
    pd.DataFrame({
        'Nombre Entidad': ['A', 'A', None, None],
        'Estado del Proceso': ['Abierto', 'Abierto', None, None],
    }).to_csv("bronze.csv", index=False)

    df = transformar_datos("bronze.csv", "silver/secop.csv")

    assert list(df.columns) == ['nombre_entidad', 'estado_del_proceso']
    assert len(df) == 1


def test_secop_archivo_inexistente():
    assert transformar_datos("no_existe.csv", "silver/secop.csv") is None


def test_procuraduria_limpieza():
    pd.DataFrame({
        'numero_siri': [1, 1, 2],
        'sanciones': ['multa', 'multa', 'destitucion'],
        'cargo': [' alcalde ', ' alcalde ', None],
        'duracion_anos': ['2', '2', None],
    }).to_csv("bronze.csv", index=False)

    df = transformar_datos_procuraduria("bronze.csv", "silver/proc.csv")

    assert len(df) == 2
    assert df['cargo'].tolist() == ['ALCALDE', 'NO REGISTRADO']
    assert df['duracion_anos'].tolist() == [2, 0]


def test_fiscalia_procesos():
    filas = [
        proceso(),
        proceso(),
        proceso(deli_id='497', delito='Abuso De Autoridad Por Acto Arbitrario O Injusto Art. 416'),
        proceso(proceso_anonimizado='P2', deli_id='999', delito='Delitos Contra La Administracion De Publica',
                capitulo_delito='Sin Información', mes_hecho='Sin Información', departamento_hecho='Boyaca'),
    ]
    pd.DataFrame(filas).to_csv("bronze.csv", index=False)

    df = transformar_procesos("bronze.csv", "silver/procesos.csv")

    assert len(df) == 3
    assert df['titulo_delito'].nunique() == 1
    assert 'BOLIVAR' in df['departamento_hecho'].values
    assert df['articulo'].tolist()[:2] == ['397', '416']
    assert pd.isna(df['articulo'].iloc[2])
    assert df['capitulo_delito'].iloc[2] == 'NO REGISTRADO'
    assert df['mes_creacion'].iloc[0] == 7
    assert 'pais_hecho' not in df.columns


def test_fiscalia_procesados():
    pd.DataFrame([procesado(), procesado(), procesado(id_procesado_anonimizado='X2', mes_hecho_origen='07')]).to_csv("bronze.csv", index=False)

    df = transformar_procesados("bronze.csv", "silver/procesados.csv")

    assert len(df) == 2
    assert df['mes_hecho'].tolist() == [7, 7]
    assert df['grupo_etario'].iloc[0] == 'NO REGISTRADO'
    assert 'etnia' not in df.columns
    assert df['departamento_hecho'].iloc[0] == 'BOGOTA, D. C.'


def test_gold_secop_y_procuraduria():
    pd.DataFrame({'nombre_entidad': ['A', 'A', 'B'], 'id_del_proceso': [1, 2, 3]}).to_csv("secop.csv", index=False)
    pd.DataFrame({'entidad_sancionado': ['X', 'Y', 'Y']}).to_csv("proc.csv", index=False)

    secop = generar_capa_gold("secop.csv", "gold/secop.csv")
    proc = procesar_capa_gold("proc.csv", "gold/proc.csv")

    assert secop.iloc[0].tolist() == ['A', 2]
    assert proc.iloc[0].tolist() == ['Y', 2]


def test_gold_fiscalia():
    pd.DataFrame([
        proceso(),
        proceso(proceso_anonimizado='P2', estado='Inactivo'),
        proceso(proceso_anonimizado='P3', departamento_hecho='Antioquia', municipio_hecho='Medellín', cod_dane_hecho='05001'),
    ]).to_csv("bronze_procesos.csv", index=False)
    pd.DataFrame([
        procesado(),
        procesado(id_procesado_anonimizado='X2', tipo_sentencia='Absuelto'),
        procesado(id_procesado_anonimizado='X3', tipo_sentencia='No Aplica'),
        procesado(id_procesado_anonimizado='X4', tipo_sentencia='No Aplica'),
    ]).to_csv("bronze_procesados.csv", index=False)
    transformar_procesos("bronze_procesos.csv", "silver/procesos.csv")
    transformar_procesados("bronze_procesados.csv", "silver/procesados.csv")

    depto = generar_gold_fiscalia("silver/procesos.csv", "silver/procesados.csv", "gold")
    sentencias = pd.read_csv("gold/fiscalia_procesados_sentencias_gold.csv")

    bolivar = depto[depto['departamento_hecho'] == 'BOLIVAR'].iloc[0]
    assert bolivar['total_procesos'] == 2
    assert bolivar['pct_activos'] == 50.0
    assert sentencias.iloc[0]['pct_condena'] == 25.0
    assert len(os.listdir("gold")) == 6
