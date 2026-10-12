"""An adapter to use the real NandhaKishorM/laya as an OPTIONAL candidate classifier.

This module has no dependency on a live LAYA checkpoint until the caller supplies
an actual Router. It does NOT prove legal applicability, validity or correctness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class BatchRouter(Protocol):
    def predict_batch(self, requests: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class Candidate:
    id: str
    heading: str
    passage: str
    jurisdiction: str = "unknown"


RELEVANCE_QUESTION = {
    "relevance": {
        "type": "choice",
        "instructions": (
            "Classifica la relacion tematica del extracto normativo con la consulta. "
            "Esto NO determina si la norma se aplica juridicamente al asunto."
        ),
        "criteria": {
            "none": "El texto no responde al tema de la consulta.",
            "partial": "El texto toca un concepto parecido pero no responde de forma directa.",
            "direct": "El texto aborda directamente el tema preguntado.",
        },
    },
}


def score_candidates(query: str, candidates: list[Candidate], router: BatchRouter,
                     *, batch_size: int = 8) -> list[dict[str, Any]]:
    """Returns candidate ids + provisional LAYA class/probabilities, same input order.

    Never use this output alone as a legal relevance threshold. Train/evaluate
    on labeled Spanish legal tasks before incorporating it into production rank.
    """
    requests = []
    for cand in candidates:
        # Do NOT attach full confidential documents, only a selected short excerpt.
        state = (
            f"CONSULTA: {query[:3000]}\n"
            f"TÍTULO: {cand.heading[:1000]}\n"
            f"TERRITORIO: {cand.jurisdiction[:80]}\n"
            f"EXTRACTO: {cand.passage[:6000]}"
        )
        requests.append({
            "state": state,
            "questions": RELEVANCE_QUESTION,
            "model": "multilingual",
            "max_len": 2048,
        })
    if not requests:
        return []
    responses = router.predict_batch(requests, batch_size=batch_size)
    if len(responses) != len(candidates):
        raise RuntimeError("LAYA devolvió un número incorrecto de decisiones")
    out = []
    for cand, res in zip(candidates, responses):
        ans = res["answers"]["relevance"]
        label = ans["choice"]
        if label not in RELEVANCE_QUESTION["relevance"]["criteria"]:
            raise RuntimeError("LAYA devolvió clase no reconocida")
        out.append({
            "candidate_id": cand.id,
            "class": label,
            "probabilities": dict(ans.get("probabilities", {})),
            "answer_confidence": ans.get("answer_confidence"),
            "truncated": bool(res.get("usage", {}).get("truncated", False)),
        })
    return out


def rrf(rank_lists: list[list[str]], *, k: int = 60) -> list[tuple[str, float]]:
    """Deterministic reciprocal rank fusion over *unique* candidate IDs."""
    if k <= 0:
        raise ValueError("k must be positive")
    scores: dict[str, float] = {}
    for ids in rank_lists:
        for rank, item_id in enumerate(dict.fromkeys(ids), start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
