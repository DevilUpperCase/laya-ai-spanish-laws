"use client";

import {useEffect,useState} from "react";

import {DocumentPreview} from "@/components/document-preview";

import {useParams,useRouter} from "next/navigation";

import {Search,Trash2,Download} from "lucide-react";

import {Button} from "@/components/ui/button";

import {useSession} from "@/components/workspace";

import {Results} from "@/components/results";

import {api,DocumentRecord,SearchResponse,unicodeOffset,message,API_BASE} from "@/lib/api";

type Selection={page_number:number;start_offset:number;end_offset:number;selected_text:string};

export default function DocumentView(){

 const session=useSession();const [trash,setTrash]=useState(false),[notebooks,setNotebooks]=useState<Array<{id:string;title:string}>>([]),[book,setBook]=useState(""),[note,setNote]=useState(""),[trashNotes,setTrashNotes]=useState<Array<{id:string;body:string}>>([]);

 useEffect(()=>{const params=new URLSearchParams(window.location.search);setTrash(params.get("trash")==="1");const requested=Number(params.get("page")??1);setPage(Number.isInteger(requested)&&requested>0?requested-1:0);},[]);

 useEffect(()=>{if(session){api<Array<{id:string;title:string}>>("/v1/notebooks",session).then(setNotebooks).catch(()=>{});}},[session]);const {id}=useParams<{id:string}>();const router=useRouter();const [doc,setDoc]=useState<DocumentRecord|null>(null);const [page,setPage]=useState(0);const [selection,setSelection]=useState<Selection|null>(null);const [results,setResults]=useState<SearchResponse|null>(null);const [error,setError]=useState("");const [busy,setBusy]=useState(false);const [confirm,setConfirm]=useState(false);

 useEffect(()=>{let cancelled=false;let timer:ReturnType<typeof setTimeout>;async function refresh(){if(!session)return;try{const record=await api<DocumentRecord>("/v1/documents/"+id+(trash?"?trash=true":""),session);if(cancelled)return;setDoc(record);setError("");setPage(current=>Math.min(current,Math.max(0,record.pages.length-1)));if(["queued","processing"].includes(record.parse_status))timer=setTimeout(refresh,2000);}catch(e){if(!cancelled){setDoc(null);setSelection(null);setResults(null);setError(e instanceof Error?e.message:"Error");}}}refresh();return()=>{cancelled=true;clearTimeout(timer);};},[id,session,trash]);

 async function search(){if(!session||!selection)return;setBusy(true);setError("");try{setResults(await api<SearchResponse>(`/v1/documents/${id}/search-related`,session,{method:"POST",body:JSON.stringify(selection)}));}catch(e){setError(e instanceof Error?e.message:"Error");}finally{setBusy(false);}}

 async function remove(){if(!session)return;setBusy(true);try{await api<void>("/v1/documents/"+id+"/trash",session,{method:"POST"});setDoc(null);setResults(null);setSelection(null);router.push("/documents");}catch(e){setError(e instanceof Error?e.message:"Error");}finally{setBusy(false);}}

 async function download(){if(!session)return;setError("");try{const response=await fetch(`${API_BASE}/v1/documents/${id}/download${trash?"?trash=true":""}`,{headers:{"X-Tenant-ID":session.tenant_id},credentials:"include",cache:"no-store"});if(!response.ok)throw new Error("El documento no está disponible.");const object=URL.createObjectURL(await response.blob());const a=document.createElement("a");a.href=object;a.download=doc?.filename??"documento";a.click();URL.revokeObjectURL(object);}catch(e){setError(e instanceof Error?e.message:"Error");}}

 function select(target:HTMLTextAreaElement){if(!doc)return;const text=doc.pages[page]?.text??"";const start=target.selectionStart;const end=target.selectionEnd;const selected=text.slice(start,end);setSelection(selected?{page_number:doc.pages[page].page_number,start_offset:unicodeOffset(text,start),end_offset:unicodeOffset(text,end),selected_text:selected}:null);}

 async function saveNote(){if(!session||!book)return;try{await api("/v1/notes",session,{method:"POST",body:JSON.stringify({notebook_id:book,document_id:id,body:note,...(selection?{page_number:selection.page_number,start_offset:selection.start_offset,end_offset:selection.end_offset}:{})})});setNote("");}catch(e){setError((e as Error).message);}}

 useEffect(()=>{if(session&&trash)api<Array<{id:string;body:string}>>("/v1/documents/"+id+"/trash-notes",session).then(setTrashNotes).catch(()=>{});},[session,trash,id]);

 return <><p className="eyebrow">Documento privado</p><h1>{doc?.filename??"Documento"}</h1>{error&&<p className="error" role="alert">{error}</p>}{doc&&<>{session&&doc.mime_type==="application/pdf"&&<DocumentPreview session={session} path={"/v1/documents/"+id+"/preview"+(trash?"?trash=true":"")} page={(doc.pages[page]?.page_number??1)}/>} {trash&&<div className="warning">En Papelera: puedes restaurar este documento desde la lista. {trashNotes.map(n=><p key={n.id}>{n.body}</p>)}</div>}<div className="document-toolbar" style={{marginTop:24}}><Button variant="outline" onClick={download}><Download size={16}/>Descargar original</Button>{!trash&&<Button disabled={session?.role==="reader"} variant="outline" onClick={()=>setConfirm(true)}><Trash2 size={16}/>Mover a Papelera</Button>}</div>{confirm&&<div className="delete-confirm"><h2>Mover este documento a Papelera</h2><p>El original y sus notas se conservan. Puedes restaurarlos desde Papelera hasta que los elimines permanentemente.</p><Button onClick={remove} disabled={busy}>Confirmar traslado a Papelera</Button><Button variant="outline" onClick={()=>setConfirm(false)}>Cancelar</Button></div>}{["queued","processing"].includes(doc.parse_status)&&<p role="status" className="loading">Procesando el documento de forma local…</p>}{doc.parse_status==="failed"&&<p className="error">{message(doc.failure_code??"EXTRACTION_FAILED")}</p>}{doc.parse_status==="ready"&&<><label style={{maxWidth:220,marginBottom:20}}>Página / sección lógica<select value={page} onChange={e=>{setPage(Number(e.target.value));setSelection(null);}}>{doc.pages.map((p,i)=><option key={p.page_number} value={i}>{p.page_number}</option>)}</select></label>{doc.pages[page]?.ocr_uncertain&&<div className="warning">Texto obtenido mediante OCR. Puede contener errores.</div>}<label>Selecciona texto para buscar normativa relacionada<textarea className="document-page" readOnly value={doc.pages[page]?.text??""} onSelect={e=>select(e.currentTarget)} aria-label="Texto del documento"/></label>{!trash&&selection&&<div className="selection-box"><p>{selection.selected_text}</p><Button onClick={search} disabled={busy||Array.from(selection.selected_text).length>3000}><Search size={16}/>{busy?"Buscando…":"Buscar normativa relacionada"}</Button>{Array.from(selection.selected_text).length>3000&&<p>Selecciona hasta 3000 caracteres.</p>}</div>}</>}{!trash&&<section className="panel"><h2>Nota vinculada al documento</h2><label>Cuaderno<select value={book} onChange={e=>setBook(e.target.value)}><option value="">Selecciona un cuaderno</option>{notebooks.map(n=><option key={n.id} value={n.id}>{n.title}</option>)}</select></label><label>Tu nota<textarea rows={4} value={note} onChange={e=>setNote(e.target.value)} maxLength={50000}/></label><p>{selection?"Vinculada a la selección actual.":"Vinculada al documento completo."}</p><Button disabled={!book||!note.trim()||session?.role==="reader"} onClick={saveNote}>Guardar nota vinculada</Button></section>}{results&&<><div className="warning">{results.warnings.map(message).join(" ")}</div>{results.results.length?<Results results={results.results}/>:<div className="empty"><h2>Sin extractos relacionados</h2><p>Puede faltar normativa en el corpus.</p></div>}</>}</>}</>;

}

