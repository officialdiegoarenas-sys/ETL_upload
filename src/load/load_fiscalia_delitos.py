import os
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil


def generar_gold_fiscalia(ruta_procesos: str, ruta_procesados: str, carpeta_gold: str):
    print("Iniciando procesamiento de la Capa Gold (Fiscalía delitos contra la administración pública)...")

    try:
        nombre_equipo = os.getlogin()
    except:
        nombre_equipo = "Desconocido"
    ruta_ejecucion = os.path.abspath(__file__)
    ram_uso = psutil.virtual_memory().percent
    try:
        temp_uso = f"{psutil.sensors_temperatures()['coretemp'][0].current}°C"
    except Exception:
        temp_uso = "N/A"

    os.makedirs('logs', exist_ok=True)
    with open('logs/logs.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Integrando datos Fiscalia delitos;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")

    try:
        procesos = pd.read_csv(ruta_procesos, dtype={'cod_dane_hecho': str, 'articulo': str})
        procesados = pd.read_csv(ruta_procesados, dtype={'cod_dane_hecho': str, 'articulo': str})
        print(f"Registros cargados desde Silver: {len(procesos)} procesos, {len(procesados)} procesados")
        os.makedirs(carpeta_gold, exist_ok=True)

        # Procesos por año y capitulo
        por_año = procesos.groupby(['año_creacion', 'capitulo_delito'])['proceso_anonimizado'].nunique().reset_index(name='total_procesos')
        por_año.to_csv(f"{carpeta_gold}/fiscalia_procesos_año_capitulo_gold.csv", index=False, encoding='utf-8')

        # Procesos por departamento
        procesos['activo'] = (procesos['estado'] == 'Activo').astype(int)
        por_depto = procesos.drop_duplicates('proceso_anonimizado').groupby('departamento_hecho').agg(
            total_procesos=('proceso_anonimizado', 'count'),
            procesos_activos=('activo', 'sum')
        ).reset_index()
        por_depto['pct_activos'] = (por_depto['procesos_activos'] / por_depto['total_procesos'] * 100).round(2)
        por_depto = por_depto.sort_values('total_procesos', ascending=False)
        por_depto.to_csv(f"{carpeta_gold}/fiscalia_procesos_departamento_gold.csv", index=False, encoding='utf-8')

        # Delitos mas frecuentes
        top_delitos = procesos.groupby(['articulo', 'delito', 'capitulo_delito']).size().reset_index(name='total')
        top_delitos = top_delitos.sort_values('total', ascending=False)
        top_delitos.to_csv(f"{carpeta_gold}/fiscalia_top_delitos_gold.csv", index=False, encoding='utf-8')

        # Etapa y estado
        por_etapa = procesos.groupby(['etapa', 'estado']).size().reset_index(name='total')
        por_etapa['porcentaje'] = (por_etapa['total'] / por_etapa['total'].sum() * 100).round(2)
        por_etapa.to_csv(f"{carpeta_gold}/fiscalia_procesos_etapa_gold.csv", index=False, encoding='utf-8')

        # Sentencias por capitulo
        procesados['condenado'] = (procesados['tipo_sentencia'] == 'Condenado').astype(int)
        procesados['absuelto'] = (procesados['tipo_sentencia'] == 'Absuelto').astype(int)
        sentencias = procesados.groupby('capitulo_delito').agg(
            total_procesados=('id_procesado_anonimizado', 'count'),
            condenados=('condenado', 'sum'),
            absueltos=('absuelto', 'sum')
        ).reset_index()
        sentencias['pct_condena'] = (sentencias['condenados'] / sentencias['total_procesados'] * 100).round(2)
        sentencias = sentencias.sort_values('total_procesados', ascending=False)
        sentencias.to_csv(f"{carpeta_gold}/fiscalia_procesados_sentencias_gold.csv", index=False, encoding='utf-8')

        # Perfil de los condenados
        perfil = procesados[procesados['condenado'] == 1].groupby(['sexo', 'grupo_etario']).size().reset_index(name='total_condenados')
        perfil.to_csv(f"{carpeta_gold}/fiscalia_perfil_condenados_gold.csv", index=False, encoding='utf-8')

        print(f"¡Capa Gold generada con éxito en {carpeta_gold}!")
        print("\n--- Vista previa: procesos por departamento ---")
        print(por_depto.head(5))
        print("\n--- Vista previa: sentencias por capitulo ---")
        print(sentencias.head(5))

        return por_depto

    except Exception as e:
        print(f"Error procesando la Capa Gold de Fiscalía: {e}")
        return None


if __name__ == "__main__":
    generar_gold_fiscalia("data/silver/fiscalia_procesos_clean.csv", "data/silver/fiscalia_procesados_clean.csv", "data/gold")
