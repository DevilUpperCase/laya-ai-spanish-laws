import asyncio
import math
from pathlib import Path
import os
import json
from .config import ROOT
from .model_integrity import verify_artifacts


class EmbeddingClient:
    def __init__(self,settings):
        self.settings=settings
        self.model=None
        self.lock=asyncio.Lock()

    async def load(self):
        async with self.lock:
            if self.model is not None:return
            if not self.settings.embedding_model_revision or not (self.settings.embedding_model_path/"config.json").is_file():
                raise RuntimeError("Pinned local BGE-M3 artifacts unavailable")
            manifest=json.loads((ROOT/"verification/model-artifacts.json").read_text())["bge-m3"]
            await asyncio.to_thread(verify_artifacts,self.settings.embedding_model_path,manifest,self.settings.embedding_model_revision)
            os.environ["HF_HUB_OFFLINE"]="1"
            os.environ["TRANSFORMERS_OFFLINE"]="1"
            os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
            import torch
            torch.set_num_threads(self.settings.embedding_threads)
            from sentence_transformers import SentenceTransformer
            self.model=await asyncio.to_thread(SentenceTransformer,str(self.settings.embedding_model_path),device="cpu",local_files_only=True,trust_remote_code=False)
            self.model.max_seq_length=2048
            if self.model.get_embedding_dimension()!=1024:
                self.model=None
                raise RuntimeError("BGE-M3 dimension mismatch")

    async def embed(self,texts):
        await self.load()
        async with self.lock:
            vectors=await asyncio.to_thread(self.model.encode,texts,batch_size=self.settings.embedding_batch_size,normalize_embeddings=True,show_progress_bar=False)
        output=vectors.tolist()
        if len(output)!=len(texts) or any(len(v)!=1024 or any(not math.isfinite(x) for x in v) for v in output):
            raise RuntimeError("Invalid embedding output")
        return output
