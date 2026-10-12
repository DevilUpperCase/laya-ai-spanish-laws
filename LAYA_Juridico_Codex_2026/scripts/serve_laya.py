"""Serve only the hash-verified local multilingual decision checkpoint."""
import os
from pathlib import Path
import sys
import json
import hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
from services.api.app.config import Settings


if __name__=="__main__":
    settings=Settings()
    if not settings.laya_api_key:raise ValueError("LAYA bearer secret required")
    manifest=json.loads((ROOT/"verification/model-artifacts.json").read_text())["laya"]
    if manifest["revision"]!=settings.laya_model_revision:raise ValueError("LAYA checkpoint revision mismatch")
    checkpoint=ROOT/"model-cache/laya/multilingual"
    for name,digest in manifest["files"].items():
        path=(ROOT/"model-cache/laya"/name).resolve()
        if not path.is_relative_to((ROOT/"model-cache/laya").resolve()):raise ValueError("Unsafe artifact path")
        h=hashlib.sha256()
        with path.open("rb") as f:
            while b:=f.read(1024*1024):h.update(b)
        if h.hexdigest()!=digest:raise ValueError("LAYA artifact hash mismatch")
    os.environ["LAYA_API_KEY"]=settings.laya_api_key
    os.environ["LAYA_MODELS"]="juridico"
    os.environ["LAYA_DEFAULT_MODEL"]="juridico"
    os.environ["LAYA_JEV_STRICT"]="0"
    os.environ["LAYA_MAX_CONCURRENT"]="2"
    import torch
    torch.set_num_threads(4)
    from laya import Router
    from laya.serve import create_app
    import uvicorn
    router=Router(device="cpu",models={"juridico":str(checkpoint)},default="juridico",revision=settings.laya_model_revision)
    router.preload(["juridico"])
    # Upstream local-path loads have no Hub snapshot revision. Attach the revision
    # whose complete artifact hashes we verified above, for authenticated health.
    router.load("juridico").revision=settings.laya_model_revision
    # Disable upstream exception propagation: errors may include private inference input.
    import logging
    logging.getLogger("laya.serve").disabled=True
    uvicorn.run(create_app(router),host="127.0.0.1",port=8001,access_log=False,log_level="warning")
