"""Compare public calibration rankings; do not tune on the frozen holdout."""
import argparse,hashlib,json
from pathlib import Path
from .metrics import ranking_metrics,validate_reviewed_dataset

def compare(cases,baseline,improved):
    validate_reviewed_dataset(cases)
    calibration=[c for c in cases if c['split']=='calibration'];ids={c['id'] for c in calibration}
    if set(baseline)!=ids or set(improved)!=ids:raise ValueError('Calibration IDs must match exactly; no holdout tuning')
    output={}
    for name,rankings in [('baseline',baseline),('improved',improved)]:
        values=[ranking_metrics(rankings[c['id']],c['judgments'],20) for c in calibration if not c.get('negative')]
        if not values:raise ValueError('Positive reviewed calibration required')
        negatives=[c for c in calibration if c.get('negative')]
        if not negatives:raise ValueError('Negative calibration required')
        output[name]={key:sum(row[key] for row in values)/len(values) for key in ('recall','mrr','ndcg')}
        output[name]['negative_false_positive_rate']=sum(bool(rankings[c['id']]) for c in negatives)/len(negatives)
    return {'calibration_cases':len(calibration),'scores':output,'status':'comparison_requires_professional_review','laya_training_authorized':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('cases','baseline','improved','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();report=compare(*[json.loads(getattr(args,n).read_text(encoding='utf-8')) for n in ('cases','baseline','improved')])
    report['input_sha256']={n:hashlib.sha256(getattr(args,n).read_bytes()).hexdigest() for n in ('cases','baseline','improved')}
    report['limitations']=['Reviewed calibration only; preserves sealed holdout. No model training, production reranking approval or performance guarantee implied.']
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
