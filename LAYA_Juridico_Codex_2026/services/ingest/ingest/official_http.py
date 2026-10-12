"""Bounded public-source transport; exact allowlist, verified TLS, no private content."""
import os,subprocess,time
from urllib.parse import urlparse,urljoin
import httpx


class OfficialHTTP:
    def __init__(self,hosts,max_bytes=16*1024*1024):
        self.hosts=frozenset(hosts);self.max_bytes=max_bytes
        self.client=httpx.Client(timeout=60,trust_env=False,follow_redirects=False,headers={'User-Agent':'LAYA-Juridico-source-audit/0.1'})
    def get(self,url,params=None):
        if params:url=str(httpx.URL(url,params=params))
        for _ in range(6):
            parsed=urlparse(url)
            if parsed.scheme not in {'http','https'} or parsed.hostname not in self.hosts or parsed.username or parsed.password:
                raise ValueError('Official source boundary violation')
            try:
                with self.client.stream('GET',url) as r:
                    body=bytearray()
                    for block in r.iter_bytes():
                        body.extend(block)
                        if len(body)>self.max_bytes:raise ValueError('Official response exceeds budget')
                    headers={k:v for k,v in r.headers.items() if k.lower() not in {'content-encoding','content-length','transfer-encoding'}}
                    response=httpx.Response(r.status_code,headers=headers,content=bytes(body),request=r.request)
            except httpx.ConnectError:
                if os.name!='nt':raise
                # Windows Schannel supports official servers incompatible with OpenSSL.
                # Certificate verification remains enabled. No cookies or external credentials.
                command=['curl.exe','--silent','--include','--connect-timeout','10','--max-time','60',url]
                child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                data=child.stdout.read(self.max_bytes+65537)
                if len(data)>self.max_bytes+65536:child.kill();child.wait();raise ValueError('Official response exceeds budget')
                if child.wait(timeout=65)!=0:raise RuntimeError('Native official transport failed')
                headers,separator,body=data.partition(b'\r\n\r\n')
                if not separator or len(headers)>65536 or len(body)>self.max_bytes:raise ValueError('Invalid official transport envelope')
                lines=headers.split(b'\r\n');code=int(lines[0].split()[1])
                pairs=[line.split(b':',1) for line in lines[1:] if b':' in line]
                response=httpx.Response(code,headers=[(k.strip(),v.strip()) for k,v in pairs],content=body,request=httpx.Request('GET',url))
            if response.is_redirect:
                url=urljoin(url,response.headers.get('location',''));continue
            response.raise_for_status();time.sleep(.25);return response
        raise ValueError('Official redirect budget exhausted')
    def close(self):self.client.close()
