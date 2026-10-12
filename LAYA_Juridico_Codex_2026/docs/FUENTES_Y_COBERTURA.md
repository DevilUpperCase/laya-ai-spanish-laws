> Legacy reference. SPECIFICATION.md requires every jurisdiction verified before first release. This inventory is not proof of ingestion, current capability, license approval or national completeness; see sources/README.md and DECISIONS.md.

# Fuentes oficiales y estrategia de cobertura de España

## Hechos contrastados a 11/10/2026

1. **BOE — sumarios:** endpoint `GET https://www.boe.es/datosabiertos/api/boe/sumario/{YYYYMMDD}`; sumarios disponibles desde septiembre de 1960; proporcionan URL de textos PDF/XML/HTML cuando los hay. **No** es sinónimo de descargar todas las leyes consolidadas.
2. **BOE — legislación consolidada:** `GET https://www.boe.es/datosabiertos/api/legislacion-consolidada?offset=0&limit=50` acepta `from`, `to` (fechas de *última actualización* YYYYMMDD), `offset`, `limit`; `limit=-1` está documentado para lista completa, pero se prefiere paginar y respaldar con checkpoints. Para cada ID: `.../id/{BOE-A-YYYY-NNNNN}` devuelve la norma; endpoints específicos `/metadatos`, `/analisis`, `/texto`, `/texto/indice` y `/texto/bloque/{id_bloque}` en documentación. Verificar Content-Type real y parsing XML antes de fijar parser.
3. El BOE sólo consolida **normas seleccionadas**, estatales y autonómicas. **No** garantiza todos los textos de todas las administraciones, ni modificaciones tácitas. El status `estado_consolidacion` puede ser `finalizado` o `desactualizado`, y los nuevos consolidados suelen tardar 1-3 días tras una modificación. El atributo de fecha de una *versión de bloque* es publicación de la disposición modificadora, no necesariamente entrada en vigor.
4. **DOGC / Portal Jurídic de Catalunya:** dataset `n6hn-rmy7`, catálogo y formatos CSV/JSON/XML, frecuencia de actualización diaria, normativa vigente y derogada publicada en DOGC (normativa de rangos especificados). Dataset: https://datos.gob.es/es/catalogo/a09002970-normativa-de-cataluna-publicada-en-el-dogc . Ejemplo de recurso de catálogo JSON: https://analisi.transparenciacatalunya.cat/api/v3/views/n6hn-rmy7/query.json?accessType=DOWNLOAD ; evaluar esquema, paginación, licencias del dataset y documentos enlazados antes de ingestión.
5. **17 comunidades autónomas + Ceuta/Melilla:** directorio BOE: https://www.boe.es/legislacion/otros_diarios_oficiales.php . El directorio ofrece enlaces humanos, no prueba que todos tengan una API o dumps públicos. La ingeniería consiste en inspeccionar una a una capacidades, históricos, PDF/XML/HTML y licencias.
6. **43 entradas provinciales enumeradas** en el directorio de BOE (no hay BOP independiente en las provincias de comunidades uniprovinciales y Ceuta/Melilla): https://administracion.gob.es/pag_Home/espanaAdmon/boletinesYLegislacion/BO_Diputaciones.html . No convertir cada entrada en una afirmación de disponibilidad de API.
7. **Municipios:** no existe una única fuente nacional integral garantizada de ordenanzas vigentes históricas. La vía principal de localización de ordenanzas es la publicación en los boletines provinciales conforme al artículo 70.2 de Ley 7/1985, con particularidades legales. Incorporar portales de normativa municipal cuando tengan un texto consolidado más útil, con atribución y control de duplicados.
8. **Códigos geográficos:** INE códigos de comunidades, provincias y municipios; cinco primeros dígitos del municipio (2 provincia + 3 municipio) y dígito de control adicional: https://www.ine.es/daco/daco42/codmun/codmun00i.htm . No fiarse de nombres de pueblos extraídos con OCR sin cotejar código.

## Matriz de CCAA y ciudades autónomas (inventario de diarios, NO auditoría de APIs)
| Territorio | Diario o boletín | Enlace de referencia |
|---|---|---|
| Andalucía | BOJA | https://www.boe.es/legislacion/otros_diarios_oficiales.php |
| Aragón | BOA | idem |
| Asturias | BOPA | idem |
| Illes Balears | BOIB | idem |
| Canarias | BOC | idem |
| Cantabria | BOC | idem |
| Castilla-La Mancha | DOCM | idem |
| Castilla y León | BOCYL | idem |
| Cataluña | DOGC | Dataset específico confirmado |
| Comunitat Valenciana | DOGV | Directorio BOE |
| Extremadura | DOE | Directorio BOE |
| Galicia | DOG | Directorio BOE |
| La Rioja | BOR | Directorio BOE |
| Comunidad de Madrid | BOCM | Directorio BOE |
| Región de Murcia | BORM | Directorio BOE |
| Navarra | BON | Directorio BOE |
| País Vasco | BOPV | Directorio BOE |
| Ceuta | BOCCE | Directorio BOE |
| Melilla | BOME | Directorio BOE |

**Inventario provincial (43 entradas de referencia en directorio BOE):** A Coruña, Albacete, Alicante, Almería, Araba/Álava, Ávila, Badajoz, Barcelona, Bizkaia, Burgos, Cáceres, Cádiz, Castellón, Ciudad Real, Córdoba, Cuenca, Gipuzkoa, Girona, Granada, Guadalajara, Huelva, Huesca, Jaén, Las Palmas, León, Lleida, Lugo, Málaga, Ourense, Palencia, Pontevedra, Salamanca, Santa Cruz de Tenerife, Segovia, Sevilla, Soria, Tarragona, Teruel, Toledo, Valencia, Valladolid, Zamora, Zaragoza. Directorio oficial: https://www.boe.es/legislacion/otros_diarios_oficiales.php

## Contrato de cada conector
Archivo `sources/<id>.yaml` con:
- identidad de fuente; órgano; nivel territorial; código normalizado; enlaces oficiales
- `capabilities`: discovery API / bulk export / RSS / HTML / PDF / XML; versiones consolidadas; histórico; publicación diaria
- ventana histórica auditada `coverage_start`, `coverage_end`; `completeness_level`: `unknown|partial|verified`
- URL y licencia de reutilización auditadas, restricción de robots/uso y frecuencia permitida
- metadatos de las fechas disponibles; resolución temporal; parser versionado; fixtures de ejemplo
- cursor, `ETag`, `Last-Modified` si existen, último sync verificado, días faltantes, errores
- reglas de clasificación normativa versus anuncios; detector de duplicados; mapeo de códigos INE

**Interfaz:** `discover(start_date,end_date)->PublicationRef[]`, `fetch(ref)->RawPublication`, `parse(raw)->ParsedPublication`, `reconcile(...)`, `healthcheck()`. Métodos idempotentes. Capturar raw original sin modificar, SHA256, URL oficial y timestamp; comparar metadatos antes de re-embeddar todo. Validar encabezados, número de disposición, título, artículo y vínculos modificadores.

## Carga inicial y actualización diaria
### Inicial
- Inicializar directorio de órganos, INE, boletines y términos. Guardar fuentes `coverage=unknown` inicialmente.
- BOE: paginar índice consolidado, descargar en lotes, almacenar XML, parsear bloques y todas sus versiones, metadatos y análisis. Obtener publicaciones originales cuando haya URL y permiso. Crear pruebas contra normas con muchas modificaciones.
- BOE sumarios históricos: recorrer desde el periodo objetivo conocido; sumarios desde 1960 no equivalen a cobertura histórica completa anterior.
- DOGC: importar catálogo disponible y fechas; validar régimen de reutilización y fuente original.
- Resto CCAA/BOP: auditoría manual de servicio oficial/descargas y desarrollo de conectores por prioridad. Extraer ordenanzas del BOP y cotejar textos consolidados municipales cuando existan.
### Diaria
- Por cada fuente: `T-7..T` idempotente, detectar nuevas publicaciones (o utilizar cursor de actualización si existe), procesar nuevas versiones y correcciones, detectar cambios de consolidación, reindexar solo los chunks modificados.
- Guardar `source_run_id`, conteos, watermark, errores, gaps, tiempo sin novedades y alertas. No dar la fuente por "al día" si fallan publicaciones.
- Una vez a la semana revisar periodos con fallos; mensualmente backfill de ventanas relevantes.
- Transparencia en UI: "última consulta a la fuente", "última publicación integrada", "fuente actualizada / retraso / desconocido" y "cobertura histórica auditada".

## Reutilización y responsabilidad
BOE licencia comercial permisiva pero condicionada a fuente, metadatos, indicación de que el consolidado es informativo y no official; ver https://www.boe.es/informacion/aviso_legal/ . Cada CCAA/BOP debe tener su propia revisión de términos. No redistribuir contenido con derechos ajenos o datos personales sin base jurídica. Mantener los archivos originales no equivale a que la extracción, OCR o normalización sea un texto oficial.
