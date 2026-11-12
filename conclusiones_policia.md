# Conclusiones del Análisis de Datos (Policía Nacional - DIJIN) - Proyecto Entidades de Control

## 1. Resumen Ejecutivo y Separación del Fenómeno Operativo

A partir de la extracción en vivo desde la API oficial de **Datos Abiertos (`datos.gov.co`, dataset `3jdh-nmwu` - Reporte Capturas Policía Nacional)**, se aislaron las conductas pertenecientes al **Título XV del Código Penal (Delitos contra la Administración Pública, Artículos 397 al 434)**, consolidando **70.685 registros depurados** equivalentes a **70.685 capturas operativas** entre 2010 y 2026.

Al igual que ocurrió en el módulo de la Procuraduría (SIRI), el primer gran hallazgo analítico consiste en **separar la operatividad de calle de los delitos de corrupción y contratación pública**:

- **Delitos contra los Servidores Públicos (Arts. 429 y 430 - Violencia y obstrucción):** Representan **56.340 capturas (79.7%)**. Son procedimientos policivos en flagrancia por agresiones a uniformados o funcionarios.
- **Delitos de Corrupción, Función Pública y Contratación (Arts. 397 al 428 y 431 al 434):** Representan **14.345 capturas (20.3%)**, que constituyen el núcleo de interés investigativo para cruzar con la Fiscalía General de la Nación, la Contraloría y el SECOP.

## 2. Radiografía de las Capturas por Corrupción y Contratación Estatal

Dentro del bloque de corrupción administrativa y delitos funcionales, las capturas de la Policía Nacional (DIJIN) se concentran en cuatro modalidades críticas:

1. **Cohecho (Sobornos - Arts. 405 al 407):** **8.500 capturas**, liderado por *Cohecho por dar u ofrecer (Art. 407)*.
2. **Peculado (Detrimento y apropiación del erario - Arts. 397 al 403A):** **3.277 capturas**, encabezado por *Peculado por apropiación (Art. 397)* y *Omisión del agente retenedor o recaudador (Art. 402)*.
3. **Concusión (Exigencias ilegales por funcionarios - Art. 404):** **987 capturas**.
4. **Celebración Indebida de Contratos (Arts. 408 al 410A):** **475 capturas** directas de contratistas y ordenadores del gasto por *Contrato sin cumplimiento de requisitos legales (Art. 410)*, *Interés indebido en la celebración de contratos (Art. 409)* y *Violación del régimen de inhabilidades e incompatibilidades (Art. 408)*.

### Top 5 conductas de corrupción con más capturas:
- **Art. 407 - COHECHO POR DAR U OFRECER** (Del Cohecho): **8.059 capturas**.
- **Art. 397 - PECULADO POR APROPIACION** (Del Peculado): **2.067 capturas**.
- **Art. 404 - CONCUSION** (De La Concusion): **987 capturas**.
- **Art. 402 - OMISION DEL AGENTE RETENEDOR O RECAUDADOR** (Del Peculado): **913 capturas**.
- **Art. 426 - SIMULACION DE INVESTIDURA O CARGO** (De La Usurpacion Y Abuso De Funciones Publicas): **570 capturas**.

## 3. Distribución Geográfica y Evolución Temporal

- **Concentración Territorial General:** El territorio con mayor volumen total de capturas del Título XV es **ANTIOQUIA** con **10.164 capturas**.
- **Foco Territorial de Corrupción:** Al filtrar exclusivamente los delitos de corrupción y función pública, lidera **BOGOTA, D. C.** con **2.553 capturas**, seguido de los principales centros administrativos y portuarios del país.
- **Pico Histórico Operativo:** El año con mayor número de capturas por corrupción administrativa fue **2014** (con **1.809 capturas**).

## 4. Integración con Fiscalía, Procuraduría y Contraloría (Valor para el Proyecto)

La estandarización realizada en la Capa Silver (`cod_dane_hecho` a 5 dígitos, `departamento_hecho` sin tildes, extracción de `articulo` y homologación de los 11 capítulos del Título XV del Código Penal) permite conectar directamente este módulo con el resto del proyecto:

1. **Embudo Operativo Policía vs. Fiscalía:** Mientras la Fiscalía registra cientos de miles de noticias criminales por *Celebración Indebida de Contratos* y *Peculado*, las capturas efectivas materializadas por la Policía Nacional (DIJIN) son altamente selectivas, evidenciando que los delitos de cuello blanco rara vez se capturan en flagrancia y requieren órdenes judiciales tras largas auditorías.
2. **Cruce con Procuraduría (SIRI) y SECOP:** Las capturas por el **Artículo 408 (Violación del régimen de inhabilidades e incompatibilidades)** confirman penalmente el escenario detectado en el módulo de la Procuraduría: personas inhabilitadas que intentan contratar o posesionarse ilegalmente con el Estado.
3. **Cruce con Contraloría:** Los departamentos y vigencias con mayores hallazgos con incidencia penal y fiscal en la Contraloría sirven como insumo preventivo para focalizar las unidades investigativas de la DIJIN en delitos de *Peculado por apropiación (Art. 397)*.
