"""Galicia general-disposition RSS preview; never a complete historical archive."""
from datetime import date
from email.utils import parsedate_to_datetime
import json,re
from urllib.parse import urlparse
from defusedxml.ElementTree import fromstring
from bs4 import BeautifulSoup
from .official_http import OfficialHTTP
from .contracts import PublicationRef,RawPublication,SectionVersion,ParsedPublication,DiscoveryPage
from .boe import digest
from .jurisdiction_resolver import identity_tokens


def discover_feed(content):
    root=fromstring(content);rows=[]
    for item in root.findall('./channel/item'):
        url=item.findtext('link','');title=item.findtext('title','')
        match=re.fullmatch(r'/dog/Publicados/\d{4}/(\d{8})/(Anuncio[\w-]+)_(es|gl)\.html',urlparse(url).path)
        if not match:continue  # Excludes whole-issue PDFs and announcement indexes.
        tokens=identity_tokens(title)
        normative=title.upper().startswith(('LEY ','LEI ')) or bool({'regula','regulamento','reglamento'}&tokens)
        if not normative:continue  # Conservative preview rule; never a completeness claim.
        published=parsedate_to_datetime(item.findtext('pubDate')).date()
        if published.strftime('%Y%m%d')!=match[1]:raise ValueError('Official feed/URL publication-date mismatch')
        if urlparse(url).hostname!='www.xunta.gal':raise ValueError('Unexpected DOG publication host')
        rows.append({'id':'DOG-'+match[1]+'-'+match[2],'title':title,'url':url,'publication_date':published,'language':match[3]})
    return rows


def parse_html(content,row,language):
    soup=BeautifulSoup(content,'html.parser');body=soup.select_one('#audioid .story')
    if body is None:raise ValueError('Official DOG body selector missing')
    for node in body.select('script,style'):node.decompose()
    text=body.get_text('\n',strip=True)
    if not text:raise ValueError('Official DOG body empty')
    sha=digest(text);ref=row['publication_date'].isoformat()+':'+language+':original'
    return (SectionVersion(digest(row['id']+language+sha),language+':document',row['title'],0,ref,row['publication_date'],row['publication_date'],None,text,sha,language_code=language,official_url=row['url']),)


class DOGAdapter:
    source_id='DOG_GENERAL'
    inherent_gaps=('RSS_WINDOW_IS_NOT_AVAILABLE_HISTORY','CONSERVATIVE_NORMATIVE_RULE_REQUIRES_REVIEW','FEED_FRESHNESS_NOT_CERTIFIED')
    def __init__(self):self.http=OfficialHTTP({'www.xunta.gal'});self.records={}
    def discover(self,start_date=None,end_date=None,cursor=None):
        groups={}
        for language in ('es','gl'):
            rows=discover_feed(self.http.get('https://www.xunta.gal/diario-oficial-galicia/rss/Seccion1_'+language+'.rss').content)
            for row in rows:
                if start_date and row['publication_date']<start_date:continue
                if end_date and row['publication_date']>end_date:continue
                groups.setdefault(row['id'],{})[language]=row
        self.records=groups
        refs=[]
        for identifier,translations in groups.items():
            row=translations.get('es') or translations['gl']
            refs.append(PublicationRef(self.source_id,identifier,row['url'],row['publication_date']))
        return DiscoveryPage(tuple(refs),None)
    def fetch(self,ref):
        documents={};metadata={}
        for language,row in self.records[ref.external_id].items():
            response=self.http.get(row['url']);documents[language]=response.text;metadata[language]={**row,'publication_date':row['publication_date'].isoformat()}
        return RawPublication(ref,json.dumps({'documents':documents,'metadata':metadata},ensure_ascii=False).encode('utf-8'),format='json')
    def parse(self,raw):
        bundle=json.loads(raw.content);versions=[]
        for language,content in bundle['documents'].items():
            row=bundle['metadata'][language];row['publication_date']=date.fromisoformat(row['publication_date'])
            versions.extend(parse_html(content.encode('utf-8'),row,language))
        row=bundle['metadata'].get('es') or bundle['metadata']['gl']
        warnings=['AVAILABLE_HISTORY_NOT_RECONCILED']
        if set(bundle['documents'])!={'es','gl'}:warnings.append('OFFICIAL_TRANSLATION_MISSING')
        return ParsedPublication(raw.ref.external_id,row['title'],row['title'].split()[0],raw.ref.publication_date,raw.ref.external_id,row['url'],None,'Autonómico','Comunidad Autónoma de Galicia',None,tuple(versions),is_consolidated=False,ingestion_warnings=tuple(warnings))
    def close(self):self.http.close()
