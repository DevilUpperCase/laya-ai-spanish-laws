"""Smoke test with real LAYA weights. Run ONLY on own server after installing laya.

Requires internet only for FIRST checkpoint download unless cache is prepopulated.
No legal validity inference or latency promises.
"""
from laya import Router
from laya_adapter import Candidate, score_candidates


if __name__ == "__main__":
    router = Router()  # pin checkpoint/revision in production
    demo_query = "¿Cómo se computan los plazos en un procedimiento administrativo?"
    # Explicitly artificial passages, never use as real legal citations:
    candidates = [
        Candidate("demo-a", "[DEMO] Cómputo de plazos", "Se explica el cómputo de los plazos por días hábiles y naturales."),
        Candidate("demo-b", "[DEMO] Organización interna", "Se organiza la ubicación física de los archivos en una oficina."),
    ]
    for decision in score_candidates(demo_query, candidates, router):
        print(decision)
