import os
import requests
import pandas as pd

def extraer_datos_api(url: str, ruta_salida: str):
    print("Iniciando extracción de datos desde la API pública...")
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