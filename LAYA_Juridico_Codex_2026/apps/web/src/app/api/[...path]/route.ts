/** Same-origin streaming gateway. Credentials stay in HttpOnly browser cookies. */
import {NextRequest} from "next/server";
export const dynamic="force-dynamic";
const upstream=process.env.INTERNAL_API_URL??"http://127.0.0.1:8000";
async function forward(request:NextRequest,{params}:{params:Promise<{path:string[]}>}){
 const {path}=await params;
 if(!["auth","v1"].includes(path[0])||path.some(p=>!p||p==="."||p===".."||p.includes("/")||p.includes("\\")))return new Response(null,{status:404});
 const headers=new Headers();
 for(const key of ["content-type","cookie","origin","x-requested-with","x-tenant-id","idempotency-key"]) {const value=request.headers.get(key);if(value)headers.set(key,value);}
 const options:RequestInit&{duplex?:string}={method:request.method,headers,cache:"no-store",redirect:"manual",signal:request.signal};
 if(!["GET","HEAD"].includes(request.method)){options.body=request.body;options.duplex="half";}
 try{
  const response=await fetch(upstream+"/"+path.map(encodeURIComponent).join("/")+request.nextUrl.search,options);
  const outgoing=new Headers({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"});
  for(const key of ["content-type","content-disposition","x-request-id"]) {const value=response.headers.get(key);if(value)outgoing.set(key,value);}
  for(const cookie of response.headers.getSetCookie())outgoing.append("Set-Cookie",cookie);
  return new Response(response.body,{status:response.status,headers:outgoing});
 }catch{return Response.json({error:"SERVICE_UNAVAILABLE"},{status:503,headers:{"Cache-Control":"no-store"}});}
}
export {forward as GET,forward as POST,forward as DELETE};
