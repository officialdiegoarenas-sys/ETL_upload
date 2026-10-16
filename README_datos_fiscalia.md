# Pipeline de datos de Fiscalía y SECOP

El proceso añade dos fuentes independientes a la arquitectura medallón:

| Dataset | API | Bronze | Silver | Gold |
|---|---|---|---|---|
| Fiscalía | `piva-db2c` | `data/bronze/datos_fiscalia_raw.json` | `data/silver/datos_fiscalia_silver.csv` | `data/gold/datos_fiscalia_gold.csv` |
| SECOP | `p6dx-8zbt` | `data/bronze/datos_secop_raw.json` | `data/silver/datos_secop_silver.csv` | `data/gold/datos_secop_gold.csv` |

Bronze conserva en JSON hasta 1.000 filas de cada API en una sola página, para
mantener rápida la extracción y acotado el tiempo de procesamiento.
Silver quita metadatos técnicos de Socrata, estandariza nombres de columnas,
limpia espacios, elimina filas vacías y duplicados exactos, convierte fechas y
campos numéricos verificables y registra conversiones inválidas. No reemplaza
categorías legítimas como «Sin Información» o «No Adjudicado».

Se genera un reporte por fuente en `data/quality/`. Gold agrupa Fiscalía por
delito, estado, departamento y año del hecho, contando registros y procesos
anonimizados únicos. Gold de SECOP agrupa por entidad, modalidad y estado, con
cantidad de procesos y agregados del precio base.

El proceso se ejecuta junto con las demás etapas desde `python main.py`. Para
ejecutarlo de forma independiente desde la carpeta `ETL_upload`, puede usarse:

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from pipeline.datos_fiscalia import ejecutar_pipeline_datos_fiscalia; ejecutar_pipeline_datos_fiscalia()"
```

Si una API falla, el error se propaga y el pipeline no informa éxito ni crea una
capa posterior incompleta.
