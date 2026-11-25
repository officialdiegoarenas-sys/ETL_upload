# Conclusiones descriptivas de la API de SECOP II

# Alcance de la consulta

Las cifras se consultaron directamente en la API pública de SECOP II el 16 de
octubre de 2026. Las consultas de conteo y agrupación operan sobre las filas
que cumplen sus filtros; una fila no equivale necesariamente a un proceso
único. Los datos y agregados de la API pueden cambiar con el tiempo.

# Hallazgos

- Volumen de la base: la API reportó 9.339.466 filas y 8.891.225 valores
  distintos de `id_del_proceso`. La diferencia de 448.241 filas indica que
  algunos identificadores aparecen en más de una fila; no debe tratarse como
  un conteo de procesos duplicados sin revisar el contenido de cada registro.
- Publicaciones desde el 1 de enero de 2025: la consulta agrupada por
  `estado_del_procedimiento` sumó 3.457.561 filas. Los estados más frecuentes
  fueron `Seleccionado` (1.941.852), `Publicado` (1.296.188) y `Evaluación`
  (181.437). `Cancelado` registró 30.316 filas. Son estados publicados por la
  API, no prueba por sí mismos de adjudicación, ejecución o irregularidad.
- Modalidad desde 2025: `Contratación régimen especial` tuvo 1.600.185
  filas y `Contratación directa` 1.460.762. Juntas representan alrededor del
  88,5 % de las filas devueltas por la consulta filtrada por fecha. Su
  frecuencia orienta la segmentación del análisis, pero no indica por sí sola
  riesgo ni incumplimiento.
- Valor base: para las filas publicadas desde 2025, la suma del campo
  `precio_base` devuelta por la API fue 29.290.676.840.684.695 y el promedio
  8.471.485.200,31 por fila. Es el agregado del campo reportado, no el valor
  efectivamente adjudicado o pagado. Por su magnitud y porque hay varias filas
  por identificador, debe validarse antes de usarlo como indicador financiero.
- Revisión de una página: entre las primeras 1.000 filas sin orden
  solicitado, 980 tenían un `id_del_proceso` distinto, 28 tenían
  `precio_base` igual a cero y el máximo observado fue 73.962.028.000. Esta
  página sirve solo para revisar calidad de datos; no es una muestra
  representativa del total.





# Fuente

- [Dataset de procesos de contratación de SECOP II en datos.gov.co](https://www.datos.gov.co/resource/p6dx-8zbt.json)
- [Conteo total de filas e identificadores de proceso](https://www.datos.gov.co/resource/p6dx-8zbt.json?$select=count%28*%29%20as%20total%2Ccount%28distinct%20id_del_proceso%29%20as%20procesos&$limit=1)
- Consultas descriptivas desde 2025:
  - Estados:
    `https://www.datos.gov.co/resource/p6dx-8zbt.json?$select=estado_del_procedimiento,count(*)%20as%20registros&$where=fecha_de_publicacion_del%20%3E%3D%20%272025-01-01T00%3A00%3A00%27&$group=estado_del_procedimiento&$order=registros%20DESC&$limit=20`
  - Modalidades:
    `https://www.datos.gov.co/resource/p6dx-8zbt.json?$select=modalidad_de_contratacion,count(*)%20as%20registros,sum(precio_base)%20as%20valor_base&$where=fecha_de_publicacion_del%20%3E%3D%20%272025-01-01T00%3A00%3A00%27&$group=modalidad_de_contratacion&$order=registros%20DESC&$limit=10`
  - Suma y promedio de `precio_base`:
    `https://www.datos.gov.co/resource/p6dx-8zbt.json?$select=sum(precio_base)%20as%20valor_base,avg(precio_base)%20as%20promedio&$where=fecha_de_publicacion_del%20%3E%3D%20%272025-01-01T00%3A00%3A00%27`
