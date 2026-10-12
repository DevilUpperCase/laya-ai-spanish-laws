"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {api} from "@/lib/api";
import {useSession} from "@/components/workspace";
import {Button} from "@/components/ui/button";
type Note={id:string;body:string;revision:number;document_id:string|null;page_number:number|null};
type Notebook={id:string;title:string;notes:Note[];references:{id:string;section_version_id:string}[]};
export function NotebookEditor({id}:{id:string}){
 const session=useSession();const [book,setBook]=useState<Notebook|null>(null),[body,setBody]=useState(""),[editing,setEditing]=useState<Note|null>(null),[error,setError]=useState("");
 async function refresh(){if(session)setBook(await api<Notebook>("/v1/notebooks/"+id,session));}
 useEffect(()=>{refresh().catch(e=>setError(e.message));},[id,session]);
 async function save(){if(!session)return;setError("");try{await api("/v1/notes"+(editing?"/"+editing.id:""),session,{method:"POST",body:JSON.stringify({notebook_id:id,body,...(editing?{revision:editing.revision}:{})})});setBody("");setEditing(null);await refresh();}catch(e){setError((e as Error).message);}}
 return <><h1>{book?.title??"Cuaderno"}</h1><p>Notas escritas por el equipo. Las citas enlazan a sus documentos y versiones.</p>{error&&<p className="error" role="alert">{error}</p>}
 <div className="panel"><label>Nota del cuaderno<textarea value={body} maxLength={50000} onChange={e=>setBody(e.target.value)} rows={6}/></label><Button disabled={session?.role==="reader"} onClick={save}>{editing?"Guardar cambios":"Guardar nota"}</Button>{editing&&<Button variant="outline" onClick={()=>{setEditing(null);setBody("");}}>Cancelar edición</Button>}</div>
 {book?.notes.map(note=><article className="panel notebook-note" key={note.id}><p style={{whiteSpace:"pre-wrap"}}>{note.body}</p>{note.document_id&&<Link href={"/documents/"+note.document_id}>Documento · página {note.page_number??"sin selección"}</Link>}<Button disabled={session?.role==="reader"} variant="ghost" onClick={()=>{setEditing(note);setBody(note.body);}}>Editar nota</Button></article>)}
 {book?.references.map(ref=><p key={ref.id}><Link href={"/instruments/version?version="+ref.section_version_id}>Referencia oficial guardada</Link></p>)}</>;
}
