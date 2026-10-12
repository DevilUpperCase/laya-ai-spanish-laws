"use client";

import {DocumentLibrary} from "@/components/document-library";

import {useState} from "react";

import {useRouter} from "next/navigation";

import {Upload,FileText} from "lucide-react";

import {useSession} from "@/components/workspace";

import {Button} from "@/components/ui/button";

import {api,DocumentRecord} from "@/lib/api";

export default function Documents(){

 const session=useSession();const router=useRouter();const [file,setFile]=useState<File|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState("");

 async function upload(event:React.FormEvent){event.preventDefault();if(!session||!file)return;setBusy(true);setError("");try{const data=new FormData();data.set("file",file);const doc=await api<DocumentRecord>("/v1/documents",session,{method:"POST",headers:{"Idempotency-Key":crypto.randomUUID()},body:data});router.push("/documents/"+doc.id);}catch(e){setError(e instanceof Error?e.message:"Error al cargar");}finally{setBusy(false);}}

 return <><div className="page-heading"><div><p className="eyebrow">Expedientes privados</p><h1>Del documento<br/><em>a la normativa.</em></h1><p className="lead">Selecciona un fragmento y encuentra extractos oficiales relacionados.</p></div><FileText size={62} strokeWidth={1} className="heading-icon"/></div><form onSubmit={upload} className="panel document-upload"><h2>Cargar un documento</h2><label>Archivo PDF o DOCX<input type="file" accept=".pdf,.docx" required onChange={e=>setFile(e.target.files?.[0]??null)}/></label><p className="muted">Máximo 20 MB. Los documentos en Papelera se pueden restaurar indefinidamente. El borrado permanente es una acción separada e irreversible.</p><Button disabled={busy||!file||session?.role==="reader"}><Upload size={16}/>{busy?"Cargando…":"Cargar y procesar"}</Button>{error&&<p className="error" role="alert">{error}</p>}</form><DocumentLibrary/><div className="warning">Las páginas DOCX son secciones lógicas. El OCR local puede introducir errores; verifica siempre el fragmento seleccionado.</div></>;

}

