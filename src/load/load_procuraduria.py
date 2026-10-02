import os
import pandas as pd
import datetime #Capturar la fecha y hora de ejecución
import psutil

def procesar_capa_gold(ruta_entrada: str, ruta_salida: str):
    print("Iniciando procesamiento de la Capa Gold (Procuraduría)...")
    
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
        log_file.write(f"{datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')};Integrando datos Procuraduria;{nombre_equipo};{ruta_ejecucion};RAM:{ram_uso}%;Temp:{temp_uso}\n")
    
    try:
        df = pd.read_csv(ruta_entrada)
        print(f"Registros cargados desde Silver: {len(df)}")
        
        # Validamos si existe la columna de entidad sancionada para hacer la agregación
        if 'entidad_sancionado' in df.columns:
            # Agrupar por entidad y contar el total de procesos/sanciones
            df_gold = df.groupby('entidad_sancionado').size().reset_index(name='total_sanciones')
            
            # Ordenamos de mayor a menor
            df_gold = df_gold.sort_values(by='total_sanciones', ascending=False)
        else:
            # Fallback si cambia el nombre de la columna
            df_gold = df.head(0)
        
        # Aseguramos que exista la carpeta de gold
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        
        # Guardamos el resumen analítico en capa Gold
        df_gold.to_csv(ruta_salida, index=False, encoding='utf-8')
        print(f"¡Capa Gold generada con éxito en {ruta_salida}!")
        
        print("\n--- Vista previa del resumen analítico (Top Entidades Sancionadas) ---")
        print(df_gold.head(5))
        
        return df_gold
        
    except Exception as e:
        print(f"Error procesando la Capa Gold: {e}")
        return None

if __name__ == "__main__":
    input_path = "data/silver/procuraduria_clean.csv"
    output_path = "data/gold/resumen_procuraduria_gold.csv"
    procesar_capa_gold(input_path, output_path)
