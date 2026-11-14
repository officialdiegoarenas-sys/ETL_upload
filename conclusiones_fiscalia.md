# Conclusiones descriptivas de la API de Fiscalía

## Alcance de la consulta

La consulta del 16 de octubre de 2026 obtuvo la primera página de 1.000 filas
del dataset público de procesos de la Fiscalía. No se especificó un orden ni se
descargó el dataset completo; por tanto, estos resultados describen únicamente
esa página y no deben extrapolarse a todos los procesos registrados.

En las 1.000 filas se encontraron 240 valores distintos de
`proceso_anonimizado` y 110 valores distintos de `delito`. Varias filas pueden
corresponder a un mismo proceso, así que los conteos por delito, estado,
departamento y etapa son conteos de filas, no necesariamente de procesos
únicos.

## Hallazgos de la página consultada

- **Estado:** 595 filas (59,5 %) aparecen como `Inactivo` y 405 (40,5 %) como
  `Activo`.
- **Etapa:** 687 filas (68,7 %) están en `Indagación`; 122 (12,2 %) en
  `Ejecución De Penas`, 101 (10,1 %) en `Juicio` y 90 (9,0 %) en
  `Investigación`.
- **Departamento del hecho:** Bogotá, D. C. registra 436 filas (43,6 %) y
  Antioquia 186 (18,6 %). Son concentraciones de esta página, no tasas
  territoriales ni comparaciones ajustadas por población.
- **Delitos:** el valor más frecuente es una modalidad agravada de estafa,
  con 130 filas; le siguen estafa (82) y estafa de menor cuantía (58).
  `Contrato Sin Cumplimiento De Requisitos Legales` aparece en 36 filas y
  `Peculado Por Apropiación` en 27. Las filas pueden compartir proceso y no
  representan por sí solas decisiones judiciales.
- **Categoría del procesado:** 879 filas (87,9 %) tienen la categoría
  `Indiciado`; 91 (9,1 %) `Sentenciado`, 17 `Imputado` y 13 `Acusado`. La
  categoría debe leerse tal como está publicada y no como una declaración
  independiente de responsabilidad.
- Los años del hecho de esta página van de 2005 a 2010. Esto confirma que la
  primera página no basta para describir la evolución reciente de la base.

## Soluciones y siguientes pasos

1. **No limitar el análisis al primer bloque de 1.000 filas.** Para conclusiones
   generales, ejecutar la extracción paginada hasta el final del dataset y
   registrar la fecha de corte. La muestra actual no es aleatoria ni
   representativa.
2. **Contar procesos únicos además de filas.** Agrupar por
   `proceso_anonimizado` antes de comparar delitos, etapas o territorios, para
   evitar que procesos con más intervinientes o delitos pesen más en los
   resultados.
3. **Usar categorías como filtros de revisión, no como acusaciones.** Las filas
   de delitos relacionados con contratación pública pueden orientar una
   revisión documental posterior; el dataset anonimizado no identifica por sí
   solo responsables ni acredita hechos.
4. **Actualizar el análisis por fecha de corte y validar las categorías.**
   Comparar páginas completas y revisar los valores `Sin Información` antes
   de presentar proporciones como indicadores definitivos.

## Fuente

- [Dataset de procesos de la Fiscalía en datos.gov.co](https://www.datos.gov.co/resource/piva-db2c.json)
- Consulta reproducible de la primera página:
  `https://www.datos.gov.co/resource/piva-db2c.json?$limit=1000`

Los datos de esta API usan identificadores anonimizados. No se deben intentar
reidentificar personas ni inferir culpabilidad a partir de estos conteos.
