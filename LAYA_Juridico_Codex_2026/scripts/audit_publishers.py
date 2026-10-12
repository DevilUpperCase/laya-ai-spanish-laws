"""Capture every directory publisher's entry point. Reachability is not coverage approval."""
import concurrent.futures,hashlib,json,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from services.ingest.ingest.source_registry import directory_sources
from services.ingest.ingest.official_http import OfficialHTTP


def inspect(source):
    host=urlsplit(source['official_url']).hostname
    client=OfficialHTTP({host,'www.'+host if not host.startswith('www.') else host[4:]},max_bytes=4*1024*1024)
    report={**source,'captured_at':datetime.now(timezone.utc).isoformat(),'audit_status':'pending','coverage_verified':False}
    try:
        response=client.get(source['official_url']);body=response.content
        folder=ROOT/'sources/publisher-audits'/source['id'];folder.mkdir(parents=True,exist_ok=True)
        artifact=folder/'entry.html';artifact.write_bytes(body)
        report.update({'fetch_status':'captured','http_status':response.status_code,'artifact':str(artifact.relative_to(ROOT)),'sha256':hashlib.sha256(body).hexdigest()})
        soup=BeautifulSoup(body,'html.parser');feeds=[];terms=[];eli=[]
        for node in soup.select('a[href],link[href]'):
            href=urljoin(str(response.url),node['href']);text=node.get_text(' ',strip=True).lower()
            if urlsplit(href).scheme not in {'http','https'}:continue
            if 'rss' in href.lower() or node.get('type') in {'application/rss+xml','application/atom+xml'}:feeds.append(href)
            if any(t in text for t in ('aviso legal','avis legal','licencia','licència','reutiliza','condiciones de uso')):terms.append(href)
            if '/eli' in href.lower():eli.append(href)
        report.update({'feed_candidates':sorted(set(feeds))[:30],'terms_candidates':sorted(set(terms))[:20],'eli_candidates':sorted(set(eli))[:30],'limits':['Entry-point capture only. Historical inventory, normative selection, geographic coverage and reuse review remain required.']})
    except Exception as e:report.update({'fetch_status':'blocked','failure_code':type(e).__name__,'limits':['Resolve transport/redirect/source capability before enabling ingestion.']})
    finally:client.close()
    print(source['id'],report['fetch_status'],flush=True)
    return report


def main():
    sources=directory_sources((ROOT/'sources/snapshots/boe-directory.html').read_bytes())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:reports=list(pool.map(inspect,sources))
    path=ROOT/'verification/reports/publisher-audits.json';path.write_text(json.dumps({'generated_at':datetime.now(timezone.utc).isoformat(),'status':'audit_pending','sources':reports},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Captured',sum(r['fetch_status']=='captured' for r in reports),'of',len(reports),'publisher entry points; zero completeness approvals.')


if __name__=='__main__':main()
