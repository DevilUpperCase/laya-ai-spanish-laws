import asyncio
import time
import httpx
from langchain_core.runnables import RunnableLambda
from .contracts import Decision

QUESTIONS = {"relevance":{"type":"choice","instructions":"Clasifica la relación temática. No determines aplicabilidad ni vigencia jurídica.",
    "criteria":{"none":"No aborda la consulta.","partial":"Tema relacionado indirectamente.","direct":"Aborda directamente la consulta."}}}


class LayaClient:
    def __init__(self, settings, *, transport=None):
        self.settings = settings
        self.client = httpx.AsyncClient(base_url=settings.laya_base_url, timeout=settings.laya_timeout_seconds,
                      transport=transport, headers={"Authorization":"Bearer " + settings.laya_api_key}, trust_env=False)
        self.failures = 0
        self.open_until = 0.0
        self.half_open = False
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(2)
        self.runnable = RunnableLambda(self._invoke)

    async def _invoke(self, data):
        return await self.classify(data["query"],data["candidates"])

    async def classify(self, query, candidates):
        if not candidates:
            return []
        if not self.settings.laya_api_key:
            raise RuntimeError("LAYA credentials missing")
        async with self.lock:
            now = time.monotonic()
            if self.open_until > now or self.half_open:
                raise RuntimeError("LAYA circuit open")
            if self.open_until:
                self.half_open = True
        started = time.monotonic()
        states = [f"CONSULTA: {query}\nTÍTULO: {c.heading}\nTERRITORIO: {c.jurisdiction_code}\nEXTRACTO: {c.passage}" for c in candidates]
        payload = {"states":states,"questions":QUESTIONS,"model":"juridico","max_len":2048,"min_confidence":0.0,"batch_size":8}
        try:
            async with asyncio.timeout(self.settings.laya_timeout_seconds):
                async with self.semaphore:
                    for attempt in range(2):
                        try:
                            response = await self.client.post("/v1/systemone/batch",json=payload)
                            response.raise_for_status()
                            break
                        except (httpx.TransportError,httpx.HTTPStatusError) as error:
                            transient = not isinstance(error,httpx.HTTPStatusError) or error.response.status_code in {502,503,504}
                            if not transient or attempt:
                                raise
                            await asyncio.sleep(0.05)
                    body = response.json()
                    if not isinstance(body,dict):raise ValueError("Invalid batch envelope")
                    rows = body["results"]
                    if not isinstance(rows,list) or len(rows) != len(candidates):
                        raise ValueError("Invalid batch cardinality")
                    decisions = []
                    for candidate,row in zip(candidates,rows):
                        if not isinstance(row,dict) or not isinstance(row.get("answers"),dict):raise ValueError("Invalid answer envelope")
                        answer = row["answers"]["relevance"]
                        if not isinstance(answer,dict) or not isinstance(row.get("usage",{}),dict):raise ValueError("Invalid answer/usage metadata")
                        if row.get("usage",{}).get("output_tokens",0) != 0:
                            raise ValueError("Unexpected generation")
                        truncated = row.get("usage",{}).get("truncated")
                        if truncated is not None and type(truncated) is not bool:
                            raise ValueError("Invalid truncation metadata")
                        abstention = answer.get("abstention")
                        if abstention not in {None,"passed","abstained","unevaluated"}:
                            raise ValueError("Invalid abstention state")
                        decisions.append(Decision(candidate_id=candidate.candidate_id,label=answer["choice"],probabilities=answer["probabilities"],
                            answer_confidence=answer.get("answer_confidence"),abstained=False if abstention=="passed" else True if abstention=="abstained" else None,
                            truncated=truncated,model_revision=self.settings.laya_model_revision or "unverified",latency_ms=(time.monotonic()-started)*1000))
            async with self.lock:
                self.failures,self.open_until,self.half_open = 0,0.0,False
            return decisions
        except asyncio.CancelledError:
            async with self.lock:
                self.half_open = False
            raise
        except (httpx.HTTPError,ValueError,KeyError,TypeError,TimeoutError) as error:
            async with self.lock:
                self.failures += 1
                self.half_open = False
                if self.failures >= self.settings.laya_circuit_failures:
                    self.open_until = time.monotonic()+self.settings.laya_circuit_open_seconds
            raise RuntimeError("LAYA unavailable or malformed") from None

    async def close(self):
        await self.client.aclose()
