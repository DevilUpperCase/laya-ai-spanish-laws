"""Export every real jurisdiction for source/history review; never approve coverage."""
import csv,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings


def main():
    settings=Settings()
    with psycopg.connect(settings.ingest_database_url) as conn:
        rows=conn.execute('SELECT id,level,parent_id,name,official_source_url,inventory_revision FROM legal.jurisdictions ORDER BY id').fetchall()
        counts=dict(conn.execute('SELECT jurisdiction_id,count(*) FROM legal.instruments GROUP BY jurisdiction_id').fetchall())
        sources=conn.execute('SELECT id,name,official_url,adapter,audit_status FROM legal.sources ORDER BY id').fetchall()
    path=ROOT/'sources/nationwide-review-queue.csv'
    with path.open('w',encoding='utf-8',newline='') as out:
        writer=csv.writer(out);writer.writerow(['jurisdiction_id','level','parent_id','name','inventory_url','inventory_revision','observed_instruments','required_source_ids','current_from','current_to','history_from','history_to','unavailable_history_evidence','expected_norms','integrated_norms','missing_required_periods','source_audit_path','source_audit_sha256','reviewer','reviewed_at','status'])
        for row in rows:writer.writerow([*row,counts.get(row[0],0),*(['']*13),'pending'])
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'blocked','required_jurisdictions':len(rows),'levels':dict(Counter(r[1] for r in rows)),'approved_jurisdictions':0,'publishers':[dict(zip(('id','name','url','adapter','audit_status'),r)) for r in sources],'queue':str(path.relative_to(ROOT)),'limitations':['Observed instrument counts do not prove jurisdiction coverage.','All current/history source audits, reuse terms and institutional inventory review remain mandatory.','Foral institutional supplement and island workbook date mismatch remain unresolved.']}
    (ROOT/'verification/reports/nationwide-coverage.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Exported {len(rows)} pending jurisdictions; no coverage approval was created.')


if __name__=='__main__':main()
