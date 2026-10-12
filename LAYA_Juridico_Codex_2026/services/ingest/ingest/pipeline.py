from datetime import datetime, timezone
from pathlib import Path
import json
from dataclasses import asdict
from psycopg.types.json import Jsonb
from .boe import digest


def chunks(text: str, size: int = 1800, overlap: int = 200):
    start, ordinal = 0, 0
    while start < len(text):
        end = min(start + size, len(text))
        yield ordinal, start, end, text[start:end]
        if end == len(text):
            break
        start, ordinal = end - overlap, ordinal + 1


def store_publication(conn, parsed, raw, storage: Path, jurisdiction_id: str):
    sha = digest(raw.content)
    if raw.format not in {'xml','json','html','pdf'}:raise ValueError('Unsupported original format')
    key = sha + '.' + raw.format
    storage.mkdir(parents=True, exist_ok=True)
    destination = storage / key
    if not destination.exists():
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(raw.content)
        temporary.replace(destination)
    identifier = parsed.instrument_id or parsed.external_id
    metadata_sha=None
    if parsed.instrument_id:
        metadata_sha=digest(json.dumps({'publication_date':str(parsed.publication_date),'official_url':raw.ref.official_url,'versions':[asdict(v) for v in parsed.versions]},default=str,sort_keys=True,separators=(',',':')))
    publication_id = digest(raw.ref.source_id + ":" + identifier + ":" + sha + (':'+metadata_sha if metadata_sha else ''))
    with conn.transaction():
        if conn.execute("SELECT 1 FROM legal.publications WHERE id=%s",(publication_id,)).fetchone():
            return 0  # Already committed atomically; replay does not resend all historical chunks.
        conn.execute("""INSERT INTO legal.instruments(id,source_id,external_id,title,legal_type,jurisdiction_id,eli,official_reference,official_url)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET title=excluded.title""",
          (identifier,raw.ref.source_id,parsed.external_id,parsed.title,parsed.legal_type,jurisdiction_id,parsed.eli,parsed.official_reference,parsed.official_url))
        conn.execute('UPDATE legal.instruments SET ingestion_warnings=%s WHERE id=%s',(Jsonb(list(parsed.ingestion_warnings)),identifier))
        conn.execute("""INSERT INTO legal.publications(id,instrument_id,source_id,official_url,publication_date,sha256,object_key,format,is_consolidated,source_updated_at,metadata_sha256)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
          (publication_id,identifier,raw.ref.source_id,raw.ref.official_url,parsed.publication_date,sha,key,raw.format,parsed.is_consolidated,parsed.source_updated_at,metadata_sha))
        for version in parsed.versions:
            section_id = identifier + ":" + version.section_key
            conn.execute("INSERT INTO legal.sections VALUES(%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING",
                         (section_id,identifier,version.section_key,version.heading,version.ordinal))
            conn.execute("""INSERT INTO legal.section_versions(id,section_id,publication_id,version_ref,publication_date,consolidation_date,effective_from,effectiveness_verified,text,language_code,sha256)
             VALUES(%s,%s,%s,%s,%s,%s,%s,false,%s,%s,%s) ON CONFLICT DO NOTHING""",
             (version.id,section_id,publication_id,version.version_ref,version.publication_date,version.consolidation_date,version.effective_from,version.text,version.language_code,version.sha256))
            conn.execute("UPDATE legal.section_versions SET source_order=%s WHERE id=%s",(version.source_order,version.id))
            if version.official_url:conn.execute('UPDATE legal.section_versions SET official_url=%s WHERE id=%s',(version.official_url,version.id))
            for ordinal,start,end,passage in chunks(version.text):
                conn.execute("""INSERT INTO legal.chunks(id,version_id,ordinal,start_offset,end_offset,passage,search_vector)
                 VALUES(%s,%s,%s,%s,%s,%s,to_tsvector('simple',public.unaccent(%s))) ON CONFLICT DO NOTHING""",
                 (version.id + ":" + str(ordinal),version.id,ordinal,start,end,passage,passage))
        for target,kind in parsed.relationships:
            conn.execute("INSERT INTO legal.relationships VALUES(%s,%s,%s,%s,false) ON CONFLICT DO NOTHING",
                         (identifier,target,kind,raw.ref.official_url))
        conn.execute('SELECT pg_advisory_xact_lock(149728)')
        conn.execute("""INSERT INTO legal.current_versions_cache(section_id,version_id)
        SELECT DISTINCT ON(v.section_id) v.section_id,v.id FROM legal.section_versions v JOIN legal.sections s ON s.id=v.section_id
        WHERE s.instrument_id=%s AND v.publication_date<=(SELECT as_of FROM legal.current_cache_metadata WHERE singleton)
        ORDER BY v.section_id,v.consolidation_date DESC NULLS LAST,v.source_order DESC,v.id DESC
        ON CONFLICT(section_id) DO UPDATE SET version_id=excluded.version_id""",(identifier,))
    return len(parsed.versions)


def ingest_window(conn, adapter, storage, *, start_date=None, end_date=None, limit=None, jurisdiction_resolver=None):
    run = conn.execute("INSERT INTO legal.ingest_runs(source_id,window_start,window_end) VALUES(%s,%s,%s) RETURNING id",
                       (adapter.source_id,start_date,end_date)).fetchone()[0]
    conn.commit()
    cursor, discovered, integrated, gaps, stopped = None, 0, 0, list(getattr(adapter,'inherent_gaps',())), False
    try:
        while True:
            page = adapter.discover(start_date, end_date, cursor)
            for ref in page.publications:
                if limit is not None and integrated >= limit:
                    stopped = True
                    break
                discovered += 1
                try:
                    raw = adapter.fetch(ref)
                    parsed = adapter.parse(raw)
                    jurisdiction = "ES" if parsed.scope == "Estatal" else (jurisdiction_resolver(parsed) if jurisdiction_resolver else None)
                    if not jurisdiction:
                        gaps.append(ref.external_id + ":JURISDICTION_UNRESOLVED")
                        continue
                    store_publication(conn,parsed,raw,storage,jurisdiction)
                    conn.commit()
                    integrated += 1
                    conn.execute("UPDATE legal.ingest_runs SET discovered_count=%s,integrated_count=%s,gaps=%s,cursor=%s WHERE id=%s",(discovered,integrated,Jsonb(gaps),Jsonb(cursor),run))
                    conn.commit()
                except Exception:
                    conn.rollback()
                    gaps.append(ref.external_id + ":INGEST_FAILED")
            cursor = page.next_cursor
            if stopped or cursor is None:
                break
        status = "complete" if not stopped and not gaps else "partial"
        conn.execute("UPDATE legal.ingest_runs SET status=%s,finished_at=now(),discovered_count=%s,integrated_count=%s,cursor=%s,gaps=%s WHERE id=%s",
                     (status,discovered,integrated,Jsonb(cursor),Jsonb(gaps),run))
        conn.execute("UPDATE legal.sources SET last_checked_at=now() WHERE id=%s", (adapter.source_id,))
        if status == "complete":
            conn.execute("UPDATE legal.sources SET last_successful_sync=now(),cursor=%s WHERE id=%s", (Jsonb(cursor),adapter.source_id))
        conn.commit()
        return {"run_id":str(run),"status":status,"discovered":discovered,"integrated":integrated,"gaps":gaps,"limited_internal_import":stopped}
    except Exception:
        conn.rollback()
        conn.execute("UPDATE legal.ingest_runs SET status='failed',finished_at=now(),failure_code='SOURCE_FAILURE',discovered_count=%s,integrated_count=%s,cursor=%s,gaps=%s WHERE id=%s",(discovered,integrated,Jsonb(cursor),Jsonb(gaps),run))
        conn.commit()
        raise
