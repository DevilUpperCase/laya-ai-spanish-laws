from .private_retrieval import PrivateRetriever

class AttachmentService:
    def __init__(self,db,embeddings):self.retriever=PrivateRetriever(db,embeddings)
    async def resolve(self,context,ids,plan):
        result=await self.retriever.ainvoke({'context':context,'ids':ids,'query':plan['inputs'][-1]})
        passages=[]
        selected=[];seen=set()
        for row in result['results']:
            if row['document_id'] not in seen:selected.append(row);seen.add(row['document_id'])
            if len(selected)==4:break
        for row in result['results']:
            if len(selected)==4:break
            if row not in selected:selected.append(row)
        for row in selected:
            passages.append({k:row[k] for k in ('document_id','filename','page_number','start_offset','end_offset','passage','ocr_uncertain')})
        return passages,result['warnings']+(['ATTACHMENT_CONTEXT_BOUNDED'] if len(result['results'])>4 else [])
