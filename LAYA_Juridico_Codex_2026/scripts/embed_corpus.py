"""Embed current observed section versions locally; originals/history remain preserved."""
import argparse
import asyncio
import os
from pathlib import Path
import sys
import json,time
from datetime import datetime,timezone
import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.api.app.embeddings import EmbeddingClient


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit",type=int,default=0,help="0 means all current observed versions")
    parser.add_argument('--include-history',action='store_true',help='Index current versions first, then all retained historical versions')
    parser.add_argument('--threads',type=int,default=4,choices=range(1,65))
    parser.add_argument('--batch-size',type=int,default=8,choices=range(1,65))
    args=parser.parse_args()
    if args.limit<0:parser.error('Limit must be nonnegative')
    settings=Settings(embedding_threads=args.threads,embedding_batch_size=args.batch_size)
    import torch
    torch.set_num_threads(args.threads)
    embedding=EmbeddingClient(settings)
    count=0
    with psycopg.connect(settings.ingest_database_url) as conn:
        if not conn.execute('SELECT pg_try_advisory_lock(149727)').fetchone()[0]:
            raise RuntimeError('Another pinned-corpus indexer owns the database lock')
        register_vector(conn)
        conn.execute('CREATE TEMP TABLE latest_versions AS SELECT DISTINCT ON(section_id) id FROM legal.section_versions ORDER BY section_id,consolidation_date DESC NULLS LAST,source_order DESC,id DESC')
        conn.execute('CREATE UNIQUE INDEX ON latest_versions(id)');conn.execute('ANALYZE latest_versions');conn.commit()
        initial=conn.execute('SELECT count(*) FROM legal.chunks WHERE embedding IS NOT NULL AND embedding_revision=%s',(settings.embedding_model_revision,)).fetchone()[0]
        total=conn.execute('SELECT count(*) FROM legal.chunks').fetchone()[0]
        stage='current';started=time.monotonic()
        def progress(status):
            elapsed=time.monotonic()-started;rate=count/elapsed if elapsed and count else None
            report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':status,'stage':stage,'revision':settings.embedding_model_revision,'include_history':args.include_history,'threads':args.threads,'batch_size':args.batch_size,'initial_pinned_chunks':initial,'committed_this_run':count,'total_snapshot_chunks':total,'chunks_per_second':rate,'estimated_all_history_seconds_remaining':max(0,total-initial-count)/rate if rate and args.include_history else None,'limitation':'Throughput estimate changes with passage lengths and new ingestion. Completion is checked by SQL, not this estimate.'}
            path=ROOT/'verification/reports/index-progress.json';temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
        progress('running')
        while not args.limit or count<args.limit:
            bulletin_rows=conn.execute('SELECT id,passage FROM legal.bulletin_chunks WHERE embedding IS NULL OR embedding_revision IS DISTINCT FROM %s ORDER BY id LIMIT %s',(settings.embedding_model_revision,args.batch_size)).fetchall()
            if bulletin_rows:
                bulletin_vectors=await embedding.embed([r[1] for r in bulletin_rows])
                for row,vector in zip(bulletin_rows,bulletin_vectors):conn.execute('UPDATE legal.bulletin_chunks SET embedding=%s,embedding_revision=%s WHERE id=%s',(Vector(vector),settings.embedding_model_revision,row[0]))
                conn.commit()
            latest="AND EXISTS(SELECT 1 FROM latest_versions v WHERE v.id=c.version_id)" if stage=='current' else ''
            rows=conn.execute('SELECT c.id,c.passage FROM legal.chunks c WHERE (c.embedding IS NULL OR c.embedding_revision IS DISTINCT FROM %s) '+latest+' ORDER BY c.id LIMIT %s',(settings.embedding_model_revision,min(args.batch_size,args.limit-count) if args.limit else args.batch_size)).fetchall()
            if not rows:
                if stage=='current' and args.include_history:stage='history';progress('running');continue
                break
            vectors=await embedding.embed([r[1] for r in rows])
            for row,vector in zip(rows,vectors):
                conn.execute("UPDATE legal.chunks SET embedding=%s,embedding_revision=%s WHERE id=%s",(Vector(vector),settings.embedding_model_revision,row[0]))
            conn.commit()
            count+=len(rows)
            print("Embedded",count,"chunks",flush=True)
            progress('running')
        progress('bounded' if args.limit and count>=args.limit else 'complete_snapshot')
    print("Embedding run complete:",count)


if __name__=="__main__":asyncio.run(main())
