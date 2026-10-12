> Legacy UX reference. Apply the confirmed English SPECIFICATION.md and docs/contracts/API.md when behavior differs. Prototype/mock data cannot pass real-data or coverage release gates.

# UX del buscador jurídico — especificación para diseño y frontend

**Dirección visual:** producto jurídico de gama alta, fondo neutro claro u oscuro configurable, tipografía sobria, mucha jerarquía, uso mínimo de color en alertas, accesible con teclado. Estilo coherente shadcn/ui con tokens centralizados. No ocultar elementos jurídicos importantes en hover.

## Vista A — Buscador
- Header pequeño: logo provisional del nuevo producto, búsqueda global, "Mis documentos", "Cobertura", usuario/despacho.
- Barra de búsqueda protagonista, autocompletado de referencia exacta y sugerencias sin generar contenido. Ej.: `¿Qué plazo tengo para interponer un recurso de alzada?`.
- Dos modos claramente diferenciados: **Preguntar por la legislación** y **Buscar desde documento**.
- Filtros persistentes: fecha en que se quiere consultar la ley, territorio (España/CA/provincia/municipio), rango normativo, norma vigente/histórica/ambas, solo estado verificado, fuente.
- Resultados en columna principal: cada norma + artículo + extracto de texto literal con resaltado de términos, URL fuente oficial, fecha redacción; agrupación de artículos de una misma norma. No saturar con 10 trozos idénticos.
- Panel derecho de detalle para resultado seleccionado, con 2-4 **explicaciones deterministas** y trazables a match exacto, coincidencia textual, tema categorizado, territorio y versión. Si motivo solo semántico, "Coincidencia temática estimada; verifica el texto del artículo"; nunca inventar razonamiento jurídico.
- Estados: buscando, sin resultados, cobertura insuficiente, versión no verificada, fuente desactualizada, error parcial de motor LAYA, corpus vacío.
- Botones funcionales: Abrir PDF original/HTML del organismo, copiar cita + enlace, comparar versiones, guardar resultado, ver normas que modifican.

## Vista B — Trabajo con PDF/DOCX
- Layout 2 paneles: izquierda visor PDF (PDF.js) o texto renderizado del DOCX (sin edición original); derecha barra de pregunta y resultados. Permitir ampliar/reducir.
- Usuario selecciona párrafo, cláusula o rango de páginas y pulsa `Buscar legislación relacionada` (recibe `document_id`, `page`, offsets y `selected_text`).
- Expandir contexto seleccionado sin enviar documento completo a LAYA. Mostrar resaltado en PDF de origen y en el texto normativo; los resaltados se basan en offsets o coincidencias literales, no explicaciones inventadas.
- Panel de resultados con misma estructura legal de vista A y pistas de selección: "Fragmento del contrato" y "Texto legal vinculado"; citas copiables.
- Mantener privado el expediente, indicadores de extracción OCR y opción de borrado.

## Comportamiento verificable
- Las tarjetas muestran 1) norma, 2) artículo, 3) texto exacto, 4) versión, 5) jurisdicción, 6) origen oficial, 7) por qué aparece, 8) limitaciones de vigencia.
- Si LAYA devuelve resultado dudoso o falla, seguir mostrando búsqueda híbrida; no ocultar resultados. Debe ser reversible sin romper UI.
- Probar uso con teclado, dispositivos móviles, accesibilidad WCAG 2.2 AA; tablas y URLs largas adaptativas.
- Analytics exclusivamente técnicos/anónimos, sin consultas privadas o contenidos de expedientes.

## Ejemplo de reasons (contrato JSON)
```
[
  {"kind":"exact_term", "display":"Coincide la expresión «plazo de recurso» en el artículo.",
   "evidence": {"query_span":[0,16], "article_span":[80,96]}},
  {"kind":"territory", "display":"El resultado corresponde al ámbito estatal seleccionado.",
   "evidence":{"territory_code":"ES"}},
  {"kind":"legal_status_warning", "display":"La vigencia de esta redacción requiere verificación.",
   "evidence":{"status":"unknown"}}
]
```
No ofrecer "resultados sobre la aplicabilidad jurídica" si faltan datos de la consulta o hay normas temporalmente inconsistentes.
