import os
import pandas as pd
import pytest

# Se saltan si no se ha corrido el pipeline
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SILVER_PROCESOS = os.path.join(RAIZ, 'data', 'silver', 'fiscalia_procesos_clean.csv')
SILVER_PROCESADOS = os.path.join(RAIZ, 'data', 'silver', 'fiscalia_procesados_clean.csv')
GOLD = os.path.join(RAIZ, 'data', 'gold')


def cargar(ruta, **kwargs):
    if not os.path.exists(ruta):
        pytest.skip(f"No existe {ruta}, primero correr main.py")
    return pd.read_csv(ruta, dtype={'cod_dane_hecho': str, 'articulo': str}, **kwargs)


@pytest.fixture(scope="module")
def procesos():
    return cargar(SILVER_PROCESOS)


@pytest.fixture(scope="module")
def procesados():
    return cargar(SILVER_PROCESADOS)


def test_procesos_sin_duplicados(procesos):
    assert not procesos.duplicated(['proceso_anonimizado', 'deli_id']).any()


def test_procesados_sin_duplicados(procesados):
    assert not procesados.duplicated().any()


def test_un_solo_titulo(procesos, procesados):
    assert procesos['titulo_delito'].unique().tolist() == ['Delitos Contra La Administracion Publica']
    assert procesados['titulo_delito'].unique().tolist() == ['Delitos Contra La Administracion Publica']


def test_sin_texto_sin_informacion(procesos):
    assert not (procesos == 'Sin Información').any().any()


def test_columnas_clave_completas(procesos, procesados):
    for col in ['proceso_anonimizado', 'deli_id', 'delito', 'capitulo_delito', 'estado', 'año_creacion']:
        assert procesos[col].notna().all(), col
    for col in ['id_procesado_anonimizado', 'proceso_anonimizado', 'tipo_sentencia', 'sexo']:
        assert procesados[col].notna().all(), col


def test_rangos_de_fechas(procesos):
    assert procesos['año_creacion'].between(2010, 2030).all()
    assert procesos['mes_creacion'].between(1, 12).all()
    assert procesos['mes_hecho'].dropna().between(1, 12).all()
    assert (procesos['año_hecho'].dropna() <= procesos.loc[procesos['año_hecho'].notna(), 'año_creacion']).all()


def test_codigo_dane(procesos):
    assert procesos['cod_dane_hecho'].dropna().str.fullmatch(r'\d{5}').all()


def test_departamentos_sin_tildes(procesos):
    deptos = procesos['departamento_hecho'].dropna()
    assert (deptos == deptos.str.upper()).all()
    assert not deptos.str.contains('[ÁÉÍÓÚÑáéíóúñ]').any()


def test_valores_validos(procesos, procesados):
    assert set(procesos['estado']) <= {'Activo', 'Inactivo'}
    assert set(procesados['tipo_sentencia']) <= {'Condenado', 'Absuelto', 'Sancionado', 'No Aplica'}


def test_gold_porcentajes():
    depto = cargar(os.path.join(GOLD, 'fiscalia_procesos_departamento_gold.csv'))
    sentencias = cargar(os.path.join(GOLD, 'fiscalia_procesados_sentencias_gold.csv'))
    etapas = cargar(os.path.join(GOLD, 'fiscalia_procesos_etapa_gold.csv'))

    assert depto['pct_activos'].between(0, 100).all()
    assert sentencias['pct_condena'].between(0, 100).all()
    assert abs(etapas['porcentaje'].sum() - 100) < 0.1


def test_gold_cuadra_con_silver(procesos):
    depto = cargar(os.path.join(GOLD, 'fiscalia_procesos_departamento_gold.csv'))
    sin_depto = procesos.drop_duplicates('proceso_anonimizado')['departamento_hecho'].isna().sum()
    assert depto['total_procesos'].sum() + sin_depto == procesos['proceso_anonimizado'].nunique()
