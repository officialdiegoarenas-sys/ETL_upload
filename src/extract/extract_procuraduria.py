import io
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
import requests
import datetime #Capturar la fecha y hora de ejecución
import psutil

TAMANO_PAGINA = 25000   # filas por solicitud (el portal limita el tamaño de cada respuesta)
MAX_PAGINAS = 40         # tope de seguridad: 1.000.000 de filas


def descargar_paginado(url_csv: str, tamano_pagina: int = TAMANO_PAGINA, max_paginas: int = MAX_PAGINAS,
                       timeout: int = 120) -> pd.DataFrame:
    """Descarga TODO el dataset de datos.gov.co (Socrata) página por página.

    Se ignora cualquier $limit/$offset/$order de la URL y se ordena por :id (orden estable),
    para que ninguna fila se repita ni se pierda entre páginas.
    """
    partes = urlsplit(url_csv)
    otros = [(k, v) for k, v in parse_qsl(partes.query) if k not in ("$limit", "$offset", "$order")]
    paginas = []
    for n in range(max_paginas):
        consulta = urlencode(otros + [("$limit", tamano_pagina), ("$offset", n * tamano_pagina), ("$order", ":id")])
        resp = requests.get(urlunsplit(partes._replace(query=consulta)), timeout=timeout)
        resp.raise_for_status()
        pagina = pd.read_csv(io.StringIO(resp.text), dtype=str)
        if pagina.empty:
            break
        paginas.append(pagina)
        print(f"  página {n + 1}: {len(pagina)} filas")
        if len(pagina) < tamano_pagina:
            break
    return pd.concat(paginas, ignore_index=True) if paginas else pd.DataFrame()


def extraer_datos_procuraduria(url_csv: str, ruta_salida: str):
    print("Iniciando extracción de datos de antecedentes y sanciones (SIRI - Procuraduría)...")
    
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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Extrayendo datos Procuraduria;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")

    try:
        # Descargamos y leemos de forma directa del archivo CSV exportado por la plataforma
        # URL del portal -> descarga paginada de toda la base; ruta local -> lectura directa
        df = descargar_paginado(url_csv) if url_csv.startswith("http") else pd.read_csv(url_csv)
        
        if not df.empty:
            # Aseguramos que exista la carpeta bronze
            os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
            
            # Guardamos en el formato CSV limpio en la capa Bronze
            df.to_csv(ruta_salida, index=False, encoding='utf-8')
            print(f"¡Datos extraídos y guardados con éxito en {ruta_salida}!")
            print(f"Total de registros obtenidos: {len(df)}")
            return df
        else:
            print("El dataset devuelto está vacío.")
            return None
            
    except Exception as e:
        print(f"Ocurrió un error inesperado durante la extracción: {e}")
        return None

if __name__ == "__main__":
    # Endpoint de exportación CSV; se descarga toda la base de forma paginada
    url_csv = "https://www.datos.gov.co/resource/iaeu-rcn6.csv"
    output_path = "data/bronze/procuraduria_raw.csv"
    
    extraer_datos_procuraduria(url_csv, output_path)
    

