import os
import pandas as pd

def procesar_capa_gold(ruta_entrada: str, ruta_salida: str):
    print("Iniciando procesamiento de la Capa Gold (Procuraduría)...")
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
        
        # Aseguramos que exista la carpeta gold
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
