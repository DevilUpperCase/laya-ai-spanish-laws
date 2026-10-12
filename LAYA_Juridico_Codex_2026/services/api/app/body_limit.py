"""Bound request bytes before FastAPI's multipart parser can spool a file."""
class BodyLimitMiddleware:
    def __init__(self,app,upload_max_bytes):
        self.app=app
        self.upload_limit=upload_max_bytes+65536

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http" or scope["method"] not in {"POST","PUT","PATCH"}:
            return await self.app(scope,receive,send)
        limit=self.upload_limit if scope["path"]=="/v1/documents" else 65536
        chunks=[]
        size=0
        while True:
            message=await receive()
            if message["type"]=="http.disconnect":return
            chunk=message.get("body",b"")
            size+=len(chunk)
            if size>limit:
                await send({"type":"http.response.start","status":413,"headers":[
                    (b"content-type",b"application/json"),(b"cache-control",b"no-store")]})
                await send({"type":"http.response.body","body":b'{"error":"REQUEST_TOO_LARGE"}'})
                return
            chunks.append(chunk)
            if not message.get("more_body",False):break
        body=b"".join(chunks)
        delivered=False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {"type":"http.request","body":body,"more_body":False}
            return await receive()
        await self.app(scope,bounded_receive,send)
