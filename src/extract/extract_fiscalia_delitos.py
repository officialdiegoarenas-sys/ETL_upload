import os
import io
import time
import requests
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil

# Filtro del titulo de delitos contra la administracion publica (en la fuente viene escrito de dos formas)
FILTRO = "titulo_delito in('Delitos Contra La Administracion De Publica','Delitos Contra La Administracion Publica')"


def descargar_pagina(url, params, reintentos=5):
    for _ in range(reintentos):
        try:
            r = requests.get(url, params=params, timeout=300)
            if r.status_code == 200:
                return r.text
            print(f"Status {r.status_code}, reintentando...")
        except Exception as e:
            print(f"Error de conexion ({e}), reintentando...")
        time.sleep(5)
    return None


def extraer_datos_fiscalia(dataset_id: str, ruta_salida: str, tamano_pagina=50000):
    print(f"Iniciando extracción de datos Fiscalía (dataset {dataset_id})...")

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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Extrayendo datos Fiscalia delitos {dataset_id};{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")

    url = f"https://www.datos.gov.co/resource/{dataset_id}.csv"
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)

    # Se descarga por paginas y se va guardando en el csv para no llenar la memoria
    # Se pagina con el :id interno de la API porque con $offset se vuelve muy lento
    ultimo_id = None
    total = 0
    while True:
        where = FILTRO if ultimo_id is None else f"{FILTRO} AND :id > '{ultimo_id}'"
        params = {"$select": ":*,*", "$where": where, "$order": ":id", "$limit": tamano_pagina}
        texto = descargar_pagina(url, params)
        if texto is None:
            print("No se pudo descargar la pagina, se cancela la extraccion.")
            return None

        df = pd.read_csv(io.StringIO(texto), dtype=str)
        if df.empty:
            break

        ultimo_id = df[':id'].iloc[-1]
        df = df.drop(columns=[':id', ':created_at', ':updated_at', ':version'])
        df.to_csv(ruta_salida, mode='w' if total == 0 else 'a', header=(total == 0), index=False, encoding='utf-8')
        total += len(df)
        print(f"Pagina descargada, registros acumulados: {total}")

        if len(df) < tamano_pagina:
            break

    if total == 0:
        print("El dataset devuelto está vacío.")
        return None

    print(f"¡Datos extraídos y guardados con éxito en {ruta_salida}!")
    print(f"Total de registros obtenidos: {total}")
    return total


if __name__ == "__main__":
    extraer_datos_fiscalia("dbdv-iihs", "data/bronze/fiscalia_procesos_raw.csv")
    extraer_datos_fiscalia("piva-db2c", "data/bronze/fiscalia_procesados_raw.csv")
