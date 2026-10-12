"""Measure public-search latency on this host. Does not freeze release thresholds."""
import argparse,json,math,platform,sys,time
from datetime import datetime,timezone
from pathlib import Path
import httpx,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from evaluation.prepare_review import LANGUAGES


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repeats',type=int,default=2);args=p.parse_args()
    if not 1<=args.repeats<=10:raise ValueError('Repeat budget 1..10 required')
    session=json.loads((ROOT/'private-data/local-session.json').read_text())
    rows=[]
    with httpx.Client(base_url='http://127.0.0.1:8000',headers={'Authorization':'Bearer '+session['token'],'X-Tenant-ID':session['tenant_id']},trust_env=False,timeout=180) as client:
        for language in LANGUAGES:
            for topic in (LANGUAGES[language][0],LANGUAGES[language][1]):
                for repeat in range(args.repeats):
                    start=time.perf_counter()
                    try:
                        response=client.post('/v1/search',json={'query':topic});elapsed=(time.perf_counter()-start)*1000
                        body=response.json() if response.status_code==200 else {}
                        rows.append({'language':language,'query':topic,'repeat':repeat,'ms':round(elapsed,2),'http_status':response.status_code,'results':len(body.get('results',[])),'engines':body.get('engines'), 'warnings':body.get('warnings',[])})
                    except httpx.HTTPError as exc:rows.append({'language':language,'query':topic,'repeat':repeat,'http_status':None,'error':type(exc).__name__,'ms':round((time.perf_counter()-start)*1000,2)})
                    print(f'Pilot {len(rows)}/{8*args.repeats} complete.',flush=True)
    times=sorted(r['ms'] for r in rows)
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'measured_not_frozen','hardware':{'os':platform.platform(),'cpu':platform.processor(),'logical_cores':psutil.cpu_count(),'ram_bytes':psutil.virtual_memory().total},'workload':{'concurrency':1,'private_documents':False,'languages':list(LANGUAGES),'requests':len(rows),'background_indexing':True},'p95_ms':times[math.ceil(len(times)*.95)-1],'error_rate':sum(r['http_status']!=200 for r in rows)/len(rows),'requests':rows,'limitations':['Small development hardware pilot; no professionally reviewed relevance judgments, load acceptance, frozen performance policy or LAYA activation approval.','Background CPU indexing and partial vectors affect these measurements.']}
    (ROOT/'verification/reports/hardware-pilot.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Hardware pilot saved. Thresholds are not frozen.')


if __name__=='__main__':main()
