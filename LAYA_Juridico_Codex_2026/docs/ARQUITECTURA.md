> Legacy reference. The confirmed English SPECIFICATION.md and ARCHITECTURE.md supersede conflicting recommendations, including optional LAYA and managed hosting. This document is not a newly executed audit.

# Arquitectura técnica y decisiones de diseño

## 1. Componentes
```
Browser / Next.js
   | Auth de Supabase; preguntas, filtros, subida, visor PDF.js
   v
FastAPI (privado detrás de reverse proxy, JWT y tenant scoping)
   +-- PostgreSQL/Supabase: exact refs -> FTS/trigram -> pgvector -> RRF
   +-- Local embeddings service: BAAI/bge-m3 (1024-d, MIT, multilingüe)
   +-- LAYA decision service (laya[serve], no inferencia externa)
   +-- Deterministic evidence explainer (templates, extractos, metadatos)
   +-- doc processor (PyMuPDF, python-docx, OCR offline si procede)

Scheduler -> source connectors -> raw storage -> parse -> versions/relations
          -> QA checkpoints -> FTS + embeddings -> publicación transaccional
```

La API de LAYA está documentada en https://github.com/NandhaKishorM/laya/blob/main/docs/http-api.md; `laya-serve` expone `/health`, `/v1/systemone` y `/v1/systemone/batch`. Configurar un bearer secreto, red interna, TLS en proxy, límites de concurrencia, sesiones; no publicarlo directamente en internet.

Ejecución recomendada para v1: 1 VPS/app node (8 vCPU/32GB RAM como hipótesis **a validar**), postgres separado/gestionado o autohospedado según privacidad. CPU sirve para desarrollo, pero medir p50/p95; si el volumen exige GPU valorar T4/16 GB o superior mediante benchmark propio. No se presupone que 33 ms anunciados por LAYA se transfieran a nuestra carga CPU y lotes largos.

El usuario exigió **LAYA local**; Supabase puede ser administrado o autohospedado, decisión separada. Para confidencialidad fuerte, estudiar Supabase autohospedado y copia de seguridad/PITR/monitoring gestionados por nosotros. Documentación: https://supabase.com/docs/guides/self-hosting

## 2. Modelo de búsqueda
**A. Interpretación de solicitud:** validar pregunta, `as_of` (fecha), territorio y tipo; si es texto seleccionado de documento añadir 1-3 fragmentos de contexto, sin incluir todo el documento. Reglas exactas detectan cita `BOE-A-...`, `Ley XX/YYYY`, `artículo`, ELI y provincia/municipio; LAYA `choice` opcional para intención y materia jurídica (solo etiquetas predefinidas, con clase otro).

**B. Recuperación de alta exhaustividad:**
- búsqueda de referencia legal exacta (si hay referencia, priorizarla y no depender de similitud)
- PostgreSQL FTS / trigramas (medir adaptación es/ca/gl/eu; `simple` de base y personalización por idioma)
- BGE-M3 embeddings: 1024 dimensiones; HNSW con el operador que coincida (`vector_cosine_ops` si distancia `<=>`)
- filtros anteriores al ranking (vigencia verificada o `unknown`, municipio/provincia/CA, rango temporal, tipo norma)
- combinación RRF, p.ej. `score=Σ 1/(60+posición)`, además de señales exactas verificables
- agregar por instrumento jurídico, mostrar el mejor artículo con opción «mostrar otros artículos»; diversidad para evitar 12 resultados de una misma ley

**C. LAYA (capa opcional sujeta a benchmark):** evaluar el par `{pregunta, título, artículo/extracto}` sobre 20-50 candidatos, con `Router.predict_batch`, `model='multilingual'` y controles de truncamiento. Primera apuesta: `choice` de 3 niveles (sin relación, relación tangencial, relación directa) como experimento A; `score` ordinal como experimento B, no requisito del MVP. Las probabilidades de LAYA **no** son probabilidades jurídicas y nunca sustituyen hechos legales de fuente. Comparar con baseline sin LAYA y publicar flag reversible (`LAYA_RERANK_ENABLED`). No filtrar resultados por LAYA si no hay evidencia de mejora.

**D. Explicación sin generación:** `explanation_rules` devuelven claves, evidencias y texto de plantilla determinista. Ejemplo:
- `match.exact_reference`: "Coincide con la referencia legal indicada en la búsqueda: {referencia}."
- `match.exact_terms`: "El {artículo} contiene las expresiones {términos}, presentes en tu consulta."
- `match.selected_clause`: "Este artículo comparte los conceptos {términos} con el fragmento seleccionado."
- `match.same_jurisdiction`: "La norma corresponde al ámbito territorial seleccionado: {territorio}."
- `match.historical`: "Se muestra la redacción identificada con fecha de publicación {fecha}; comprueba su vigencia efectiva."
- `match.unknown`: "No se ha podido verificar automáticamente la vigencia de esta redacción."
Nunca escribir "se aplica", "demuestra", "incumple" o "garantiza" si no hay evidencia jurídica independiente.

**E. Salida:** tarjeta por resultado: título oficial, tipo, institución, artículo, extracto literal, provincia/CCAA/municipio, fecha de publicación, fecha de entrada en vigor si confirmada, versión, fuente oficial, 2-4 reasons con evidencia/offsets y sello de actualización. Botón: fuente oficial, PDF original, abrir artículo, copiar referencia, mostrar otras redacciones. En modo documento resaltar correspondencia sobre página PDF y mostrar página/número de cláusula.

## 3. Documentos privados
- Aceptar PDF y DOCX, límites y antivirus, firmar URLs de upload/download.
- Primero extraer texto digital (`PyMuPDF`, `python-docx`); OCR offline (`Tesseract/OCRmyPDF`) solo al detectar ausencia de capa textual, señalizar calidad OCR.
- Segmentar por encabezados, páginas, cláusulas; preservar page, bbox/offset si es posible; generar chunks 200-500 tokens con solape pequeño sin partir artículos; para búsqueda legal usar el párrafo seleccionado + contexto cercano.
- Privacidad por `tenant_id`, sesiones auditables, autenticación real, RLS, bucket privado con políticas; borrar originales y embeddings al borrar el expediente según política.
- No guardar el contenido privado en logs, APM, analíticas o telemetría de terceros.

## 4. Datos jurídicos: dos líneas de tiempo
- `published_at`: cuándo se publica una disposición.
- `effective_from` y `effective_to`: cuándo resulta efectiva la redacción **si se verifica**; nulos indican desconocimiento, no "vigente".
- `version_publication_at`: la fecha de publicación del texto modificador, **no** entrada en vigor.
- `ingested_at`: cuándo lo aprendió el sistema.
- `consolidation_status`: `finalizado/desactualizado/unknown` si lo publica BOE.
- `lifecycle_state`: `vigente/derogada/parcial/unknown` con procedencia específica; no inferir derogación tácita.
- `legal_relationships`: `modifica/deroga/corrige/desarrolla/remite` con origen de la relación y fecha.
- `effective_date_review`: `verified/unverified`, regla/documento de respaldo.

Si el usuario consulta "ley aplicable el 15 de febrero de 2019" y falta la fecha de entrada en vigor, no adjudicar la versión con simple `published_at<=fecha`: devolver "vigencia no verificada" o escalar a revisión humana.

## 5. Expansión del corpus y escalabilidad
Separar **norma abstracta** de **su publicación original**, **cada versión**, **cada artículo y su versión**, y **los chunks**. Un instrumento autonómico puede publicarse también en BOE: deduplicación por ELI, emisor, fecha, número y equivalencias curadas (no solo hash). Conservar varias publicaciones y lenguas. Hash de blobs evita descargas repetidas; contenido OCR puede variar por proveedor. Una publicación municipal no siempre es una ordenanza: categorizar y mantener boletines de anuncios fuera del índice normativo principal.

Cursor diario por fuente, descubrimiento + reconciliación y reintentos: leer últimos 7 días; además hacer barrido mensual de periodos rezagados y recalcular corpus por registros consolidados actualizados. Respetar términos de cada sitio, robots cuando aplique y límites de uso. No utilizar scraping intensivo de donde exista API.

En PostgreSQL, índices HNSW y FTS deben evaluarse al crecer; volumen real de PDFs, coste de disco/OCR y latencias de filtros ANN son desconocidos. Presupuestar tras prueba piloto con muestras representativas y métricas.

## 6. Evaluación y umbrales propuestos (objetivos internos, no prestaciones demostradas)
- Conjunto de >=200 consultas revisadas por abogados, mezclando: referencias exactas, consultas abiertas, contratos, varios idiomas, municipio y preguntas a fecha histórica, más negativos difíciles.
- Ground truth en artículos/versions, no solo documentos.
- Medir Recall@20, MRR@10, nDCG@10, Precision@5, tasa de falsas citas, cobertura temporal, errores de territorio, porcentaje `unknown`, latencia p50/p95 y tasa de filtrado por seguridad.
- Tres brazos: 1) FTS, 2) FTS + BGE-M3 + RRF, 3) brazo 2 + LAYA. Mantener LAYA solo si mejora indicadores críticos sin aumentar errores jurídicos. Reportar resultados por idioma y longitud; fijar y versionar umbrales por calibración, no inventar un `0.8` universal.
- Probar clasificación con cláusulas largas, detección de truncación en `usage`, inversión del orden de opciones y términos negativos.
- Lanzamiento en "shadow mode" de LAYA, luego exposición gradual y rollback configurable. Documentado por upstream: https://github.com/NandhaKishorM/laya/blob/main/docs/staged-adoption.md

## 7. Seguridad y licencias
- Código LAYA: licencia Apache 2.0 declarada en repositorio; verificar licencias de pesos concretos descargados por separado.
- BGE-M3 model card: licencia MIT; atribución y avisos conforme a licencia aplicable.
- BOE reutilización comercial sometida a condiciones, atribución y "consolidado informativo/no oficial": https://www.boe.es/informacion/aviso_legal/
- Fuente BOE consolidada excluye derrogación tácita y a veces tiene 1-3 días de retraso: https://www.boe.es/datosabiertos/faq/consolidada.php
- Políticas distintas en autonomías/BOP: ficha de licencia por fuente y revisión previa a copia masiva.
- Datos privados: RGPD/LOPDGDD, encargado de tratamiento, secreto profesional, retención mínima, cifrado en reposo y tránsito, auditoría, backups cifrados, plan de eliminación y restauración. No aplicar políticas de datos públicos a expedientes privados.

## 8. Contratos de API propuestos
`POST /v1/search` `{query, territory_codes[], as_of?, legal_types[], include_historical?, mode:'question'|'document', document_id?, selected_text?, page?}` => `{results:[{instrument, article, version, snippet, source, citations, explanation_reasons[], signals, validity_status}], coverage, warnings, trace_id}`.
`POST /v1/documents` multipart PDF/DOCX => id+processing status, siempre tenant-bound.
`GET /v1/documents/:id` => estado, páginas, índice de secciones autorizadas.
`POST /v1/documents/:id/search-related` => búsqueda desde cláusula / selección; autenticación y ownership obligatorios.
`GET /v1/instruments/:id/versions` => versiones, relaciones y enlaces de fuente.
`GET /v1/coverage` => fuentes, territorio, última sincronización verificada, lag y huecos.
`GET /health` => salud API sin exponer documentos o secretos.
