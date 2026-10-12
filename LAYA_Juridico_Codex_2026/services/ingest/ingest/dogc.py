"""Official DOGC normative catalogue, Spanish/Catalan original Akoma Ntoso texts.

The published catalogue's scope excludes many local acts. Complete historical
versions and binary annexes remain explicit source-audit obligations.
"""
from datetime import date
import html,json,re
from urllib.parse import urlparse
from defusedxml.ElementTree import fromstring
from xml.etree.ElementTree import ParseError
import httpx
from bs4 import BeautifulSoup
from .official_http import OfficialHTTP
from .contracts import PublicationRef,RawPublication,SectionVersion,ParsedPublication,DiscoveryPage
from .boe import digest

API='https://analisi.transparenciacatalunya.cat/resource/n6hn-rmy7.json'
NS={'a':'http://docs.oasis-open.org/legaldocml/ns/akn/3.0'}


def parse_akoma(content,row,language):
    root=fromstring(content)
    if root.tag!='{'+NS['a']+'}akomaNtoso':raise ValueError('Official Akoma Ntoso schema missing')
    published=date.fromisoformat(row['data_de_publicaci_del_diari'][:10]);identifier='DOGC-'+row['n_mero_de_control']
    versions=[];warnings=['AVAILABLE_HISTORY_NOT_RECONCILED']
    url=row['format_html' if language=='ca' else 'url_es_formato_html']['url']
    if urlparse(url).hostname not in {'portaljuridic.gencat.cat','portaldogc.gencat.cat'}:raise ValueError('Unexpected official document host')
    for ordinal,container in enumerate(root.findall('./a:act/a:body/a:hcontainer',NS)):
        heading=container.findtext('a:heading','',NS).strip() or 'Fragment '+str(ordinal+1)
        contents=container.findall('a:content',NS);parts=[]
        for node in contents:
            encoded=node.get('period') or ''.join(node.itertext())
            decoded=html.unescape(encoded)
            soup=BeautifulSoup(decoded,'html.parser')
            if soup.find('a',href=True) or '(Vegeu la imatge' in soup.get_text():warnings.append('OFFICIAL_ANNEXES_NOT_INDEXED')
            for hostile in soup.select('script,style'):hostile.decompose()
            text=soup.get_text('\n',strip=True)
            if text:parts.append(text)
        text='\n'.join(parts)
        if not text:continue
        key=language+':fragment:'+str(ordinal);sha=digest(text);version_ref=published.isoformat()+':'+language+':original'
        versions.append(SectionVersion(digest(identifier+key+sha),key,heading,ordinal,version_ref,published,published,None,text,sha,language_code=language,official_url=url))
    if not versions:raise ValueError('No official body text')
    return tuple(versions),tuple(sorted(set(warnings)))


class DOGCAdapter:
    source_id='DOGC_NORMATIVE'
    inherent_gaps=('AVAILABLE_HISTORY_NOT_RECONCILED','BINARY_ANNEXES_NOT_RECONCILED')
    def __init__(self,page_size=50):
        self.page_size=page_size
        self.known_ids=set()
        self.http=OfficialHTTP({'analisi.transparenciacatalunya.cat','portaljuridic.gencat.cat','portaldogc.gencat.cat'})
    def discover(self,start_date=None,end_date=None,cursor=None):
        offset=int((cursor or {}).get('offset',0));params={'$limit':self.page_size,'$offset':offset,'$order':'n_mero_de_control'}
        clauses=[]
        if start_date:clauses.append("data_de_publicaci_del_diari >= '"+start_date.isoformat()+"T00:00:00'")
        if end_date:clauses.append("data_de_publicaci_del_diari <= '"+end_date.isoformat()+"T23:59:59'")
        if clauses:params['$where']=' AND '.join(clauses)
        rows=self.http.get(API,params).json();refs=[]
        for row in rows:
            if not re.fullmatch(r'[0-9A-Z-]{1,32}',row.get('n_mero_de_control','')):raise ValueError('Unknown official DOGC identity')
            if 'DOGC-'+row['n_mero_de_control'] in self.known_ids:continue
            refs.append(PublicationRef(self.source_id,'DOGC-'+row['n_mero_de_control'],str(__import__('httpx').URL(API,params={'n_mero_de_control':row['n_mero_de_control']})),date.fromisoformat(row['data_de_publicaci_del_diari'][:10])))
        return DiscoveryPage(tuple(refs),{'offset':offset+len(rows)} if len(rows)==self.page_size else None)
    def fetch(self,ref):
        rows=self.http.get(ref.official_url).json()
        if len(rows)!=1:raise ValueError('DOGC identity not unique')
        row=rows[0];documents={};urls={};failures={}
        for language,key in [('ca','url_format_xml'),('es','url_es_format_xml')]:
            try:
                urls[language]=row[key]['url'];response=self.http.get(urls[language]);documents[language]=response.content.decode('utf-8')
            except (KeyError,ValueError,RuntimeError,httpx.HTTPError) as error:
                documents[language]='';failures[language]=type(error).__name__
        return RawPublication(ref,json.dumps({'metadata':row,'documents':documents,'urls':urls,'language_failures':failures},ensure_ascii=False).encode('utf-8'),format='json')
    def parse(self,raw):
        bundle=json.loads(raw.content);row=bundle['metadata'];versions=[];warnings=[]
        for language,content in bundle['documents'].items():
            try:parsed,limits=parse_akoma(content.encode('utf-8'),row,language)
            except (ParseError,ValueError):warnings.append('OFFICIAL_TRANSLATION_MISSING');continue
            versions.extend(parsed);warnings.extend(limits)
        if not versions:raise ValueError('No available official XML body text in either language')
        url=row['format_html']['url'];eli=url.split('/dof/')[0]
        return ParsedPublication(raw.ref.external_id,row['t_tol_de_la_norma'],row['rang_de_norma'],raw.ref.publication_date,'DOGC '+row['n_mero_de_diari']+' / '+row['n_mero_de_control'],url,eli,'Autonómico','Comunidad Autónoma de Cataluña',None,tuple(versions),is_consolidated=False,ingestion_warnings=tuple(sorted(set(warnings))))
    def close(self):self.http.close()
