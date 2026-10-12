from datetime import date
import hashlib
import re
import time
from urllib.parse import urlparse
from defusedxml.ElementTree import fromstring
import httpx
from .contracts import PublicationRef, RawPublication, SectionVersion, ParsedPublication, DiscoveryPage
from pathlib import Path
import json
from datetime import datetime,timezone

BASE = "https://www.boe.es/datosabiertos/api/legislacion-consolidada"
OFFICIAL_ID = r"[A-Z]{2,8}-[A-Za-z]-\d{4}-\d+"


def official_date(value: str | None, *, allow_unknown=False) -> date | None:
    if not value:
        return None
    try:return date.fromisoformat(value[:4] + "-" + value[4:6] + "-" + value[6:8])
    except ValueError:
        if allow_unknown:return None
        raise


def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def plain_text(version) -> str:
    # Plain-text representation is fixed; original XML is retained separately.
    return "\n".join("".join(node.itertext()).strip() for node in list(version) if "".join(node.itertext()).strip())


class BOEAdapter:
    source_id = "BOE_CONSOLIDATED"

    def __init__(self, *, page_size: int = 50,max_record_bytes=128*1024*1024):
        self.page_size = page_size
        self.max_record_bytes=max_record_bytes
        self.client = httpx.Client(timeout=60, follow_redirects=False, headers={"Accept": "application/xml"})

    def _get(self, url, params=None):
        if urlparse(url).hostname != "www.boe.es":
            raise ValueError("Unexpected source host")
        for attempt in range(3):
            try:
                with self.client.stream("GET", url, params=params) as response:
                    response.raise_for_status()
                    content = bytearray()
                    for block in response.iter_bytes():
                        content.extend(block)
                        if len(content) > self.max_record_bytes:
                            raise ValueError("Official record exceeds parser budget")
                    root = fromstring(bytes(content))
                    code = root.findtext("./status/code")
                    if code and code != "200":
                        raise ValueError("Source status is not success")
                    time.sleep(0.2)
                    return bytes(content)
            except (httpx.TransportError, httpx.HTTPStatusError) as error:
                if isinstance(error, httpx.HTTPStatusError) and error.response.status_code not in {429, 500, 502, 503, 504}:
                    raise
                if attempt == 2:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def discover(self, start_date=None, end_date=None, cursor=None):
        offset = int((cursor or {}).get("offset", 0))
        params = {"offset": offset, "limit": self.page_size}
        if start_date:
            params["from"] = start_date.strftime("%Y%m%d")
        if end_date:
            params["to"] = end_date.strftime("%Y%m%d")
        root = fromstring(self._get(BASE, params))
        items = root.findall("./data/item")
        refs = []
        for item in items:
            identifier = item.findtext("identificador", "")
            if not re.fullmatch(OFFICIAL_ID, identifier):
                raise ValueError("Unexpected official identifier: "+identifier)
            refs.append(PublicationRef(self.source_id, identifier, BASE + "/id/" + identifier,
                                       official_date(item.findtext("fecha_publicacion"))))
        return DiscoveryPage(tuple(refs), {"offset": offset + len(items)} if len(items) == self.page_size else None)

    def fetch(self, ref):
        return RawPublication(ref, self._get(ref.official_url))

    def parse(self, raw):
        dates={}
        root=fromstring(raw.content)
        for version in root.findall('./data/texto/bloque/version'):
            try:official_date(version.get('fecha_publicacion'))
            except ValueError:
                norm=version.get('id_norma','')
                if not re.fullmatch(OFFICIAL_ID,norm):raise ValueError('Date correction has no official identity')
                if norm in dates:continue
                url='https://www.boe.es/diario_boe/xml.php?id='+norm
                original=self._get(url)
                meta=fromstring(original).find('./metadatos')
                if meta is None or meta.findtext('identificador')!=norm:raise ValueError('Date evidence identity mismatch')
                dates[norm]=official_date(meta.findtext('fecha_publicacion'))
                if dates[norm] is None:raise ValueError('No verified publication date')
                folder=Path(__file__).resolve().parents[3]/'sources/snapshots/date-evidence'
                folder.mkdir(parents=True,exist_ok=True)
                (folder/(norm+'.xml')).write_bytes(original)
                evidence={'url':url,'sha256':digest(original),'captured_at':datetime.now(timezone.utc).isoformat(),'date':dates[norm].isoformat(),'correction_of':raw.ref.external_id,'raw_value':version.get('fecha_publicacion')}
                (folder/(norm+'.json')).write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
        return self.parse_xml(raw.content, raw.ref.official_url,publication_dates=dates)

    @staticmethod
    def parse_xml(content: bytes, url: str, *, publication_dates=None):
        root = fromstring(content)
        meta = root.find("./data/metadatos")
        if meta is None or root.find("./data/texto") is None:
            raise ValueError("Missing consolidated metadata/text")
        identifier = meta.findtext("identificador", "")
        if not re.fullmatch(OFFICIAL_ID, identifier):
            raise ValueError("Unknown instrument identity")
        published = official_date(meta.findtext("fecha_publicacion"))
        official_url = meta.findtext("url_html_consolidada", "")
        if urlparse(official_url).hostname != "www.boe.es" or published is None:
            raise ValueError("Missing official provenance")
        versions = []
        for ordinal, block in enumerate(root.findall("./data/texto/bloque")):
            section_key = block.get("id")
            if not section_key:
                raise ValueError("Section identity missing")
            heading = block.get("titulo") or section_key
            for source_order,version in enumerate(block.findall("version")):
                text = plain_text(version)
                if not text:
                    continue
                try:version_pub = official_date(version.get("fecha_publicacion"))
                except ValueError:
                    version_pub=(publication_dates or {}).get(version.get('id_norma'))
                    if not isinstance(version_pub,date):raise ValueError('Version date requires official evidence') from None
                if version_pub is None:
                    raise ValueError("Version publication date missing")
                version_ref = (version.get("id_norma") or identifier) + ":" + version_pub.isoformat()
                hashed = digest(text)
                version_id = digest(identifier + ":" + section_key + ":" + version_ref + ":" + hashed)
                versions.append(SectionVersion(version_id, section_key, heading, ordinal, version_ref,
                                version_pub, version_pub, official_date(version.get("fecha_vigencia"),allow_unknown=True), text, hashed,source_order=source_order))
        if not versions:
            raise ValueError("Empty consolidated record")
        relationships = tuple((r.findtext("id_norma"), r.findtext("relacion")) for r in root.findall("./data/analisis/referencias/anteriores/anterior") if r.findtext("id_norma") and r.findtext("relacion"))
        return ParsedPublication(identifier, meta.findtext("titulo"), meta.findtext("rango"), published,
               meta.findtext("numero_oficial") or identifier, official_url, meta.findtext("url_eli"),
               meta.findtext("ambito"), meta.findtext("departamento"), meta.findtext("fecha_actualizacion"), tuple(versions), relationships)

    def healthcheck(self):
        page = self.discover(cursor={"offset": 0})
        return {"status": "ok" if page.publications else "empty", "scope": "consolidated catalogue only"}

    def close(self):
        self.client.close()
