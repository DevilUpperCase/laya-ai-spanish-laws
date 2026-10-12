"""Reviewed publication manifests for publishers without an audited discovery adapter.

Imports only enumerated normative HTML/PDFs. It cannot certify archive completeness.
"""
import hashlib,ipaddress,json,re,subprocess,sys,tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .contracts import PublicationRef,RawPublication,SectionVersion,ParsedPublication,DiscoveryPage
from .official_http import OfficialHTTP
from .boe import digest


def load_manifest(path,root):
    path=Path(path).resolve();root=Path(root).resolve()
    if not path.is_relative_to(root) or path.stat().st_size>8*1024*1024:raise ValueError('Manifest outside review directory or over budget')
    data=json.loads(path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[A-Z0-9_]{3,80}',data['source_id']):raise ValueError('Invalid source ID')
    evidence=(path.parent/data['review_evidence']).resolve()
    if not evidence.is_relative_to(root) or not evidence.is_file() or not str(data.get('reviewer') or '').strip() or hashlib.sha256(evidence.read_bytes()).hexdigest()!=data['review_sha256']:raise ValueError('Matching human review evidence required')
    hosts=set(data['allowed_hosts'])
    if not hosts:raise ValueError('Exact official hosts required')
    for host in hosts:
        if not isinstance(host,str) or not re.fullmatch(r'[a-z0-9.-]+',host) or '.' not in host or host.endswith(('.local','.localhost','.internal')):raise ValueError('Invalid official host')
        try:ipaddress.ip_address(host)
        except ValueError:continue
        raise ValueError('IP hosts prohibited for reviewed public sources')
    def check_url(url):
        parsed=urlparse(url)
        if parsed.scheme not in {'https','http'} or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in {None,80,443}:raise ValueError('Manifest official host boundary violation')
    check_url(data['official_url']);check_url(data['terms_url'])
    seen=set()
    for row in data['publications']:
        if row.get('normative') is not True:raise ValueError('Only explicitly reviewed normative publications allowed')
        check_url(row['official_url']);date.fromisoformat(row['publication_date'])
        if row.get('version_date'):date.fromisoformat(row['version_date'])
        if row['language'] not in {'es','ca','gl','eu'} or row['format'] not in {'html','pdf'}:raise ValueError('Unsupported language/format')
        if not row.get('title') or not row.get('jurisdiction_id') or not row.get('legal_type') or not row.get('external_id'):raise ValueError('Exact normative metadata required')
        identity=(row['external_id'],row['language'],row.get('version_date'),row['official_url'])
        if identity in seen:raise ValueError('Duplicate reviewed publication')
        seen.add(identity)
        if row['format']=='html' and not row.get('selector'):raise ValueError('Publisher-specific body selector required')
    return data


class ManifestAdapter:
    inherent_gaps=('ENUMERATED_MANIFEST_IS_NOT_COMPLETE_DISCOVERY','AVAILABLE_HISTORY_NOT_RECONCILED','BINARY_ANNEXES_NOT_RECONCILED')
    def __init__(self,data,settings):
        self.data=data;self.settings=settings;self.source_id=data['source_id'];self.http=OfficialHTTP(data['allowed_hosts'],max_bytes=20*1024*1024)
        self.rows={str(i):row for i,row in enumerate(data['publications'])}
    def close(self):self.http.close()
    def discover(self,start_date,end_date,cursor):
        if cursor:return DiscoveryPage((),None)
        refs=tuple(PublicationRef(self.source_id,key,row['official_url'],date.fromisoformat(row['publication_date'])) for key,row in self.rows.items() if (not start_date or date.fromisoformat(row['publication_date'])>=start_date) and (not end_date or date.fromisoformat(row['publication_date'])<=end_date))
        return DiscoveryPage(refs,None,len(refs))
    def fetch(self,ref):
        row=self.rows[ref.external_id];response=self.http.get(row['official_url'])
        if row.get('artifact_sha256') and digest(response.content)!=row['artifact_sha256']:raise ValueError('Official artifact changed after review')
        return RawPublication(ref,response.content,row['format'])
    def parse(self,raw):
        row=self.rows[raw.ref.external_id]
        if raw.format=='html':
            soup=BeautifulSoup(raw.content,'html.parser');nodes=soup.select(row['selector'])
            if len(nodes)!=1:raise ValueError('Reviewed body selector no longer uniquely matches')
            for element in nodes[0].select('script,style,nav'):element.decompose()
            text=nodes[0].get_text('\n',strip=True)
        else:
            # Reuse the bounded isolated extraction worker; no native PDF parsing in the ingest process.
            from services.api.app.documents import scan_upload
            if not scan_upload(raw.content,self.settings.clamav_host,self.settings.clamav_port):raise ValueError('Scanner required before official PDF extraction')
            with tempfile.TemporaryDirectory(prefix='laya-official-pdf-') as directory:
                path=Path(directory)/'official.pdf';path.write_bytes(raw.content)
                proc=subprocess.run([sys.executable,'-m','services.api.app.extract_worker',str(path),'application/pdf','300','2000000','0','spa+cat+eus+glg'],capture_output=True,timeout=90,cwd=Path(__file__).resolve().parents[3])
                if proc.returncode:raise ValueError('Official PDF extraction failed or needs audited OCR')
                pages=json.loads(proc.stdout);text='\n'.join(page['text'] for page in pages)
        if not text.strip() or len(text)>2_000_000:raise ValueError('Official body missing or over extraction budget')
        namespace=self.source_id+':'+digest(str(row['external_id']))[:24]
        published=raw.ref.publication_date;version_date=date.fromisoformat(row.get('version_date') or row['publication_date']);sha=digest(text)
        version=SectionVersion(namespace+':'+row['language']+':'+version_date.isoformat()+':'+sha,row['language']+':document','Documento publicado',0,version_date.isoformat(),published,version_date,None,text,sha,row['language'],official_url=row['official_url'])
        return ParsedPublication(str(row['external_id']),row['title'],row['legal_type'],published,row.get('official_reference',str(row['external_id'])),row['official_url'],row.get('eli'),'Reviewed manifest',row.get('issuer',''),None,(version,),is_consolidated=False,ingestion_warnings=('AVAILABLE_HISTORY_NOT_RECONCILED','OFFICIAL_ANNEXES_NOT_INDEXED'),instrument_id=namespace)
