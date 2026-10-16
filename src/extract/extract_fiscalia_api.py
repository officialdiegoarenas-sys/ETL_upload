import os
import requests # para hacer la petición a la API   
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil # Para capturar el uso de RAM y temperatura del equipo

def extraer_datos_api(url: str, ruta_salida: str): #aca definimos la función que extrae los datos de la API y los guarda en un archivo CSV
    print("Iniciando extracción de datos desde la API pública...")
    
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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Extrayendo datos API Fiscalia;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)

        # Asegurar que exista la carpeta bronze
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        df.to_csv(ruta_salida, index=False, encoding='utf-8')
        print(f"¡Datos extraídos y guardados con éxito en {ruta_salida}!")
        print(f"Total de registros obtenidos: {len(df)}")
        return df
    else:
        print(f"Error en la petición: Status Code {response.status_code}")
        return None

if __name__ == "__main__":
    url_api = "https://www.datos.gov.co/resource/p6dx-8zbt.json?$limit=100"
    output_path = "data/bronze/contratos_fiscalia_raw.csv"
    extraer_datos_api(url_api, output_path)