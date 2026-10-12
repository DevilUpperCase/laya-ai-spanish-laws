from .contracts import RetrievalQuery,SearchResponse
from .errors import DomainError
from .explanations import build_reasons
from .search_graph import build_search_graph,build_private_search_graph
from .query_intent import build_query_plan
from .attachments import AttachmentService


class SearchService:
    def __init__(self,retriever,laya,selection,coverage):
        self.retriever,self.selection,self.coverage=retriever,selection,coverage
        self.attachments=AttachmentService(selection.db,retriever.embeddings) if hasattr(selection,"db") and hasattr(retriever,"embeddings") else None
        self.private_graph=build_private_search_graph(self.attachments.retriever) if self.attachments else None
        self.graph=build_search_graph(retriever,laya,build_reasons)

    async def search(self,request,context,trace_id):
        query=request.query
        if request.mode=="document":
            stored=await self.selection.resolve(context,request.document_id,request.selection)
            query=(query+"\n"+stored).strip()
            if len(query)>3000:raise DomainError("COMBINED_QUERY_TOO_LONG",422)
        plan=build_query_plan(request);context_evidence=[];extra_warnings=[];sources=[]
        if request.mode=='document':plan['inputs']=[query]
        if request.attachment_ids:
            if request.scope=='attachments':
                private_state=await self.private_graph.ainvoke({'query':{'context':context,'ids':request.attachment_ids,'query':plan['inputs'][-1]}},config={'callbacks':[],'recursion_limit':8})
                private=private_state['response']
                return SearchResponse(results=[],private_results=private['results'],warnings=private['warnings'],coverage=await self.coverage.report(context),trace_id=trace_id,engines={'retrieval':'private_hybrid','laya_mode':'shadow','laya_status':'not_applicable_private'},interpreted_query=plan)
            context_evidence,extra_warnings=await self.attachments.resolve(context,request.attachment_ids,plan)
            room=4-len(plan['inputs'])
            if len(context_evidence)>room:extra_warnings.append('ATTACHMENT_CONTEXT_BOUNDED')
            context_evidence=context_evidence[:room]
            sources=[{'context_kind':'question_or_intent'} for _ in plan['inputs']]
            for passage in context_evidence:
                sources.append({'context_kind':'attachment','context_document_id':str(passage['document_id']),'context_page':passage['page_number'],'context_start':passage['start_offset'],'context_end':passage['end_offset']})
            plan['inputs']+= [p['passage'] for p in context_evidence]
        retrieval=RetrievalQuery(query=query,retrieval_inputs=plan['inputs'],retrieval_sources=sources,request=request,context=context,trace_id=trace_id)
        state=await self.graph.ainvoke({"retrieval_query":retrieval,"warnings":[]},config={"callbacks":[],"recursion_limit":12})
        if request.document_id:
            await self.selection.recheck(context,request.document_id)
        if request.attachment_ids:await self.attachments.retriever.authorize(context,request.attachment_ids)
        coverage=await self.coverage.report(context)
        warnings=extra_warnings+list(state["warnings"])+["NATIONAL_COVERAGE_INCOMPLETE"]
        if coverage.embedded_chunks<coverage.total_chunks:warnings.append("SEMANTIC_INDEX_PARTIAL")
        if state["embedding_degraded"]:warnings.append("EMBEDDINGS_UNAVAILABLE")
        return SearchResponse(results=state["results"],interpreted_query=plan,context_evidence=context_evidence,coverage=coverage,warnings=warnings,trace_id=trace_id,
            engines={"retrieval":"hybrid_degraded" if state["embedding_degraded"] else "hybrid",
                     "laya_mode":"shadow","laya_status":state["laya_status"]})
