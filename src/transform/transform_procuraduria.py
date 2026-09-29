import os
import pandas as pd

def transformar_datos_procuraduria(ruta_entrada: str, ruta_salida: str):
    print("Iniciando transformación de datos (Capa Silver - Procuraduría)...")
    try:
        df = pd.read_csv(ruta_entrada)
        print(f"Registros cargados desde Bronze: {len(df)}")
        
        # Eliminamos los duplicados basados en el número de SIRI y las sanciones
        if 'numero_siri' in df.columns and 'sanciones' in df.columns:
            df = df.drop_duplicates(subset=['numero_siri', 'sanciones'])
        elif 'numero_siri' in df.columns:
            df = df.drop_duplicates(subset=['numero_siri'])
        
        # Normalizamos los textos a mayúsculas en campos clave de texto y rellenamos nulos
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
        
        # Guardamos el archivo limpio en capa Silver
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
