"""Install pinned official local Tesseract language data; never remote OCR."""
import hashlib
import json
import re
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1]


if __name__=="__main__":
    manifest_path=ROOT/"verification/ocr-artifacts.json"
    existing=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    with httpx.Client(trust_env=False,timeout=90,headers={"User-Agent":"LAYA-Juridico-local-OCR/0.1"}) as client:
        if existing:revision=existing["revision"]
        else:
            response=client.get("https://api.github.com/repos/tesseract-ocr/tessdata_fast/commits/main")
            response.raise_for_status();revision=response.json()["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}",revision):raise ValueError("Immutable OCR revision required")
        root=ROOT/"model-cache/ocr";root.mkdir(parents=True,exist_ok=True)
        files={}
        for name in ("spa.traineddata","cat.traineddata","eus.traineddata","glg.traineddata","LICENSE"):
            url="https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/"+revision+"/"+name
            response=client.get(url);response.raise_for_status()
            if len(response.content)>32*1024*1024:raise ValueError("OCR artifact limit")
            digest=hashlib.sha256(response.content).hexdigest()
            if existing and existing["files"].get(name)!=digest:raise ValueError("Pinned OCR artifact changed")
            (root/name).write_bytes(response.content);files[name]=digest
        manifest={"repo":"tesseract-ocr/tessdata_fast","revision":revision,"files":files,"license_review":"pending"}
        manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    path=ROOT/".env"
    lines=[line for line in path.read_text().splitlines() if not line.startswith(("OCR_ENABLED=","OCR_MODEL_REVISION="))]
    path.write_text("\n".join(lines+["OCR_ENABLED=true","OCR_MODEL_REVISION="+revision])+"\n")
    print("Local OCR language artifacts pinned and enabled. Restart API/worker. License review pending.")
