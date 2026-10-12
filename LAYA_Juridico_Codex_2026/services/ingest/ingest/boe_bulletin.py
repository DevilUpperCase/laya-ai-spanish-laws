"""BOE/BORME summary parsing with publisher category and original asset provenance."""
from datetime import datetime
from urllib.parse import urlparse
from defusedxml.ElementTree import fromstring

def official_url(value):
    parsed=urlparse(value)
    if parsed.scheme!='https' or parsed.hostname!='www.boe.es' or parsed.username or parsed.password:raise ValueError('Unexpected bulletin URL')
    return value

def parse_summary(content,source):
    root=fromstring(content)
    if root.findtext('./status/code')!='200':raise ValueError('Unsuccessful summary')
    summary=root.find('./data/sumario')
    if summary is None or summary.findtext('./metadatos/publicacion')!=source.upper():raise ValueError('Summary identity mismatch')
    day=datetime.strptime(summary.findtext('./metadatos/fecha_publicacion'),'%Y%m%d').date();items=[]
    for section in summary.findall('./diario/seccion'):
        for item in section.findall('.//item'):
            identifier=item.findtext('identificador')
            if not identifier or not identifier.startswith(source.upper()+'-'):raise ValueError('Missing item identity')
            pdf=item.findtext('url_pdf');xml=item.findtext('url_xml');html=item.findtext('url_html')
            if not pdf:raise ValueError('Summary item has no original PDF')
            items.append({'external_id':identifier,'title':item.findtext('titulo') or identifier,'pdf_url':official_url(pdf),
              'xml_url':official_url(xml) if xml else None,'official_url':official_url(html) if html else official_url(pdf),
              'category':section.get('nombre') or section.get('codigo') or 'unknown',
              'normative':source=='boe' and section.get('codigo')=='1'})
    if len({r['external_id'] for r in items})!=len(items):raise ValueError('Duplicate summary identities')
    return {'source':source,'date':day,'items':items}

def parse_item_xml(content,identifier):
    root=fromstring(content)
    meta=root.find('metadatos')
    if meta is None or meta.findtext('identificador')!=identifier:raise ValueError('Item metadata mismatch')
    text=root.find('texto')
    if text is None:return None
    result='\n'.join(''.join(n.itertext()).strip() for n in list(text) if ''.join(n.itertext()).strip())
    return result if result.strip() else None
