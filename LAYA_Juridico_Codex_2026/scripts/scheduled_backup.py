"""Daily local encrypted snapshot with coordinated private-service maintenance."""
import json,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.backup_local import snapshot,expire
from scripts.runtime_lock import RuntimeLock


def paused_snapshot():
    runtime=ROOT/'private-data/runtime'
    with RuntimeLock(runtime/'private-maintenance.lock'):
        if (runtime/'maintenance').exists():raise RuntimeError('Existing operator maintenance; scheduled snapshot deferred')
        subprocess.run([sys.executable,str(ROOT/'scripts/local_stack.py'),'pause'],check=True,stdout=subprocess.DEVNULL)
        try:
            for _ in range(45):
                status=json.loads((runtime/'status.json').read_text())
                if all(status['services'][s]['state']=='paused' for s in ('api','worker')):break
                time.sleep(2)
            else:raise RuntimeError('Private services did not pause')
            return snapshot()
        finally:subprocess.run([sys.executable,str(ROOT/'scripts/local_stack.py'),'resume'],check=True,stdout=subprocess.DEVNULL)


def main():
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'scope':'local_encrypted_snapshots','status':'failed'}
    try:
        folder=paused_snapshot();report.update({'status':'passed','snapshot':folder.name,'limitations':['Off-host encrypted replication, key custody and elapsed retention evidence remain pending.']})
    except Exception as error:report['failure_code']=type(error).__name__
    # Retention is independent of whether today's snapshot succeeded.
    try:
        report['expired_snapshots']=expire()
        retention=json.loads((ROOT/'verification/reports/backup-retention.json').read_text())
        if retention['requires_operator_review']:report['status']='requires_operator_review'
    except Exception as error:report['retention_failure_code']=type(error).__name__;report['status']='failed'
    path=ROOT/'verification/reports/scheduled-backup.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print('Scheduled backup:',report['status'])
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
