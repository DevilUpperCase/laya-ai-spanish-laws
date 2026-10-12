"""Collect observed dependencies/license metadata and hashes, without approving reuse."""
import hashlib,importlib.metadata as metadata,json,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    rows=[]
    for distribution in sorted(metadata.distributions(),key=lambda d:(d.metadata.get('Name') or '').lower()):
        files=[]
        for entry in distribution.files or []:
            if ('dist-info/licenses/' in str(entry).replace('\\','/') or entry.name.upper().startswith(('LICENSE','COPYING','NOTICE'))) and not '..' in entry.parts:
                path=Path(distribution.locate_file(entry))
                if path.is_file():files.append({'artifact':str(entry),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        rows.append({'name':distribution.metadata['Name'],'version':distribution.version,'license':distribution.metadata.get('License-Expression') or distribution.metadata.get('License'),'license_artifacts':files,'approved':False})
    lock=json.loads((ROOT/'apps/web/package-lock.json').read_text());node=[{'path':key,'version':value.get('version'),'license':value.get('license'),'approved':False} for key,value in lock['packages'].items() if key]
    report={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'approval_pending','python':rows,'node':node,'models':json.loads((ROOT/'verification/model-artifacts.json').read_text()),'ocr':json.loads((ROOT/'verification/ocr-artifacts.json').read_text()),'container_configurations':['infra/compose.yaml','infra/auth.compose.yaml','infra/ops.compose.yaml'],'official_source_terms':'verification/reports/nationwide-coverage.json','reviewer':None,'limitations':['Metadata is not legal clearance. Every dependency, model, OCR artifact, container image and official-source reuse condition needs human approval.','PyMuPDF license choice requires explicit review before production distribution.']}
    (ROOT/'verification/reports/license-inventory.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Inventoried {len(rows)} Python distributions and {len(node)} Node packages; approvals pending.')


if __name__=='__main__':main()
