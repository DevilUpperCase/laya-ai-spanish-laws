"""Prepare optional domain configuration; applying it is explicit and does not publish."""
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def profile(domain):
    domain=domain.strip().lower()
    if len(domain)>253 or '.' not in domain or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',domain):raise ValueError('A DNS hostname without scheme, port or path is required')
    return {'LAYA_DOMAIN':domain,'APP_ENV':'production','CORS_ORIGINS':json.dumps(['https://'+domain],separators=(',',':'))}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--domain',required=True);p.add_argument('--apply',action='store_true');args=p.parse_args();values=profile(args.domain)
    folder=ROOT/'private-data';folder.mkdir(exist_ok=True);(folder/'domain-config.json').write_text(json.dumps(values,indent=2)+'\n')
    if not args.apply:print('Domain profile prepared privately; local configuration is unchanged. See docs/HOSTING_GUIDE.md.');return
    from services.api.app.config import Settings
    Settings(app_env='production',cors_origins=json.loads(values['CORS_ORIGINS']))  # Validate existing secrets/pins without displaying them.
    env=ROOT/'.env'
    if not env.is_file():raise ValueError('Initialize this installation before applying a domain profile')
    content=env.read_text();lines=[line for line in content.splitlines() if line.split('=',1)[0] not in values]
    temporary=env.with_suffix('.domain.tmp');temporary.write_text('\n'.join(lines)+'\n'+''.join(k+'='+v+'\n' for k,v in values.items()));temporary.replace(env)
    print('Domain profile applied. Restart the API/web and run host Caddy with LAYA_DOMAIN set; no service was exposed by this command.')


if __name__=='__main__':main()
