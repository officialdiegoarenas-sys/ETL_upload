# Proyecto ETL: Integración de Datos de Entidades de Control y la Fiscalía General de la Nación

- Materia: ETL (Extracción, Transformación y Carga)  
- Semestre: Semestre 5  
- Estudiantes: Diego Fernando Arenas Lasso, Miguel Angel Herrera Santanilla, Nayda Liseth Sierra Jaramillo, Kevin Ospina Gamboa, Santiago Navia Soto  
 

---------------------------------------------------------------------

# 1. Descripción del Problema y Justificación

En los procesos de investigación por delitos contra la administración pública en Colombia, uno de los mayores desafíos a los que se enfrentan los investigadores de la Fiscalía General de la Nación y las entidades de control es la dispersión de la información. Los datos sobre contratación pública, procesos y entidades se encuentran en múltiples plataformas aisladas (como portales de datos abiertos y SECOP), lo que dificulta hacer cruces rápidos y auditorías eficientes.

Este proyecto propone la construcción de un pipeline ETL automatizado y modular que centralice, limpie y transforme datos clave de contratación y entidades públicas. De este modo, se facilita la labor analítica para detectar anomalías, consolidar volúmenes de contratación por entidad y agilizar la toma de decisiones investigativas. "Si es posible tambien se integrara una automatizacion para realizar un refresh cada 24 o 48 horas, esta automatizacion se realizara si el tiempo del proyecto es suficiente para llegar a este punto".

---------------------------------------------------------------------

# 2. Arquitectura del Proyecto (Arquitectura Medallón)

Para mantener un orden riguroso y garantizar la gobernanza y calidad de los datos, implementamos la **Arquitectura Medallón** recomendada en clase, dividiendo el almacenamiento en tres capas principales dentro de la carpeta `data/`:

- Capa Bronze (Datos Crudos): Almacena la información tal cual se extrae de la API pública de datos abiertos, sin modificaciones, preservando el estado original (`.csv`).
- Capa Silver (Datos Limpios y Estructurados): Contiene los scripts que eliminan registros vacíos o duplicados, estandarizan los nombres de las columnas a minúsculas sin espacios y tratan valores nulos en campos clave.
- Capa Gold (Datos Analíticos / Negocio): Agrupa y procesa la información limpia para generar indicadores y resúmenes analíticos (por ejemplo, el consolidado de procesos por cada entidad pública) listos para la toma de decisiones.

---------------------------------------------------------------------

# 3. Estructura del Repositorio

El proyecto está organizado de forma modular para separar claramente cada etapa del proceso de ETL y facilitar las pruebas:


Avance proyecto 2 corte/
│
├── config/
│   └── config.yaml             # Archivo centralizado de rutas y parámetros
│
├── data/
│   ├── bronze/                 # Datos en bruto extraídos de la API
│   ├── silver/                 # Datos limpios, tipados y sin duplicados
│   └── gold/                   # Datos agregados y modelos analíticos (KPIs)
│
├── logs/                       # Registros de ejecución del sistema
├── notebooks/                  # Cuadernos para análisis exploratorio (EDA)
│   ├── analisis_exploratorio.ipynb  # EDA del módulo de la Fiscalía
│   └── analisis_procuraduria.ipynb  # EDA del módulo de la Procuraduría
├── src/                        # Código fuente modular del pipeline
│   ├── __init__.py
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── extract_fiscalia_api.py  # Script de extracción desde la API
│   │   └── extract_procuraduria.py  # Script de extracción de sanciones (SIRI)
│   ├── transform/
│   │   ├── __init__.py
│   │   ├── clean_data.py            # Script de limpieza y estandarización (Silver)
│   │   └── transform_procuraduria.py # Transformación módulo Procuraduría
│   └── load/
│       ├── __init__.py
│       ├── load_database.py         # Script de agregaciones y analítica (Gold)
│       └── load_procuraduria.py     # KPIs y agregaciones módulo Procuraduría
│
├── tests/                      # Pruebas unitarias del pipeline
│   ├── test_extract.py
│   ├── test_transform.py
│   └── test_quality.py
│
├── .env                        # Variables de entorno confidenciales
├── .gitignore                  # Archivos excluidos del control de versiones
├── main.py                     # Script orquestador principal del ETL
├── README.md                   # Documentación principal del proyecto
└── requirements.txt            # Dependencias y librerías del proyecto

---------------------------------------------------------------------
# ¿Qué es y cómo actúa la carpeta `logs/`?

La carpeta `logs/` funciona como la caja negra de auditoría del proyecto. Su comportamiento es el siguiente:

- ¿Qué significa?: Es el espacio destinado para almacenar de forma persistente el historial técnico de todo lo que ocurre cada vez que ejecutamos el sistema.

- ¿Cómo actúa?:** Gracias al módulo de `logging` integrado en el orquestador principal (`main.py`), cada vez que se lanza el pipeline se crea o actualiza automáticamente un archivo de texto llamado `pipeline.log`. En este archivo se registra con fecha, hora exacta y nivel de severidad (INFO o ERROR) el momento exacto en el que arranca cada capa (Bronze, Silver y Gold), el total de registros procesados y si se presentó algún fallo crítico, permitiendo rastrear el comportamiento del programa sin depender únicamente de la pantalla de la terminal.
---------------------------------------------------------------------
# Tecnologías y Librerías Utilizadas 1.1

- Python (Versión 3.13): Lenguaje principal de programación para el desarrollo del pipeline.
- Pandas & NumPy: Manipulación, limpieza, transformación y agregación de los datasets.
- Requests: Consumo de solicitudes HTTP a las APIs de datos abiertos.
- Matplotlib & Seaborn: Visualización de datos y generación de gráficos para el Análisis Exploratorio (EDA).
- Arquitectura Modular y POO: Estructura basada en scripts desacoplados controlados por un orquestador central (main.py).

# Tecnologías y Librerías Utilizadas 1.2

Para poner en marcha el proyecto de manera local en Visual Studio Code, sigue estos pasos desde la terminal de PowerShell:

# 1. Clonar o abrir la carpeta del proyecto
Abre la terminal integrada en la ruta raíz del proyecto.

# 2. Crear y activar el entorno virtual
Es importante aislar las dependencias de Python ejecutando: 

python -m venv venv
.\venv\Scripts\Activate

# 3. Instalar las dependencias
pip install -r requirements.txt

# 4. Ejecutar el Pipeline ETL completo
Para correr todo el proceso de punta a punta (Extracción en Bronze, Transformación en Silver y Analítica en Gold) con un solo comando, ejecuta el orquestador principal:

python main.py


