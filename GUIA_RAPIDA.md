# Guía rápida del dashboard

# 1. Qué se hizo
Un dashboard en Streamlit que lee los datos del ETL a través de nuestra API (FastAPI). Tiene reportes con gráficas, favoritos, calendario y una pantalla Consultar para buscar por cédula, número de proceso o nombre de una contraloría.

# 2. Dónde está el código

| Qué | Dónde |
|---|---|
| Dashboard (todo) | carpeta `App/` |
| Archivo que se ejecuta | `App/app.py` |
| Pantallas (inicio, consultar, calendario...) | `App/paginas.py` |
| Gráficas y textos de cada reporte (Fiscalía, SECOP, Procuraduría, Contraloría) | `App/reportes.py` |
| Calendario y festivos | `App/calendario.py` |
| Lectura de datos / llamada a la API | `App/datos.py` |
| Login (correo con "fiscalia") | `App/acceso.py` |
| Favoritos y recordatorios | `App/almacen.py` |
| Colores y estilos | `App/estilos.py` |
| Búsqueda por cédula, proceso o contraloría (base de datos) | `src/data_warehouse/consulta.py` |
| Endpoints nuevos de la API (`/consulta`, `/gold`) | `api/main.py` |
| Descarga completa de la Procuraduría | `src/extract/extract_procuraduria.py` |
| Contraloría por API (dataset `wasc-xi4h`) | `src/extract/extract_contraloria.py` |
| Pruebas del dashboard y la consulta | `tests/test_app.py`, `tests/test_consulta.py` |
| Configuración del dashboard | `config/config.yaml` (sección `app`) |

# 3. Cómo ejecutarlo (terminal de VS Code, dentro de la carpeta del proyecto)

Primera vez (instalar):

```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Cada vez que quieran abrir el dashboard (levanta la API y abre el dashboard):

```
.\iniciar_dashboard.bat
```

Se abre en http://localhost:8501. Para apagarlo: `Ctrl + C` en la terminal y cerrar la ventana de la API.

**Ingreso:** cualquier correo que contenga `fiscalia` (ejemplo: `diegofiscalia@gmail.com`) y cualquier contraseña.

Para volver a descargar los datos (tarda y descarga cientos de MB): `.\.venv\Scripts\python.exe main.py`

# 4. Datos para probar la consulta (pantalla "Consultar")

| Escribir | Resultado |
|---|---|
| `12995790` | Cédula con 14 sanciones (Alcaldía de San Juan de Pasto) |
| `43381138` | Cédula con 12 registros (Alcaldía de Argelia) |
| `73086958` | Cédula con 12 registros (Juzgado Promiscuo Municipal) |
| `1192801117` | Cédula con 1 sanción (INPEC) |
| `1193037426` | Cédula con 1 sanción (INPEC) |
| `JO0052023` | Proceso: Alcaldía de Girardot |
| `MAM-9561-24` | Proceso: Distrito Especial de Ciencia, Tecnología e Innovación |
| `NRCD2006008` | Proceso: Superintendencia Nacional de Salud |
| `2023-0272` | Proceso: Banco Agrario |
| `CO1.REQ.6299226` | Contrato (SECOP II) adjudicado: concurso de méritos de la Superintendencia de Notariado y Registro, con NIT del proveedor |
| `901848511` | El mismo contrato, buscado por el NIT |
| `CO1.REQ.8470190` | Proceso adjudicado, NIT 900004916 |
| `CO1.REQ.6690779` | Proceso publicado, sin proveedor todavía (CIAC S.A.) |

SECOP es una muestra de 100 procesos: estos ejemplos cambian si se vuelve a correr `main.py`.
| `Contraloría de Medellín` | Contraloría: 2 resultados |
| `Contraloría General de la República` | Contraloría: 3 resultados |
| `Santa Marta` | Contraloría: 2 resultados |
| `Pereira` | Contraloría: 1 resultado |
| `99999999` | Sin resultados (muestra el aviso) |

# 5. Importante
- La consulta solo funciona con la API encendida. Si sale "No se pudo conectar con el servicio de datos", la API está apagada.
- Se puede consultar la Procuraduría (toda su base), SECOP II (una muestra) y la Contraloría (por nombre de la entidad auditada; no trae personas). La Fiscalía no, porque sus datos abiertos están anonimizados.
- Que no aparezca un resultado no significa que la persona no tenga procesos.

# 6. Pruebas

```
.\.venv\Scripts\python.exe -m pytest tests -q
```
