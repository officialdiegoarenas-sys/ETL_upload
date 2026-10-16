import os
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil


def registrar_log(etapa):
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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};{etapa};{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")


def quitar_tildes(serie):
    return serie.str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('ascii').str.upper().str.strip()


def limpiar_comun(df, col_depto, col_mpio, col_dane, col_año_hecho, col_mes_hecho):
    # Sin Información a nulo
    df = df.replace("Sin Información", pd.NA)

    # Departamento y municipio sin tildes
    df[col_depto] = quitar_tildes(df[col_depto])
    df[col_mpio] = quitar_tildes(df[col_mpio])
    df[col_dane] = df[col_dane].str.zfill(5)

    # Años y meses a numero
    for col in [col_año_hecho, col_mes_hecho]:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    # Articulo del codigo penal
    df['articulo'] = df['delito'].str.extract(r'Art\.? ?(\d+\w?)', expand=False).str.upper()

    df['capitulo_delito'] = df['capitulo_delito'].fillna("NO REGISTRADO")
    return df


def transformar_procesos(ruta_entrada: str, ruta_salida: str):
    print("Iniciando transformación de datos (Capa Silver - Fiscalía procesos)...")
    registrar_log("Transformando datos Fiscalia procesos")

    try:
        df = pd.read_csv(ruta_entrada, dtype=str)
        print(f"Registros cargados desde Bronze: {len(df)}")

        # Columnas que no se usan
        df = df.drop(columns=['pais_hecho', 'dir_hecho_rural_urbana', 'trimestre_hecho', 'trimestre_creacion',
                              'procedimiento_abreviado', 'fecha_corte_datos'])

        # Llave proceso + delito
        df = df.drop_duplicates(subset=['proceso_anonimizado', 'deli_id'])

        df = limpiar_comun(df, 'departamento_hecho', 'municipio_hecho', 'cod_dane_hecho', 'a_o_hecho', 'mes_hecho')
        df = df.rename(columns={'a_o_hecho': 'año_hecho', 'a_o_creacion_proceso': 'año_creacion',
                                'mes_creacion_proceso': 'mes_creacion'})
        df['año_creacion'] = df['año_creacion'].astype(int)
        df['mes_creacion'] = df['mes_creacion'].astype(int)
        df['fecha_creacion'] = pd.to_datetime(dict(year=df['año_creacion'], month=df['mes_creacion'], day=1))

        # Hechos con fecha posterior a la creacion
        df.loc[df['año_hecho'] > df['año_creacion'], ['año_hecho', 'mes_hecho']] = pd.NA

        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        df.to_csv(ruta_salida, index=False, encoding='utf-8')
        print(f"¡Transformación exitosa! Datos limpios almacenados en {ruta_salida}")
        print(f"Registros resultantes en Silver: {len(df)}")
        return df

    except Exception as e:
        print(f"Error en la transformación de la Capa Silver (procesos): {e}")
        return None


def transformar_procesados(ruta_entrada: str, ruta_salida: str):
    print("Iniciando transformación de datos (Capa Silver - Fiscalía procesados)...")
    registrar_log("Transformando datos Fiscalia procesados")

    try:
        df = pd.read_csv(ruta_entrada, dtype=str)
        print(f"Registros cargados desde Bronze: {len(df)}")

        # Columnas que no se usan
        df = df.drop(columns=['aplica_lgbti', 'identidad_genero_orient_sexual', 'pais_nacimiento', 'etnia',
                              'comunidad_indigena', 'religioso', 'periodista', 'profesor', 'ddhh', 'discapacidad',
                              'trimestre_hecho_origen', 'trimestre_creacion_origen', 'procedimiento_abreviado',
                              'grado_delito', 'fecha_actualizacion_datos'])

        df = df.drop_duplicates()

        df = limpiar_comun(df, 'departamento_hecho_origen', 'municipio_hecho_origen', 'cod_dane_hecho_origen',
                           'a_o_hecho_origen', 'mes_hecho_origen')
        df = df.rename(columns={'departamento_hecho_origen': 'departamento_hecho', 'municipio_hecho_origen': 'municipio_hecho',
                                'cod_dane_hecho_origen': 'cod_dane_hecho', 'a_o_hecho_origen': 'año_hecho',
                                'mes_hecho_origen': 'mes_hecho', 'a_o_creacion_origen': 'año_creacion',
                                'mes_creacion_origen': 'mes_creacion'})
        df['año_creacion'] = df['año_creacion'].astype(int)
        df['mes_creacion'] = df['mes_creacion'].astype(int)
        df.loc[df['año_hecho'] > df['año_creacion'], ['año_hecho', 'mes_hecho']] = pd.NA

        for col in ['sexo', 'grupo_etario', 'nivel_educativo']:
            df[col] = df[col].fillna("NO REGISTRADO")

        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        df.to_csv(ruta_salida, index=False, encoding='utf-8')
        print(f"¡Transformación exitosa! Datos limpios almacenados en {ruta_salida}")
        print(f"Registros resultantes en Silver: {len(df)}")
        return df

    except Exception as e:
        print(f"Error en la transformación de la Capa Silver (procesados): {e}")
        return None


if __name__ == "__main__":
    transformar_procesos("data/bronze/fiscalia_procesos_raw.csv", "data/silver/fiscalia_procesos_clean.csv")
    transformar_procesados("data/bronze/fiscalia_procesados_raw.csv", "data/silver/fiscalia_procesados_clean.csv")
