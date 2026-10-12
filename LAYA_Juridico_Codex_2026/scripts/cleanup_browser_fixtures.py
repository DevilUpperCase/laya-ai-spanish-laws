"""Permanently remove synthetic browser-check uploads and library records."""
import argparse
import json
import sys
from pathlib import Path
import re
import httpx
import psycopg
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True);args=parser.parse_args()
    if not re.fullmatch(r'\d{13,}',args.run_id):raise ValueError('Invalid synthetic browser run ID')
    session=json.loads((ROOT/"private-data/local-session.json").read_text())
    with psycopg.connect(Settings().admin_database_url) as conn:
        ids=conn.execute("SELECT id FROM private.documents WHERE tenant_id=%s AND filename=ANY(%s) AND deleted_at IS NULL",
                         (session["tenant_id"],[f'browser-acceptance-{args.run_id}.pdf',f'browser-acceptance-{args.run_id}.docx'])).fetchall()
    with httpx.Client(trust_env=False,timeout=30) as client:
        for (identifier,) in ids:
            response=client.delete("http://127.0.0.1:8000/v1/documents/"+str(identifier),headers={"Authorization":"Bearer "+session["token"],"X-Tenant-ID":session["tenant_id"]})
            response.raise_for_status()
    with psycopg.connect(Settings().admin_database_url) as conn:
        pattern=f'Browser acceptance {args.run_id}%'
        notebook_ids=[row[0] for row in conn.execute('SELECT id FROM private.notebooks WHERE tenant_id=%s AND title LIKE %s',(session['tenant_id'],pattern)).fetchall()]
        folder_ids=[row[0] for row in conn.execute('SELECT id FROM private.folders WHERE tenant_id=%s AND name LIKE %s',(session['tenant_id'],pattern)).fetchall()]
        if notebook_ids:
            conn.execute('DELETE FROM private.notes WHERE notebook_id=ANY(%s)',(notebook_ids,))
            conn.execute('DELETE FROM private.saved_references WHERE notebook_id=ANY(%s)',(notebook_ids,))
            conn.execute('DELETE FROM private.notebooks WHERE id=ANY(%s)',(notebook_ids,))
        if folder_ids:
            conn.execute('UPDATE private.documents SET folder_id=NULL WHERE folder_id=ANY(%s)',(folder_ids,))
            conn.execute('UPDATE private.notebooks SET folder_id=NULL WHERE folder_id=ANY(%s)',(folder_ids,))
            conn.execute('DELETE FROM private.folders WHERE id=ANY(%s)',(folder_ids,))
    print('Synthetic browser records removed:',len(ids),'uploads,',len(notebook_ids),'notebooks,',len(folder_ids),'folders')
