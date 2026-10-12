"""Check official processing and nationwide blockers; success never inferred from counts."""
import argparse,json,sys
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.api.app.config import Settings
from services.ingest.ingest.processing_status import collect_processing_status

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify-files',action='store_true');args=parser.parse_args()
    settings=Settings()
    try:
        with psycopg.connect(settings.ingest_database_url) as conn:
            report=collect_processing_status(conn,json.loads((ROOT/'sources/bulletin-scope.json').read_text(encoding='utf-8')),verify_files=args.verify_files,storage_root=settings.public_storage_path)
        if not args.verify_files:report['all_complete']=False;report['blockers'].append({'code':'ORIGINAL_INTEGRITY_CHECK_NOT_RUN'})
    except Exception as error:
        report={'all_complete':False,'operational_error':type(error).__name__}
    path=ROOT/'verification/reports/document-processing.json';path.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8')
    md='# Official document processing\n\n'+('\n'.join(f'- {key}: {report.get(key)}' for key in ('generated_at','snapshot_processing','national_coverage','freshness','all_complete','required_sources','required_jurisdictions','integrated_items','bulletin_index_pending','consolidated_index_pending','files_verified')))+'\n\nSee document-processing.json for source/period blockers.\n'
    path.with_suffix('.md').write_text(md,encoding='utf-8');print(json.dumps({k:report[k] for k in report if k not in {'blockers','periods','file_errors'}}))
    return 2 if 'operational_error' in report else 0 if report['all_complete'] else 1
if __name__=='__main__':raise SystemExit(main())
