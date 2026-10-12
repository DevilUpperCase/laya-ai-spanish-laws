"""Deterministic evidence reasons. Illustrative subset for Codex; no language model.

Full product must normalize accents, tokenize multiple languages and ground spans in
original published text. This example returns only reasons it can directly verify.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Reason:
    kind: str
    message: str
    evidence: dict


def build_reasons(*, query: str, official_reference: str | None,
                  extracted_reference: str | None, matched_literal: str | None,
                  passage: str, selected_territory: str | None,
                  instrument_territory: str | None,
                  legal_status: str) -> list[dict]:
    """Do not claim applicability or legal force. Return grounded facts or warnings."""
    reasons: list[Reason] = []
    if (official_reference and extracted_reference and
        official_reference.upper() == extracted_reference.upper() and
        extracted_reference.upper() in query.upper()):
        reasons.append(Reason("exact_reference", "Coincide la referencia oficial indicada en tu consulta.",
                              {"reference": official_reference}))
    if matched_literal and matched_literal.casefold() in passage.casefold() and \
            matched_literal.casefold() in query.casefold():
        reasons.append(Reason("literal_text", "Una expresión de tu consulta aparece literalmente en el texto normativo.",
                              {"expression": matched_literal, "passage_start": passage.casefold().index(matched_literal.casefold())}))
    if (selected_territory and instrument_territory and selected_territory == instrument_territory):
        reasons.append(Reason("territory", "El documento está etiquetado con el territorio seleccionado.",
                              {"territory": selected_territory}))
    if legal_status == "unknown":
        reasons.append(Reason("unverified_validity", "No se ha verificado la vigencia jurídica de esta redacción.",
                              {"status": legal_status}))
    return [asdict(r) for r in reasons]
