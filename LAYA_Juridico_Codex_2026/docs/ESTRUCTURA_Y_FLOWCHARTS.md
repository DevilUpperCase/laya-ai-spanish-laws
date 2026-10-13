# Arquitectura Técnica, Base de Datos y Flujos del Sistema

Este documento constituye la especificación visual y técnica de **LAYA Jurídico**, detallando la estructura de la base de datos relacional y vectorial, el motor de recuperación híbrida, la orquestación mediante LangGraph, la clasificación en modo observación con LAYA local, la gestión documental privada, el ciclo de purga irreversible y cada una de las herramientas que componen el sistema.

> [!IMPORTANT]
> **Invariante Arquitectónica Crítica**: El sistema opera bajo la política estricta de **cero modelos generativos (Zero-LLM)** y **soberanía local de datos**. Ninguna consulta, documento o fragmento jurídico se envía a APIs de terceros, garantizando privacidad procesal y ausencia total de alucinaciones.

---

## 1. Mapa de Arquitectura Global y Fronteras de Confianza

El sistema organiza sus capas en cinco niveles jerárquicos con aislamiento estricto de privilegios y redes locales:

```mermaid
flowchart TB
    subgraph CapaCliente["1. Capa de Cliente"]
        direction LR
        UI["Interfaz Web Next.js 14<br/>(TypeScript + Tailwind)"]
        CookieStorage["Sesión en Cookie<br/>(HttpOnly, SameSite)"]
        UI --- CookieStorage
    end

    subgraph Perimetro["2. Puerta de Enlace y Seguridad"]
        direction LR
        Gateway["Gateway Mismo Origen<br/>(/api/proxy)"] --> CSRF["Filtro Anti-CSRF<br/>(X-Requested-With: LAYA)"] --> RateLimiter["Límite de Payload<br/>(Máx 20 MiB Body)"]
    end

    subgraph BackendCore["3. Servicios Centrales FastAPI y Motores Locales"]
        subgraph FastAPI["Servicios FastAPI"]
            AuthModule["browser_auth.py / auth.py<br/>(Contexto de Tenant)"]
            SearchService["search_graph.py<br/>(Grafo LangGraph Efímero)"]
            DocService["documents.py / library.py<br/>(Gestión Documental)"]
            CoverageService["coverage.py<br/>(Auditoría Territorial)"]
        end

        subgraph Motores["Motores Locales Offline"]
            BGEM3["Local BGE-M3 (CPU)<br/>(Embeddings 1024-d)"]
            LAYAServe["Servidor LAYA (laya-serve)<br/>(Shadow Mode / 0 tokens)"]
            ClamAV["ClamAV Daemon<br/>(Escáner Malware en Memoria)"]
        end
    end

    subgraph Persistencia["4. Persistencia y Aislamiento RLS"]
        direction LR
        PGSQL[("PostgreSQL 16 + pgvector<br/>(Esquemas: legal, private RLS, auth)")]
        StorageFS["Almacenamiento en Disco<br/>(Originales Cifrados)"]
        DeletionJournal["Journal de Borrado<br/>(fsync en disco / Replay)"]
    end

    subgraph Workers["5. Trabajadores en Segundo Plano"]
        direction LR
        WorkerExtract["extract_worker.py<br/>(PyMuPDF + Tesseract OCR)"]
        WorkerPurge["purge_worker<br/>(Borrado Físico &lt; 24h)"]
        IngestCLI["Ingestores Oficiales<br/>(BOE, DOGC, DOG)"]
    end

    UI --> Gateway
    RateLimiter --> AuthModule
    AuthModule --> SearchService
    AuthModule --> DocService
    AuthModule --> CoverageService

    SearchService --> BGEM3
    SearchService --> LAYAServe
    SearchService --> PGSQL

    DocService --> ClamAV
    DocService --> StorageFS
    DocService --> DeletionJournal

    WorkerExtract --> PGSQL
    WorkerExtract --> StorageFS
    WorkerPurge --> StorageFS
    WorkerPurge --> PGSQL
    IngestCLI --> PGSQL
    IngestCLI --> StorageFS
```

---

## 2. Estructura de Base de Datos (Entity-Relationship Diagrams)

La base de datos utiliza una separación tajante entre el corpus normativo público (esquema `legal`) y los expedientes confidenciales del despacho (esquema `private` con **Row-Level Security** obligatorio). Para optimizar la legibilidad y escala visual, el modelo se desglosa en sus dos dominios fundamentales:

### 2.1 Esquema `legal`: Patrimonio Normativo Público e Índices Vectoriales

Almacena la legislación consolidada del Estado y Comunidades Autónomas, sus gacetas oficiales, versiones temporales y pasajes vectorizados con BGE-M3.

```mermaid
erDiagram
    JURISDICTIONS ||--o{ JURISDICTIONS : "parent_id"
    JURISDICTIONS ||--o{ INSTRUMENTS : "jurisdiction_id"
    JURISDICTIONS ||--o{ COVERAGE : "jurisdiction_id"
    SOURCES ||--o{ COVERAGE : "source_id"
    SOURCES ||--o{ INSTRUMENTS : "source_id"
    SOURCES ||--o{ PUBLICATIONS : "source_id"
    INSTRUMENTS ||--o{ PUBLICATIONS : "instrument_id"
    INSTRUMENTS ||--o{ SECTIONS : "instrument_id"
    SECTIONS ||--o{ SECTION_VERSIONS : "section_id"
    PUBLICATIONS ||--o{ SECTION_VERSIONS : "publication_id"
    SECTION_VERSIONS ||--o{ CHUNKS : "version_id"
    INSTRUMENTS ||--o{ RELATIONSHIPS : "from_instrument"

    JURISDICTIONS {
        text id PK "INE / Identificador Geográfico"
        text level "state / ca / province / municipality"
        text parent_id FK "Jerarquía territorial"
        text name "Nombre oficial y toponimia"
        boolean verified "Cobertura verificada"
    }

    SOURCES {
        text id PK "boe / dogc / dog / ..."
        text name "Nombre del diario oficial"
        text official_url "URL sede electrónica"
        text audit_status "pending / verified"
        jsonb cursor "Puntero de sincronización"
    }

    INSTRUMENTS {
        text id PK "Identificador único de norma"
        text source_id FK "Diario emisor"
        text external_id "Identificador en origen"
        text title "Título oficial publicado"
        text legal_type "Ley Orgánica, RD, Orden..."
        text jurisdiction_id FK "Ámbito territorial"
        text official_reference "Referencia consolidada"
    }

    PUBLICATIONS {
        text id PK "ID de publicación"
        text instrument_id FK "Norma vinculada"
        text source_id FK "Diario oficial"
        date publication_date "Fecha en boletín"
        text sha256 "Hash inmutable del original"
        text object_key "Ruta en disco"
        boolean is_consolidated "Texto consolidado"
    }

    SECTIONS {
        text id PK "ID de sección"
        text instrument_id FK "Norma a la que pertenece"
        text section_key "Clave de artículo"
        text heading "Artículo 1, DT 1ª..."
        integer ordinal "Orden relativo"
    }

    SECTION_VERSIONS {
        text id PK "ID de versión"
        text section_id FK "Sección correspondiente"
        text publication_id FK "Gaceta de publicación"
        date publication_date "Fecha diario oficial"
        date consolidation_date "Fecha consolidación"
        date effective_from "Entrada en vigor certificada"
        date effective_to "Cese de vigencia certificado"
        boolean effectiveness_verified "Prueba documental"
        text text "Texto literal de la norma"
        text language_code "es / ca / gl / eu"
        text sha256 "Hash de integridad"
    }

    CHUNKS {
        text id PK "ID de fragmento"
        text version_id FK "Versión correspondiente"
        integer ordinal "Posición del pasaje"
        integer start_offset "Offset inicial Unicode"
        integer end_offset "Offset final Unicode"
        text passage "Texto del pasaje"
        tsvector search_vector "FTS unaccent simple"
        vector embedding "Vector BGE-M3 (1024-d)"
        text embedding_revision "Revisión fijada modelo"
    }
```

### 2.2 Esquema `private` y `browser_auth`: Expedientes con RLS y Sesiones

Gobernado por **Row-Level Security (RLS)** obligatorio en cada tabla mediante `app.tenant_id` y `app.user_id`. Ningún despacho puede consultar registros de otro tenant bajo ninguna circunstancia.

```mermaid
erDiagram
    TENANTS ||--o{ TENANT_MEMBERS : "tenant_id"
    TENANTS ||--o{ FOLDERS : "tenant_id"
    FOLDERS ||--o{ FOLDERS : "parent_id"
    TENANTS ||--o{ DOCUMENTS : "tenant_id"
    FOLDERS ||--o{ DOCUMENTS : "folder_id"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "document_id"
    DOCUMENTS ||--o{ JOBS : "document_id"
    DOCUMENTS ||--o{ DELETION_RECORDS : "document_id"
    TENANTS ||--o{ NOTEBOOKS : "tenant_id"
    FOLDERS ||--o{ NOTEBOOKS : "folder_id"
    NOTEBOOKS ||--o{ NOTES : "notebook_id"
    DOCUMENTS ||--o{ NOTES : "document_id"
    NOTEBOOKS ||--o{ SAVED_REFERENCES : "notebook_id"
    TENANTS ||--o{ SESSIONS : "tenant_id"

    TENANTS {
        uuid id PK "Identificador del espacio"
        text name "Nombre del despacho o cliente"
        timestamptz created_at "Fecha de alta"
    }

    TENANT_MEMBERS {
        uuid tenant_id FK "Espacio de trabajo"
        uuid user_id PK "ID del usuario GoTrue"
        text role "admin / lawyer / reader"
    }

    FOLDERS {
        uuid id PK "ID de carpeta"
        uuid tenant_id FK "Aislamiento RLS"
        uuid parent_id FK "Jerarquía de carpetas"
        text name "Nombre de la carpeta"
    }

    DOCUMENTS {
        uuid id PK "ID de documento"
        uuid tenant_id FK "Aislamiento estricto RLS"
        uuid folder_id FK "Carpeta contenedora"
        text filename "Nombre de archivo original"
        text mime_type "application/pdf / docx"
        text object_key "Ruta de almacenamiento"
        text parse_status "queued / processing / ready / failed"
        integer deletion_epoch "Época de borrado"
        timestamptz trashed_at "Fecha en papelera"
        timestamptz deleted_at "Fecha de tombstone"
        timestamptz purge_due_at "Límite de purga física"
    }

    DOCUMENT_CHUNKS {
        uuid document_id FK "Documento padre"
        uuid tenant_id FK "Aislamiento RLS"
        integer page_number PK "Página o sección"
        text text "Texto extraído o reconocido"
        boolean ocr_uncertain "Marcado si fue OCR"
    }

    NOTEBOOKS {
        uuid id PK "ID de cuaderno"
        uuid tenant_id FK "Aislamiento RLS"
        uuid folder_id FK "Carpeta vinculada"
        text title "Nombre del cuaderno"
    }

    NOTES {
        uuid id PK "ID de nota jurídica"
        uuid tenant_id FK "Aislamiento RLS"
        uuid notebook_id FK "Cuaderno contenedor"
        uuid document_id FK "Documento citado (opcional)"
        integer page_number "Página de la cita"
        integer start_offset "Offset inicial Unicode"
        integer end_offset "Offset final Unicode"
        text body "Texto y conclusiones de la nota"
        integer revision "Concurrencia optimista"
    }

    SAVED_REFERENCES {
        uuid id PK "ID de referencia"
        uuid tenant_id FK "Aislamiento RLS"
        uuid notebook_id FK "Cuaderno contenedor"
        text section_version_id FK "Versión de ley guardada"
        text label "Etiqueta o apunte legal"
    }

    DELETION_RECORDS {
        uuid document_id PK "ID documento destruido"
        uuid tenant_id FK "Tenant del documento"
        timestamptz deleted_at "Momento de la orden"
        integer deletion_epoch "Época invalidada"
    }
```

---

## 3. Flujo Detallado de Búsqueda Híbrida y Fusión RRF

La consulta del usuario se procesa mediante **cinco canales de recuperación independientes** ejecutados con timeouts estrictos y planes SQL desacoplados (`force_custom_plan`), unificando los resultados mediante **Reciprocal Rank Fusion (RRF)**.

```mermaid
flowchart TD
    Start(["Inicio: Consulta del Usuario"]) --> ParseQuery["Parseo y Sanitización de Query<br/>(Límite estricto: 3.000 caracteres)"]

    subgraph EvaluacionFiltros["1. Filtros Temporales y Territoriales"]
        direction TB
        ParseQuery --> GeoResolve{"¿Filtro de Territorio?"}
        GeoResolve -- Sí --> GeoCTE["Resolución Jerárquica SQL CTE<br/>(WITH RECURSIVE ascendientes/descendientes)"]
        GeoResolve -- No --> TimeFilter
        GeoCTE --> TimeFilter{"¿Fecha as_of o Histórica?"}

        TimeFilter -- "Consulta ordinaria" --> CheckCache{"¿Caché de versiones<br/>al día?"}
        CheckCache -- Sí --> CacheSQL["Filtro Rápido en Caché<br/>(v.id IN current_versions_cache)"]
        CheckCache -- No --> DistOnSQL["SELECT DISTINCT ON (section_id)<br/>(ORDER BY consolidation_date DESC)"]
        TimeFilter -- "Histórica / as_of" --> DistOnSQL
        TimeFilter -- "verified_only = true" --> VerifiedSQL["Vigencia Verificada Obligatoria<br/>(effective_from &le; as_of &lt; effective_to)"]
    end

    CacheSQL --> BusVersiones["Versiones y Jurisdicciones Validadas"]
    DistOnSQL --> BusVersiones
    VerifiedSQL --> BusVersiones

    subgraph Motores["2. Recuperación Paralela Multicanal (Límite 100 por motor)"]
        direction TB
        BusVersiones --> M1["1. Cita Exacta (Regex BOE-A / Leyes)"]
        BusVersiones --> M2["2. FTS Léxico Ponderado (unaccent + ts_rank_cd)"]
        BusVersiones --> M3["3. Léxico Amplio (OR de términos clave &gt; 3 letras)"]
        BusVersiones --> M4["4. Similitud de Títulos (Trigramas pg_trgm %)"]
        BusVersiones --> M5["5. Semántica BGE-M3 (pgvector distancia &lt;=&gt;)"]
    end

    subgraph Fusion["3. Fusión RRF y Control de Diversidad"]
        direction TB
        M1 & M2 & M3 & M4 & M5 --> RRF["Algoritmo Reciprocal Rank Fusion (RRF)<br/>score(d) = &Sigma; [ 1 / (60 + pos) ]"]
        RRF --> Diversidad{"Diversidad por Versión:<br/>¿Más de 2 pasajes por versión?"}
        Diversidad -- Sí --> Descarte["Descartar pasaje redundante"]
        Diversidad -- No --> CandidatoValido["Conservar candidato"]
        CandidatoValido --> Top50["Corte de los 50 Mejores Candidatos"]
    end

    Top50 --> Fin(["Candidatos Híbridos Listos para LangGraph"])
```

---

## 4. Orquestación del Grafo LangGraph y Clasificador LAYA

El flujo de búsqueda ejecuta un grafo compilado sin persistencia de estado ni checkpoints privados, asegurando que ninguna consulta privada se almacene en disco.

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant API as FastAPI Gateway
    participant LG as LangGraph (Efímero)
    participant RET as HybridRetriever
    participant LAYA as LAYA (Local)
    participant EXP as Explainer

    U->>API: POST /v1/search (query, territory, as_of, scope)
    API->>LG: ainvoke(SearchState)
    Note over LG: Nodo 1: validate (Límite: hasta 3.000 caracteres)
    Note over LG: Nodo 2: resolve_selection (Offsets autorizados de documento)
    LG->>RET: Nodo 3: retrieve (5 motores en paralelo + RRF)
    RET-->>LG: 50 mejores candidatos + avisos de degradación
    Note over LG: Nodo 4: fuse (Recorte y ordenación de lote)

    alt LAYA Disponible y Saludable
        LG->>LAYA: Nodo 5: laya_shadow (POST /v1/systemone/batch)
        Note over LAYA: Clasifica relevancia: none / partial / direct<br/>(0 output tokens / modelo simbólico)
        LAYA-->>LG: Probabilidades y telemetría de uso
        Note over LG: Valida cardinalidad exacta e integridad
    else Timeout o Fallo en LAYA
        LG->>LG: Fallback Activo: Ranking RRF base + aviso LAYA_DEGRADED
    end

    LG->>EXP: Nodo 6: explain (Genera razones con evidencia literal)
    Note over EXP: Aplica plantillas exactas:<br/>match.exact_reference / exact_terms / jurisdiction
    EXP-->>LG: SearchResult enriquecida con citas literales
    Note over LG: Nodo 7: serialize
    LG-->>API: SearchResponse final
    API-->>U: JSON estructurado con extractos, razones y avisos de vigencia
```

---

## 5. Ciclo de Vida Documental Privado, OCR y Antivirus

La ingestión de documentos privados de clientes (PDF y DOCX) pasa por múltiples barreras de contención antes de estar disponible para búsqueda.

```mermaid
flowchart TD
    subgraph Recepcion["1. Recepción y Filtro de Seguridad"]
        direction TB
        Upload(["Usuario sube PDF o DOCX"]) --> SizeCheck{"¿Tamaño &le; 20 MiB?"}
        SizeCheck -- No --> Reject413["Rechazo HTTP 413: Request Too Large"]
        SizeCheck -- Sí --> Antivirus["ClamAV Streaming Scanner (clamd)"]
        Antivirus --> Infected{"¿Firma Malware?"}
        Infected -- Sí --> RejectInfected["Rechazo Inmediato: MALWARE_DETECTED"]
        Infected -- No --> StoreDisk["Almacenamiento Privado Cifrado"]
        StoreDisk --> EnqueueJob["Insert en private.documents y private.jobs"]
        EnqueueJob --> Return202["HTTP 202 Accepted al Usuario"]
    end

    subgraph Extraccion["2. Extracción y OCR Offline (extract_worker.py)"]
        direction TB
        Return202 -.-> LeaseJob["Lease con FOR UPDATE SKIP LOCKED"]
        LeaseJob --> FormatBranch{"¿Formato?"}
        FormatBranch -- DOCX --> PyDocx["python-docx (Párrafos y tablas)"]
        FormatBranch -- PDF --> PyMuPDF["PyMuPDF (Texto digital directo)"]
        PyMuPDF --> NativeCheck{"¿Tiene texto nativo?"}
        NativeCheck -- Sí --> Chunks["Segmentación por páginas"]
        NativeCheck -- No --> Tesseract["Tesseract OCR Offline<br/>(Marca ocr_uncertain = true)"]
        Tesseract --> Chunks
        PyDocx --> Chunks
    end

    subgraph PersistenciaDoc["3. Vectorización y Commit Atómico"]
        direction TB
        Chunks --> LimitCheck{"¿Páginas &le; 300 y Chars &le; 2.000.000?"}
        LimitCheck -- No --> MarkFailed["document.status = 'failed'<br/>(LIMIT_EXCEEDED)"]
        LimitCheck -- Sí --> Vectorize["Embeddings BGE-M3 (1024-d locales)"]
        Vectorize --> EpochCheck{"¿Coincide deletion_epoch?"}
        EpochCheck -->|"No (borrado durante proceso)"| Discard["Descartar resultados"]
        EpochCheck -->|Sí| CommitDB["Commit Atómico en private.chunks<br/>(status: 'ready')"]
    end

    CommitDB --> DocReady(["Documento Listo para Búsqueda y Visor"])
```

---

## 6. Flujo de Búsqueda Cruzada desde Selección de Texto en Documento

El usuario puede seleccionar cualquier párrafo o cláusula de su contrato o demanda y buscar automáticamente qué normativa oficial estatal o autonómica regula esa materia.

```mermaid
flowchart TD
    subgraph Cliente["1. Interacción en el Visor"]
        UserSelects["Usuario resalta texto en el visor de documento"] --> ClientOffsets["Navegador calcula:<br/>page_number, start_offset, end_offset (Unicode)"]
        ClientOffsets --> SendRequest["POST /v1/documents/:id/search-related<br/>(page_number, offsets, selected_text)"]
    end

    subgraph Validacion["2. Validación Criptográfica en Servidor"]
        SendRequest --> AuthCheck{"Verificación RLS:<br/>¿Tenant autorizado?"}
        AuthCheck -- No --> Err404["Error 404 / 403 No Autorizado"]
        AuthCheck -- Sí --> HashCheck{"¿Texto coincide con private.chunks<br/>para esa página y offsets?"}
        HashCheck -- No --> ErrTamper["Rechazo: DOCUMENT_SELECTION_MISMATCH"]
        HashCheck -- Sí --> ContextWindow["Extracción de Ventana de Contexto:<br/>Texto seleccionado + párrafos colindantes"]
    end

    subgraph BusquedaCruzada["3. Búsqueda Normativa Multipaso"]
        ContextWindow --> MultiQuery["RetrievalQuery con Múltiples Entradas"]
        MultiQuery --> ParallelBatches["Recuperación Híbrida Paralela"]
        ParallelBatches --> MultiRRF["Fusión RRF Multientrada"]
        MultiRRF --> FilterPublic["Búsqueda en Corpus Legal Público"]
    end

    FilterPublic --> ResultCards["Retorno de Tarjetas de Resultados:<br/>- Extracto legal oficial encontrado<br/>- Enlace oficial BOE / DOGC<br/>- Razón: Coincide con la cláusula seleccionada<br/>- Indicador de vigencia certificada"]
```

---

## 7. Ciclo de Vida: Papelera vs. Eliminación Permanente y Purga Criptográfica

El sistema distingue tajantemente entre la **Papelera** (estado transitorio recuperable) y la **Eliminación Permanente** (acción irreversible gobernada por auditoría forense y plazos RGPD).

```mermaid
stateDiagram-v2
    [*] --> Activo: Subida y procesamiento exitoso
    
    state "Documento Activo" as Activo {
        [*] --> Disponible
        Disponible --> BusquedaAdjuntos: Accesible en búsquedas
        Disponible --> NotasVinculadas: Vinculación de notas
    }

    Activo --> Papelera: Usuario pulsa 'Mover a Papelera'
    
    state "Papelera (trash = true)" as Papelera {
        [*] --> OcultoBusqueda
        OcultoBusqueda --> Previsualizacion: Previsualización permitida
        Previsualizacion --> NotasConservadas: Notas vinculadas retenidas
    }

    Papelera --> Activo: Usuario pulsa 'Restaurar'
    Papelera --> EliminacionPermanente: 'Eliminar permanentemente' o 'Vaciar Papelera'
    
    state "Protocolo de Destrucción Irreversible" as EliminacionPermanente {
        [*] --> JournalFsync: 1. Fsync inmediato en deletion_journal
        JournalFsync --> Revocacion0s: 2. Revocación instantánea (t = 0s) en RLS
        Revocacion0s --> TombstoneEpoch: 3. Tombstone e incremento deletion_epoch
        TombstoneEpoch --> PurgeWorker: 4. Asignación a cola purge_worker
        PurgeWorker --> PurgeLive24h: 5. Borrado físico de archivo y chunks (&lt; 24 horas)
        PurgeLive24h --> BackupExpiry30d: 6. Expiración de copias cifradas (&le; 30 días)
    }

    EliminacionPermanente --> [*]: Destrucción completada y verificada
```

### Protocolo de Restauración de Backups (Disaster Recovery)

Si se restaura una copia de seguridad antigua, el sistema ejecuta de forma obligatoria el script `reapply_deletions.py` contra el journal persistente en disco:

```mermaid
flowchart LR
    subgraph Contingencia["Protocolo de Recuperación ante Desastres (Disaster Recovery)"]
        direction LR
        Snapshot["Snapshot de Backup Restaurado"] --> Replay["Replay Obligatorio de deletion_records"] --> Bloqueo["Documentos eliminados permanecen destruidos"]
    end
```

---

## 8. Ingestión de Fuentes Oficiales, Publicaciones y Caché de Versiones

El subsistema de ingesta (`services/ingest/ingest/`) alimenta el corpus legislativo desde fuentes oficiales del Estado y Comunidades Autónomas, preservando la inmutabilidad de los textos originales.

```mermaid
flowchart TD
    CronSync["Sincronizador Periódico (sync_boe, sync_dogc, sync_dog)"] --> CheckCursor["Consultar cursor en legal.sources<br/>(Última gaceta integrada)"]
    CheckCursor --> FetchManifest["Descarga de Publicaciones Nuevas desde Sede Oficial"]

    FetchManifest --> StoreRaw["Almacenamiento de Original (XML/PDF)<br/>con verificación de SHA256"]
    StoreRaw --> Deduplicate{"¿SHA256 ya existe en legal.publications?"}
    Deduplicate -- Sí (Replay) --> SkipIngest["Omitir inserción duplicada"]
    Deduplicate -- No --> Parser["Parser Especializado por Diario Oficial"]

    subgraph Normalizacion["Normalización Estructural y Fechas"]
        Parser --> ExtractSections["Extracción de Secciones, Artículos y Rúbricas"]
        ExtractSections --> DateDisambiguation["Distinción Obligatoria de Fechas:<br/>publication_date vs consolidation_date vs effective_from"]
        DateDisambiguation --> GeoResolve["Resolución de Jurisdicción según Código INE"]
    end

    GeoResolve --> TxCommit["Transacción Atómica SQL en legal.*"]

    subgraph PostCommit["Actualización de Índices y Cachés"]
        TxCommit --> AdvisoryLock["Advisory Lock de Caché"]
        AdvisoryLock --> RefreshCache["Actualización Atómica de legal.current_versions_cache"]
        RefreshCache --> ReleaseLock["Liberación de Lock"]
        TxCommit --> VectorQueue["Cola de Vectorización BGE-M3 (embed_corpus.py)"]
        VectorQueue --> VectorBackfill["Cálculo de Embeddings 1024-d en Lotes"]
    end

    VectorBackfill --> ReadyCorpus(["Corpus Actualizado y Listo para Búsqueda"])
```

---

## 9. Flujo de Cuadernos Jurídicos, Notas Vinculadas y Referencias Normativas

Permite al equipo legal estructurar su investigación vinculando notas privadas directamente a líneas específicas de documentos o a artículos de leyes.

```mermaid
flowchart LR
    subgraph Biblioteca["Biblioteca y Carpetas"]
        Folders["Carpetas Jerárquicas<br/>(private.folders)"]
        Notebooks["Cuadernos de Trabajo<br/>(private.notebooks)"]
        Folders --> Notebooks
    end

    subgraph TiposDeNotas["Notas en private.notes"]
        NoteGeneral["Nota Libre de Análisis<br/>(document_id: null)"]
        NoteLinked["Nota Vinculada a Documento<br/>(document_id, página, offsets)"]
    end

    subgraph ReferenciasLegales["Referencias en private.saved_references"]
        RefVersion["Referencia Normativa Guardada<br/>(section_version_id vinculado)"]
    end

    Notebooks --> NoteGeneral
    Notebooks --> NoteLinked
    Notebooks --> RefVersion

    NoteLinked -.-> DocViewer["Enlace Directo: Abre visor en página<br/>y resalta texto citado"]
    RefVersion -.-> ReaderViewer["Enlace Directo: Abre artículo oficial<br/>en redacción exacta guardada"]
```

---

## 10. Resumen de Herramientas y Módulos del Sistema

| Herramienta / Módulo | Ubicación en el Código | Función Principal | Garantía Técnica / Restricción Crítica |
|---|---|---|---|
| **API Gateway & Sesión** | `services/api/app/browser_auth.py`, `main.py` | Autenticación basada en cookies HttpOnly y proxy seguro. | Tokens opacos en hash; rechazo CSRF sin `X-Requested-With: LAYA`. |
| **Motor de Búsqueda Híbrido** | `services/api/app/retrieval.py`, `fusion.py` | Recuperación simultánea de 5 motores y combinación RRF. | Planes SQL obligados (`force_custom_plan`); máx 2 pasajes por versión. |
| **Orquestador LangGraph** | `services/api/app/search_graph.py` | Ejecución secuencial de los nodos del pipeline de búsqueda. | Totalmente efímero: sin checkpoints ni persistencia de estado privado. |
| **Clasificador LAYA (Shadow)** | `services/api/app/laya_client.py` | Clasificación simbólica local de relevancia (`none`, `partial`, `direct`). | Cero tokens generados (0 output tokens); fallback transparente si falla. |
| **Embeddings BGE-M3** | `services/api/app/embeddings.py` | Generación de vectores densos multilingües de 1024 dimensiones. | Ejecución 100% offline (`HF_HUB_OFFLINE=1`); revisión fijada validada. |
| **Servicio de Documentos** | `services/api/app/documents.py`, `body_limit.py` | Carga, escaneo de malware y gestión de expedientes privados. | Límite estricto 20 MiB; escaneo ClamAV obligatorio antes de persistir. |
| **Worker de Extracción & OCR** | `services/api/app/extract_worker.py` | Extracción asíncrona de texto digital y OCR local Tesseract. | Ejecución desacoplada de la API; señalización `ocr_uncertain`. |
| **Biblioteca y Cuadernos** | `services/api/app/library.py`, `library_routes.py` | Organización de expedientes en carpetas, notas y referencias. | Control de concurrencia optimista en notas; RLS forzado en cada tabla. |
| **Journal de Eliminaciones** | `services/api/app/deletion_journal.py` | Registro inmutable en disco de órdenes de destrucción irreversible. | Fsync directo; replay mandatorio en cualquier restauración de backup. |
| **Monitor de Cobertura** | `services/api/app/coverage.py`, `scripts/verify_package.py` | Auditoría de fuentes integradas y bloqueo de release nacional. | El sistema rechaza declararse listo si falta cobertura territorial. |
| **Ingestores de Boletines** | `services/ingest/ingest/boe.py`, `dogc.py`, `dog.py` | Ingesta oficial automatizada de fuentes estatales y autonómicas. | Deduplicación por hash SHA256 inmutable; preservación de XML original. |
