"""Download immutable local inference artifacts and record file hashes. No remote inference."""
from pathlib import Path
import hashlib
import json
import os
import sys
import httpx

ROOT=Path(__file__).resolve().parents[1]
os.environ["HF_HOME"]=str(ROOT/"model-cache/hub")
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
os.environ["HF_HUB_DISABLE_XET"]="1"


def sha_file(path):
    hashed=hashlib.sha256()
    with path.open("rb") as f:
        while block:=f.read(1024*1024): hashed.update(block)
    return hashed.hexdigest()


def main():
    from huggingface_hub import snapshot_download
    models={}
    for alias,repo,patterns in (
        ("laya","convaiinnovations/laya",["multilingual/*","README.md"]),
        ("bge-m3","BAAI/bge-m3",["*.json","*.bin","*.model","1_Pooling/*","README.md"]),
    ):
        metadata=httpx.get("https://huggingface.co/api/models/"+repo,timeout=30).json()
        revision=metadata["sha"]
        if len(revision)!=40: raise ValueError("Immutable revision required")
        target=ROOT/"model-cache"/alias
        print("Downloading",alias,"revision",revision,flush=True)
        snapshot_download(repo,revision=revision,local_dir=target,allow_patterns=patterns,max_workers=2)
        files={str(p.relative_to(target)).replace("\\","/"):sha_file(p) for p in target.rglob("*") if p.is_file() and ".cache" not in p.parts}
        models[alias]={"repo":repo,"revision":revision,"files":files,"license_metadata":metadata.get("cardData",{}).get("license"),"license_review":"pending"}
    (ROOT/"verification/model-artifacts.json").write_text(json.dumps(models,indent=2)+"\n")
    env_path=ROOT/".env"
    content=env_path.read_text() if env_path.exists() else ""
    lines=[line for line in content.splitlines() if not line.startswith(("LAYA_MODEL_REVISION=","EMBEDDING_MODEL_REVISION="))]
    lines += ["LAYA_MODEL_REVISION="+models["laya"]["revision"],"EMBEDDING_MODEL_REVISION="+models["bge-m3"]["revision"]]
    env_path.write_text("\n".join(lines)+"\n")
    print("Pinned models downloaded; manifest contains file hashes. License review remains pending.")


if __name__=="__main__":main()
