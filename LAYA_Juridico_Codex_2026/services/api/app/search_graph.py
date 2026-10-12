from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .contracts import RetrievalQuery, Candidate, Decision, SearchResult


class SearchState(TypedDict, total=False):
    retrieval_query: RetrievalQuery
    candidates: list[Candidate]
    decisions: list[Decision]
    results: list[SearchResult]
    warnings: list[str]
    laya_status: str
    embedding_degraded: bool


def build_search_graph(retriever, laya, explainer):
    async def validate(state):
        if len(state["retrieval_query"].query) > 3000:
            raise ValueError("Query budget exceeded")
        return {}

    async def resolve_selection(state):
        # SearchService resolves stored tenant-authorized spans before graph invocation.
        return {}

    async def retrieve(state):
        candidates=await retriever.ainvoke(state["retrieval_query"])
        return {"candidates":candidates,"embedding_degraded":getattr(candidates,"embedding_degraded",False),'warnings':state.get('warnings',[])+getattr(candidates,'retrieval_warnings',[])}

    async def fusion(state):
        # HybridRetriever performs fusion over independently retrieved rank lists.
        return {"candidates":state["candidates"][:50]}

    async def shadow(state):
        if not state["candidates"]:
            return {"decisions":[],"laya_status":"empty"}
        try:
            decisions = await laya.classify(state["retrieval_query"].query,state["candidates"])
            if [d.candidate_id for d in decisions] != [c.candidate_id for c in state["candidates"]]:
                raise ValueError("Decision ordering mismatch")
            incomplete = any(d.truncated is not False or d.abstained is not False for d in decisions)
            return {"decisions":decisions,"laya_status":"incomplete" if incomplete else "ok",
                    "warnings":state.get("warnings",[]) + (["LAYA_INCOMPLETE"] if incomplete else [])}
        except (TimeoutError, OSError, ValueError, RuntimeError):
            return {"decisions":[],"laya_status":"degraded","warnings":state.get("warnings",[]) + ["LAYA_DEGRADED"]}

    async def explain(state):
        return {"results":[SearchResult(**c.model_dump(),reasons=explainer(state["retrieval_query"].query,c),
            warnings=c.ingestion_warnings+(["UNKNOWN_EFFECTIVENESS"] if not c.effectiveness_verified else []) + (["CONSOLIDATED_INFORMATIONAL"] if c.is_consolidated else [])) for c in state["candidates"]]}

    async def serialize(state):
        return {}

    builder = StateGraph(SearchState)
    names = ("validate","resolve_selection","retrieve","fuse","laya_shadow","explain","serialize")
    for name,node in zip(names,(validate,resolve_selection,retrieve,fusion,shadow,explain,serialize)):
        builder.add_node(name,node)
    for left,right in zip((START,) + names,names + (END,)):
        builder.add_edge(left,right)
    return builder.compile()  # Intentionally no checkpointer or persistent private graph state.


class PrivateSearchState(TypedDict,total=False):
    query: dict
    response: dict


def build_private_search_graph(retriever):
    async def validate(state):
        await retriever.authorize(state['query']['context'],state['query']['ids'])
        return {}
    async def retrieve(state):return {'response':await retriever.ainvoke(state['query'])}
    async def recheck(state):
        await retriever.authorize(state['query']['context'],state['query']['ids'])
        return {}
    graph=StateGraph(PrivateSearchState)
    graph.add_node('validate_attachments',validate);graph.add_node('retrieve_private',retrieve);graph.add_node('recheck_access',recheck)
    graph.add_edge(START,'validate_attachments');graph.add_edge('validate_attachments','retrieve_private');graph.add_edge('retrieve_private','recheck_access');graph.add_edge('recheck_access',END)
    return graph.compile() # No private checkpoint or tracing.
