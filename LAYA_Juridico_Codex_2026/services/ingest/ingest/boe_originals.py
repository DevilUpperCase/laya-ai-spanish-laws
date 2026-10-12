"""Capture original promulgated BOE PDFs using publisher-provided XML links."""
import hashlib,re
from pathlib import Path
from urllib.parse import urljoin,urlparse
from defusedxml.ElementTree import fromstring
from .official_http import OfficialHTTP

def pdf_url_from_xml(content,identifier):
    root=fromstring(content);meta=root.find('metadatos')
    if meta is None or meta.findtext('identificador')!=identifier:raise ValueError('Original identity mismatch')
    url=urljoin('https://www.boe.es',meta.findtext('url_pdf') or '')
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='www.boe.es' or parsed.username or parsed.password or not parsed.path.endswith('.pdf'):raise ValueError('No verified original PDF URL')
    return url

def archive_asset(conn,source_id,external_id,url,data,mime,root,kind='original_publication'):
    sha=hashlib.sha256(data).hexdigest();key='assets/'+sha
    path=Path(root)/key;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Archived asset corrupt')
    if not path.exists():path.write_bytes(data)
    asset_id=hashlib.sha256((source_id+'|'+external_id+'|'+url+'|'+sha).encode()).hexdigest()
    conn.execute('''INSERT INTO legal.publication_assets(id,source_id,external_id,official_url,mime_type,sha256,object_key,kind)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',(asset_id,source_id,external_id,url,mime,sha,key,kind))
    return asset_id

def capture_boe_original(identifier,destination,client,conn):
    if not re.fullmatch(r'BOE-[AB]-\d{4}-\d+',identifier):raise ValueError('Invalid BOE ID')
    xml=client.get('https://www.boe.es/diario_boe/xml.php?id='+identifier).content
    url=pdf_url_from_xml(xml,identifier);pdf=client.get(url).content
    if not pdf.startswith(b'%PDF-'):raise ValueError('Original is not a PDF')
    archive_asset(conn,'BOE_CONSOLIDATED',identifier,'https://www.boe.es/diario_boe/xml.php?id='+identifier,xml,'application/xml',destination,'original_metadata')
    return archive_asset(conn,'BOE_CONSOLIDATED',identifier,url,pdf,'application/pdf',destination)
