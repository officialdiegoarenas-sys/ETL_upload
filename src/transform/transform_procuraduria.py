import os
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil

def transformar_datos_procuraduria(ruta_entrada: str, ruta_salida: str):
    print("Iniciando transformación de datos (Capa Silver - Procuraduría)...")
    
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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Transformando datos Procuraduria;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")

    try:
        df = pd.read_csv(ruta_entrada)
        print(f"Registros cargados desde Bronze: {len(df)}")
        
        # Eliminamos los duplicados basados en el número de SIRI y las sanciones
        if 'numero_siri' in df.columns and 'sanciones' in df.columns:
            df = df.drop_duplicates(subset=['numero_siri', 'sanciones'])
        elif 'numero_siri' in df.columns:
            df = df.drop_duplicates(subset=['numero_siri'])
        
        # Normalizamos los textos a mayúsculas en campos clave de texto y rellenamos los nulos eistentes
        columnas_texto = ['cargo', 'entidad_sancionado', 'lugar_hechos_departamento', 'lugar_hechos_municipio', 'sanciones', 'autoridad', 'tipo_inhabilidad']
        for col in columnas_texto:
            if col in df.columns:
                df[col] = df[col].fillna("NO REGISTRADO")
                df[col] = df[col].astype(str).str.upper().str.strip()
                df[col] = df[col].replace(['NAN', 'NONE', 'NAT'], 'NO REGISTRADO')
        
        # Limpiamos y rellenamos los valores nulos en duraciones numéricas con 0
        columnas_num = ['duracion_anos', 'duracion_mes', 'duracion_dias']
        for col in columnas_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Aseguramos que exista la carpeta silver
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        
        # Guardamos el archivo limpio en capa de Silver
        df.to_csv(ruta_salida, index=False, encoding='utf-8')
        print(f"¡Transformación exitosa! Datos limpios almacenados en {ruta_salida}")
        print(f"Registros resultantes en Silver: {len(df)}")
        return df
        
    except Exception as e:
        print(f"Error en la transformación de la Capa Silver: {e}")
        return None

if __name__ == "__main__":
    input_path = "data/bronze/procuraduria_raw.csv"
    output_path = "data/silver/procuraduria_clean.csv"
    transformar_datos_procuraduria(input_path, output_path)
