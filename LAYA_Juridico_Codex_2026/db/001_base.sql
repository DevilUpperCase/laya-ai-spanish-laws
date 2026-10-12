-- ESQUEMA ORIENTATIVO. Verificar permisos/extensiones en Supabase antes de desplegar.
-- Para Supabase habitual: pgvector en schema extensions, pg_trgm en public o extensions.
create schema if not exists extensions;
create extension if not exists vector with schema extensions;
create extension if not exists pg_trgm with schema extensions;

create table if not exists public.legal_sources (
  id bigint generated always as identity primary key,
  code text not null unique,
  name text not null,
  official_homepage text not null,
  legal_reuse_url text,
  source_type text not null check(source_type in ('BOE','REGIONAL','PROVINCIAL','MUNICIPAL')),
  jurisdiction_code text,
  coverage_start date,
  coverage_end date,
  coverage_quality text not null default 'unknown' check(coverage_quality in ('unknown','partial','verified')),
  last_successful_sync timestamptz,
  last_verified_publication date
);

create table if not exists public.jurisdictions (
  code text primary key, -- ISO / INE code; names in separate translations table if needed
  name text not null,
  kind text not null check(kind in ('country','autonomous_community','province','municipality','city_autonomous')),
  parent_code text references public.jurisdictions(code)
);

create table if not exists public.legal_instruments (
  id bigint generated always as identity primary key,
  canonical_key text not null unique, -- ELI, BOE ref or source-specific canonical id
  eli_uri text,
  official_title text not null,
  legal_type text not null,
  issuing_body text,
  jurisdiction_code text references public.jurisdictions(code),
  lifecycle_status text not null default 'unknown' check(lifecycle_status in ('vigente','parcial','derogada','unknown')),
  lifecycle_evidence_uri text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.legal_publications (
  id bigint generated always as identity primary key,
  instrument_id bigint references public.legal_instruments(id),
  source_id bigint not null references public.legal_sources(id),
  official_ref text,
  publication_date date,
  official_url text not null,
  raw_format text not null check(raw_format in ('xml','html','pdf','json','text','other')),
  raw_storage_path text, -- bucket sólo backend, no URL pública implícita
  content_sha256 text,
  ingested_at timestamptz not null default now(),
  unique(source_id,official_ref,official_url)
);

create table if not exists public.legal_sections (
  id bigint generated always as identity primary key,
  instrument_id bigint not null references public.legal_instruments(id),
  section_key text not null, -- stable within an instrument, not necessarily 'artículo'
  kind text not null,
  heading text,
  sort_order numeric(12,4),
  unique(instrument_id,section_key)
);

create table if not exists public.legal_section_versions (
  id bigint generated always as identity primary key,
  section_id bigint not null references public.legal_sections(id),
  source_publication_id bigint references public.legal_publications(id),
  publication_date date, -- version label publication date; NOT effective_from
  effective_from date, -- NULL means not verified
  effective_to date, -- NULL means unknown, NOT necessarily current
  effectiveness_verified boolean not null default false,
  text_content text not null,
  language_code text not null default 'es',
  consolidation_status text not null default 'unknown' check(consolidation_status in ('finalizado','desactualizado','unknown','not_applicable')),
  version_ref text,
  content_sha256 text not null,
  last_checked_at timestamptz not null default now(),
  unique(section_id,version_ref,language_code,content_sha256)
);

create table if not exists public.legal_relationships (
  id bigint generated always as identity primary key,
  from_instrument_id bigint not null references public.legal_instruments(id),
  to_instrument_id bigint not null references public.legal_instruments(id),
  type text not null check(type in ('modifica','deroga','corrige','desarrolla','remite','other')),
  source_publication_id bigint references public.legal_publications(id),
  relation_note text,
  verified boolean not null default false
);

create table if not exists public.legal_chunks (
  id bigint generated always as identity primary key,
  section_version_id bigint not null references public.legal_section_versions(id) on delete cascade,
  ordinal integer not null,
  content text not null,
  start_offset integer,
  end_offset integer,
  embedding extensions.vector(1024), -- BAAI/bge-m3; model version must be pinned
  embedding_model text,
  fts tsvector generated always as (to_tsvector('simple'::regconfig, content)) stored,
  unique(section_version_id,ordinal)
);
create index if not exists legal_chunks_fts_idx on public.legal_chunks using gin(fts);
-- Crear vector HNSW después de validar volumen y memoria; ejemplo:
-- create index legal_chunks_hnsw on public.legal_chunks using hnsw (embedding extensions.vector_cosine_ops);

create table if not exists public.ingest_runs (
  id bigint generated always as identity primary key,
  source_id bigint not null references public.legal_sources(id),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check(status in ('running','success','partial','failed')),
  publications_seen integer not null default 0,
  publications_changed integer not null default 0,
  errors jsonb not null default '[]'::jsonb,
  cursor_data jsonb,
  window_start date,
  window_end date
);

-- Expedientes privados: nunca incluir contenido personal en corpus public legal_chunks.
create table if not exists public.tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null
);
create table if not exists public.tenant_members (
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check(role in ('admin','lawyer','reader')),
  primary key(tenant_id,user_id)
);
create table if not exists public.client_documents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  uploaded_by uuid references auth.users(id),
  original_filename text not null,
  private_object_path text not null,
  document_sha256 text,
  mime_type text not null,
  parse_status text not null default 'queued',
  created_at timestamptz not null default now(),
  deleted_at timestamptz
);
create table if not exists public.client_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.client_documents(id) on delete cascade,
  tenant_id uuid not null references public.tenants(id) on delete cascade,
  ordinal integer not null,
  page_number integer,
  start_offset integer,
  end_offset integer,
  content text not null,
  embedding extensions.vector(1024),
  fts tsvector generated always as (to_tsvector('simple'::regconfig, content)) stored,
  unique(document_id,ordinal)
);
create index if not exists client_chunks_doc_idx on public.client_chunks(document_id);
create index if not exists client_chunks_fts_idx on public.client_chunks using gin(fts);

-- Corpus público: lectura autenticada, escrituras exclusivamente desde pipeline backend.
alter table public.legal_sources enable row level security;
alter table public.jurisdictions enable row level security;
alter table public.legal_instruments enable row level security;
alter table public.legal_publications enable row level security;
alter table public.legal_sections enable row level security;
alter table public.legal_section_versions enable row level security;
alter table public.legal_relationships enable row level security;
alter table public.legal_chunks enable row level security;
alter table public.ingest_runs enable row level security;

create policy "authenticated_read_sources" on public.legal_sources for select to authenticated using (true);
create policy "authenticated_read_jurisdictions" on public.jurisdictions for select to authenticated using (true);
create policy "authenticated_read_instruments" on public.legal_instruments for select to authenticated using (true);
create policy "authenticated_read_publications" on public.legal_publications for select to authenticated using (true);
create policy "authenticated_read_sections" on public.legal_sections for select to authenticated using (true);
create policy "authenticated_read_versions" on public.legal_section_versions for select to authenticated using (true);
create policy "authenticated_read_relationships" on public.legal_relationships for select to authenticated using (true);
create policy "authenticated_read_chunks" on public.legal_chunks for select to authenticated using (true);
-- Runs de ingestión no públicos, solo backend.

alter table public.tenants enable row level security;
alter table public.tenant_members enable row level security;
alter table public.client_documents enable row level security;
alter table public.client_chunks enable row level security;

-- Políticas restringidas para las lecturas; gestion de altas/bajas por backend.
-- tenant_members lectura SOLO de propia fila evita recursión; gestión admins por backend.
create policy "read_own_membership" on public.tenant_members for select to authenticated
 using(user_id=auth.uid());
create policy "read_own_tenant" on public.tenants for select to authenticated
 using(exists(select 1 from public.tenant_members m where m.tenant_id=tenants.id and m.user_id=auth.uid()));
create policy "read_tenant_documents" on public.client_documents for select to authenticated
 using(deleted_at is null and exists(select 1 from public.tenant_members m where m.tenant_id=client_documents.tenant_id and m.user_id=auth.uid()));
create policy "read_tenant_chunks" on public.client_chunks for select to authenticated
 using(exists(select 1 from public.tenant_members m join public.client_documents d on d.id=client_chunks.document_id and d.tenant_id=m.tenant_id where m.tenant_id=client_chunks.tenant_id and m.user_id=auth.uid() and d.deleted_at is null));
-- IMPORTANTE: sin policy INSERT/UPDATE/DELETE por usuario aún.
-- El backend elevado debe comprobar a qué tenant pertenece cada operación antes de usar un rol que omite RLS.
-- RLS Storage (storage.objects) debe crearse aparte al registrar buckets; no confiar en este SQL para ello.
