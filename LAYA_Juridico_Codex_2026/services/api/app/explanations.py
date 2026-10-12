import re

import unicodedata

from .contracts import Candidate, Reason





def normalize(text):

    return "".join(ch for ch in unicodedata.normalize("NFD",text.casefold()) if not unicodedata.combining(ch))





def build_reasons(query: str, candidate: Candidate) -> list[Reason]:

    terms = {normalize(m.group()) for m in re.finditer(r"\w+",query) if len(m.group()) >= 4}

    reasons = []

    labels={"semantic":"Similitud sem?ntica de la consulta completa (no prueba de aplicabilidad jur?dica)","exact_reference":"Referencia exacta de la consulta", "lexical":"Recuperaci?n textual", "lexical_broad":"Recuperaci?n textual ampliada", "title_similarity":"Similitud del t?tulo", "bulletin_hybrid":"Recuperaci?n de una publicaci?n del bolet?n oficial"}

    for signal in candidate.retrieval_evidence:

        reasons.append(Reason(kind="retrieval_signal",message=labels.get(signal["engine"],signal["engine"])+" ? posici?n "+str(signal["rank"]),evidence={"engine":signal["engine"],"rank":signal["rank"],"section_version_id":candidate.section_version_id}))

    for match in re.finditer(r"\w+",candidate.passage):

        if normalize(match.group()) in terms:

            reasons.append(Reason(kind="literal_overlap",message="Coincidencia literal en el extracto: " + match.group(),

                evidence={"source_id":candidate.source_id,"section_version_id":candidate.section_version_id,

                          "passage_start":match.start(),"passage_end":match.end(),

                          "section_start":candidate.start_offset+match.start(),"section_end":candidate.start_offset+match.end()}))

            if sum(r.kind=="literal_overlap" for r in reasons) >= 3:

                break

    reasons.append(Reason(kind="official_provenance",message="Publicación y referencia de la fuente oficial.",

        evidence={"source_id":candidate.source_id,"section_version_id":candidate.section_version_id,"official_url":candidate.official_url,"publication_date":candidate.publication_date.isoformat()}))

    return reasons

