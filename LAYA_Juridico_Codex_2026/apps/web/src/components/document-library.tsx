"use client";

import {useEffect,useState} from "react";

import Link from "next/link";

import {api,DocumentRecord} from "@/lib/api";

import {useSession} from "@/components/workspace";

import {Button} from "@/components/ui/button";

type Folder={id:string;name:string;parent_id:string|null};type Book={id:string;title:string};

export function DocumentLibrary({trash=false}:{trash?:boolean}){

 const session=useSession();const [docs,setDocs]=useState<DocumentRecord[]>([]),[folders,setFolders]=useState<Folder[]>([]),[books,setBooks]=useState<Book[]>([]),[folder,setFolder]=useState(""),[query,setQuery]=useState(""),[title,setTitle]=useState(""),[error,setError]=useState(""),[cursor,setCursor]=useState<string|null>(null);

 async function refresh(next?:string){if(!session)return;const params=new URLSearchParams({trash:String(trash),query,...(folder?{folder_id:folder}:{}),...(next?{cursor:next}:{})});const result=await api<{items:DocumentRecord[];next_cursor:string|null}>("/v1/documents?"+params,session);setDocs(old=>next?[...old,...result.items]:result.items);setCursor(result.next_cursor);}

 useEffect(()=>{let active=true;if(session){refresh().catch(e=>setError(e.message));Promise.all([api<Folder[]>("/v1/folders",session),api<Book[]>("/v1/notebooks",session)]).then(([f,b])=>{if(active){setFolders(f);setBooks(b);}}).catch(e=>setError(e.message));}return()=>{active=false;};},[session,folder,query,trash]);

 async function action(id:string,kind:string){if(!session)return;if(kind==="permanent"&&!confirm("Eliminar permanentemente el documento y sus notas vinculadas. Esta acción no se puede deshacer: el acceso se revoca inmediatamente, las copias activas se purgan en un plazo máximo de 24 horas y las copias de seguridad cifradas caducan en un máximo de 30 días."))return;try{await api("/v1/documents/"+id+(kind==="permanent"?"":"/"+kind),session,{method:kind==="permanent"?"DELETE":"POST"});await refresh();}catch(e){setError((e as Error).message);}}

 async function create(kind:"folders"|"notebooks"){if(!session||!title.trim())return;try{await api("/v1/"+kind,session,{method:"POST",body:JSON.stringify({name:title,parent_id:folder||null})});setTitle("");setFolders(await api<Folder[]>("/v1/folders",session));setBooks(await api<Book[]>("/v1/notebooks",session));}catch(e){setError((e as Error).message);}}

 async function metadata(doc:DocumentRecord){if(!session)return;const value=prompt("Nombre del documento",doc.filename);if(value===null)return;try{await api("/v1/documents/"+doc.id+"/metadata",session,{method:"POST",body:JSON.stringify({filename:value})});await refresh();}catch(e){setError((e as Error).message);}}

 async function empty(){if(!session||!confirm("Vaciar Papelera: eliminar permanentemente todos sus documentos y notas vinculadas. Esta acción no se puede deshacer; revoca el acceso de inmediato, purga las copias activas en un máximo de 24 horas y hace caducar las copias cifradas en un máximo de 30 días."))return;try{let more=true;while(more){const result=await api<{has_more:boolean}>("/v1/trash/empty",session,{method:"POST"});more=result.has_more;}await refresh();}catch(e){setError((e as Error).message);}}

 return <section className="library"><div className="document-toolbar"><h2>{trash?"Papelera":"Biblioteca del espacio"}</h2><Link href={trash?"/documents":"/trash"}>{trash?"Volver a documentos":"Abrir Papelera"}</Link>{trash&&<Button disabled={session?.role==="reader"} variant="outline" onClick={empty}>Vaciar Papelera</Button>}</div>{trash&&<p>Los documentos en Papelera se pueden restaurar indefinidamente. Los plazos de revocación y borrado empiezan solo cuando eliges eliminarlos permanentemente.</p>}

 {error&&<p className="error" role="alert">{error}</p>}<div className="document-toolbar"><label>Buscar archivos<input value={query} onChange={e=>setQuery(e.target.value)}/></label><label>Carpeta<select value={folder} onChange={e=>setFolder(e.target.value)}><option value="">Todas las carpetas</option>{folders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label></div>

 {!trash&&<div className="panel"><label>Nombre de carpeta o cuaderno<input value={title} onChange={e=>setTitle(e.target.value)} maxLength={200}/></label><Button disabled={session?.role==="reader"} variant="outline" onClick={()=>create("folders")}>Crear carpeta</Button> <Button disabled={session?.role==="reader"} variant="outline" onClick={()=>create("notebooks")}>Crear cuaderno</Button><div className="notebook-links">{books.map(b=><Link key={b.id} href={"/notebooks/"+b.id}>{b.title}</Link>)}</div></div>}

 {!docs.length&&<p className="empty">No hay documentos en esta vista.</p>}{docs.map(doc=><article className="panel library-file" key={doc.id}><Link href={"/documents/"+doc.id+(trash?"?trash=1":"")}>{doc.filename}</Link><span className="badge">{doc.parse_status}</span><div className="document-toolbar">{trash?<><Button disabled={session?.role==="reader"} variant="outline" onClick={()=>action(doc.id,"restore")}>Restaurar</Button><Button disabled={session?.role==="reader"} variant="outline" onClick={()=>action(doc.id,"permanent")}>Eliminar permanentemente</Button></>:<><Button disabled={session?.role==="reader"} variant="ghost" onClick={()=>metadata(doc)}>Renombrar</Button><label>Mover a carpeta<select disabled={session?.role==="reader"} value={doc.folder_id??""} onChange={async e=>{if(!session)return;try{await api("/v1/documents/"+doc.id+"/metadata",session,{method:"POST",body:JSON.stringify({move:true,folder_id:e.target.value||null})});await refresh();}catch(error){setError((error as Error).message);}}}><option value="">Raíz</option>{folders.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select></label><Button disabled={session?.role==="reader"} variant="outline" onClick={()=>action(doc.id,"trash")}>Mover a Papelera</Button></>}</div></article>)}{cursor&&<Button variant="outline" onClick={()=>refresh(cursor)}>Cargar más archivos</Button>}</section>;

}

