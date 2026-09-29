import os
import pandas as pd

def generar_capa_gold(ruta_entrada: str, ruta_salida: str):
    print("Iniciando procesamiento de la Capa Gold (Agregaciones y Analítica)...")
    
    if not os.path.exists(ruta_entrada):
        print(f"Error: No se encontró el archivo en la capa Silver: {ruta_entrada}")
        return None
        
    # Cargar los datos limpios de la capa Silver
    df = pd.read_csv(ruta_entrada)
    print(f"Registros cargados desde Silver: {len(df)}")
    
    # Identificar columnas disponibles para la agregación
    col_entidad = 'nombre_entidad' if 'nombre_entidad' in df.columns else df.columns[0]
    
    # Generando un resumen analítico agrupado por entidad (Total de procesos / contratos)
    if 'id_del_proceso' in df.columns:
        resumen = df.groupby(col_entidad).agg(
            total_procesos=('id_del_proceso', 'count')
        ).reset_index()
    else:
        resumen = df.groupby(col_entidad).size().reset_index(name='total_procesos')
        
    # Ordenamos de mayor a menor participación
    resumen = resumen.sort_values(by='total_procesos', ascending=False)
    
    # Aseguramos que exista la carpeta gold
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    
    # Guardamos el resultado analítico en la capa Gold
    resumen.to_csv(ruta_salida, index=False, encoding='utf-8')
    
    print(f"¡Capa Gold generada con éxito en {ruta_salida}!")
    print("\n--- Vista previa del resumen analítico (Top Entidades) ---")
    print(resumen.head(5))
    
    return resumen

if __name__ == "__main__":
    input_path = "data/silver/contratos_fiscalia_clean.csv"
    output_path = "data/gold/resumen_contratos_gold.csv"
    generar_capa_gold(input_path, output_path)