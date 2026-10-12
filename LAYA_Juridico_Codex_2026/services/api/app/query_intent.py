"""Literal user-authored intent and bounded passage plans; no generated facts."""
def build_query_plan(request):
    inputs=[request.query.strip()] if request.query.strip() else []
    if request.intent:
        issue=request.intent.issue.strip();objective=request.intent.objective.strip()
        if issue:inputs.append(issue)
        if objective:inputs.append((issue+'\n'+objective).strip())
    return {'original_query':request.query,'inputs':list(dict.fromkeys(inputs))[:4],
            'territory_codes':request.territory_codes,'as_of':request.as_of,'scope':request.scope,
            'issue':request.intent.issue if request.intent else '',
            'objective':request.intent.objective if request.intent else ''}

def split_passages(text):
    return [(start,min(len(text),start+1000),text[start:start+1000]) for start in range(0,len(text),880) if text[start:start+1000].strip()]
