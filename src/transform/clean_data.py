import os
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil

def transformar_datos(ruta_entrada: str, ruta_salida: str):
    print("Iniciando transformación de datos (Capa Silver)...")
    
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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Transformando datos Fiscalia;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")

    if not os.path.exists(ruta_entrada):
        print(f"Error: No se encontró el archivo crudo en {ruta_entrada}")
        return None
    
    # Leemos el archivo de la capa Bronze
    df = pd.read_csv(ruta_entrada)
    print(f"Registros cargados desde Bronze: {len(df)}")
    
    # Aplicamos limpieza de los duplicados y filas vacías
    df = df.dropna(how='all')
    df = df.drop_duplicates()
    
    # Estandarizamos nombres de columnas (minúsculas y sin espacios)
    df.columns = [col.strip().lower().replace(" ", "_").replace(".", "") for col in df.columns]
    
    # Tratamiento de nulos en columnas clave si están presentes
    columnas_clave = [col for col in ['nombre_entidad', 'descripcion_del_proceso', 'estado_del_proceso', 'cuantia_proceso'] if col in df.columns]
    for col in columnas_clave:
        if df[col].dtype == 'object':
            df[col] = df[col].fillna("NO REGISTRADO")
            
    # Aseguramos que exista la carpeta silver
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    
    # Guardamos en formato CSV limpio en la capa Silver
    df.to_csv(ruta_salida, index=False, encoding='utf-8')
    
    print(f"¡Transformación exitosa! Datos limpios almacenados en {ruta_salida}")
    print(f"Registros resultantes en Silver: {len(df)}")
    return df

if __name__ == "__main__":
    input_path = "data/bronze/contratos_fiscalia_raw.csv"
    output_path = "data/silver/contratos_fiscalia_clean.csv"
    transformar_datos(input_path, output_path)
