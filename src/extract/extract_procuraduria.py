import os
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil

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
        df = pd.read_csv(url_csv)
        
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
    # Endpoint de exportación CSV directo con límite de registros para mantener el flujo ágil
    url_csv = "https://www.datos.gov.co/resource/iaeu-rcn6.csv?$limit=1000"
    output_path = "data/bronze/procuraduria_raw.csv"
    
    extraer_datos_procuraduria(url_csv, output_path)
    

