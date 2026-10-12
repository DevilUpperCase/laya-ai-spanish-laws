"""Prepare 200 public legal-search drafts. No professional judgments are generated."""
import json
from pathlib import Path

LANGUAGES={
 'es':['arrendamiento vivienda','protección datos personales','procedimiento administrativo','contratación pública','tributos locales','ordenanza residuos','urbanismo licencias','protección medio ambiente','norma inexistente ZZXQ998877','norma inexistente ZZXQ665544'],
 'ca':['arrendament habitatge','protecció dades personals','procediment administratiu','contractació pública','tributs locals','ordenança residus','urbanisme llicències','protecció medi ambient','norma inexistent ZZXQ998877','norma inexistent ZZXQ665544'],
 'gl':['arrendamento vivenda','protección datos persoais','procedemento administrativo','contratación pública','tributos locais','ordenanza residuos','urbanismo licenzas','protección medio ambiente','norma inexistente ZZXQ998877','norma inexistente ZZXQ665544'],
 'eu':['etxebizitza errentamendua','datu pertsonalen babesa','administrazio prozedura','kontratazio publikoa','tokiko zergak','hondakinen ordenantza','hirigintza lizentziak','ingurumenaren babesa','arau ezexistente ZZXQ998877','arau ezexistente ZZXQ665544']}
TIERS=['state','regional','provincial','municipal','island_foral']


def drafts():
    rows=[]
    for language,topics in LANGUAGES.items():
        for tier in TIERS:
            for i,query in enumerate(topics):
                rows.append({'id':f'{language}-{tier}-{i+1:02d}','query':query,'language':language,'tier':tier,'split':'holdout' if i in {1,3,5,7,9} else 'calibration','temporal':i in {6,7},'as_of':'2020-01-01' if i in {6,7} else None,'negative':i>=8,'territory_codes':[],'judgments':{},'reviewer':None,'review_evidence_sha256':None,'status':'draft_requires_professional_rewrite_and_judgment','review_notes':'Choose exact jurisdictions and references; confirm official language, temporal expectations, relevant candidate IDs and negative scope. Repeated topics are starting prompts, not independent reviewed cases.'})
    return rows


def main():
    path=Path(__file__).parent/'review-queue.json'
    if path.exists():raise RuntimeError('Review queue exists; preserve human edits rather than overwrite it')
    path.write_text(json.dumps(drafts(),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Created 200 unreviewed drafts. Release evaluation remains blocked.')


if __name__=='__main__':main()
