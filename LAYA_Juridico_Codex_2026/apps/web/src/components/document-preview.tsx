"use client";
import {useEffect,useState} from "react";
import {Session,API_BASE} from "@/lib/api";
export function DocumentPreview({session,path,page=1}:{session:Session;path:string;page?:number}){
 const [url,setUrl]=useState(""),[error,setError]=useState("");
 useEffect(()=>{let active=true,object="";const abort=new AbortController();setUrl("");setError("");
  fetch(API_BASE+path,{credentials:"include",cache:"no-store",headers:{"X-Tenant-ID":session.tenant_id},signal:abort.signal}).then(async response=>{
   if(!response.ok)throw new Error("No se puede abrir el original.");object=URL.createObjectURL(await response.blob());if(active)setUrl(object);else URL.revokeObjectURL(object);
  }).catch(()=>{if(active)setError("El original no está disponible. Puedes consultar el texto y la fuente oficial.");});
  return()=>{active=false;abort.abort();if(object)URL.revokeObjectURL(object);};
 },[session.tenant_id,path]);
 return <section className="panel original-preview"><h2>Documento original</h2>{error?<p role="alert">{error}</p>:url?<><iframe title="Vista del documento original PDF" src={url+"#page="+page} style={{width:"100%",height:650,border:0}}/><a href={url} download="original.pdf">Descargar PDF original</a></>:<p role="status">Abriendo original…</p>}</section>;
}
