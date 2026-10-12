import hashlib
from bs4 import BeautifulSoup


def directory_sources(content):
    soup=BeautifulSoup(content,"html.parser")
    sources=[{"id":"BOE_CONSOLIDATED","name":"BOE · Legislación consolidada","official_url":"https://www.boe.es/datosabiertos/api/api.php",
          "terms_url":"https://www.boe.es/informacion/aviso_legal/","adapter":"boe","audit_status":"pending"}]
    seen=set()
    for category in ("boletines_autonomicos","boletines_provinciales"):
        section=soup.find(id=category)
        if section is None:raise ValueError("BOE directory layout changed")
        for link in section.select("a[href]"):
            url=link["href"]
            if not url.startswith(("https://","http://")) or url in seen:continue
            seen.add(url)
            sources.append({"id":"DIRECTORY_"+hashlib.sha256(url.encode()).hexdigest()[:16],
                "name":link.get_text(" ",strip=True),"official_url":url,"terms_url":"","adapter":None,"audit_status":"pending"})
    return sources


def get_adapter(source_id):
    if source_id=='DOGC_NORMATIVE':
        from .dogc import DOGCAdapter
        return DOGCAdapter()
    if source_id=='DOG_GENERAL':
        from .dog import DOGAdapter
        return DOGAdapter()
    if source_id=="BOE_CONSOLIDATED":
        from .boe import BOEAdapter
        return BOEAdapter()
    raise ValueError("Source-specific audited adapter is not implemented: "+source_id)
