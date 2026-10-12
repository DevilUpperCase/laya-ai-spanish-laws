"""Daily supported-source reconciliation and fail-closed nationwide processing check."""
import argparse,json,subprocess,sys,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.runtime_lock import RuntimeLock

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-only',action='store_true');parser.add_argument('--verify-files',action='store_true');args=parser.parse_args()
    results=[];env=os.environ.copy();env['PYTHONUTF8']='1'
    with RuntimeLock(ROOT/'private-data/runtime/daily-documents.lock'):
        scripts=[] if args.check_only else ['sync_boe.py','sync_bulletins.py']
        for filename in scripts+['check_document_processing.py']:
            command=[sys.executable,str(ROOT/'scripts'/filename)]
            if filename=='check_document_processing.py' and args.verify_files:command+=['--verify-files']
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=0x08000000 if os.name=='nt' else 0)
            results.append({'script':filename,'exit_code':result.returncode})
        report={'generated_at':datetime.now(timezone.utc).isoformat(),'checks':results,'national_complete':False,'status':'blocked' if any(r['exit_code'] for r in results) else 'checked'}
        (ROOT/'verification/reports/daily-documents.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    # Coverage blockers must not turn into a 10-minute ingestion retry storm.
    return 2 if any(r['exit_code']>=2 for r in results) else 0
if __name__=='__main__':raise SystemExit(main())
