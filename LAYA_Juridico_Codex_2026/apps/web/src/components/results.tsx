"use client";
import {useEffect,useState} from "react";
import {useSession} from "@/components/workspace";
import {api} from "@/lib/api";
import {Button} from "@/components/ui/button";
import Link from "next/link";

import {ExternalLink,FileText} from "lucide-react";

import {Result,message,safeOfficialUrl} from "@/lib/api";

export function Results({results}:{results:Result[]}){
 const session=useSession();const [books,setBooks]=useState<Array<{id:string;title:string}>>([]),[book,setBook]=useState(""),[error,setError]=useState("");
 useEffect(()=>{let active=true;if(session)api<Array<{id:string;title:string}>>("/v1/notebooks",session).then(b=>{if(active)setBooks(b);}).catch(()=>{});return()=>{active=false;};},[session]);
 async function save(version:string){if(!session||!book)return;try{await api("/v1/notebooks/"+book+"/references",session,{method:"POST",body:JSON.stringify({section_version_id:version})});setError("Referencia guardada en el cuaderno.");}catch(e){setError((e as Error).message);}}
 return <div className="results">{results.length>0&&<><label>Cuaderno para guardar referencias<select value={book} onChange={e=>setBook(e.target.value)}><option value="">Selecciona un cuaderno</option>{books.map(b=><option value={b.id} key={b.id}>{b.title}</option>)}</select></label>{error&&<p role="status">{error}</p>}</>}{results.map((result,index)=><article key={result.candidate_id} className="result-card"><div className="result-top"><span className="result-number">{String(index+1).padStart(2,"0")}</span><span className="badge"><FileText size={13}/>{result.official_reference}</span><span className="muted">{result.jurisdiction_code} · {result.language_code}</span></div><h2>{result.heading}</h2><p className="passage">{result.passage}</p><div className="metadata"><span>Publicación: {result.publication_date}</span><span>Versión publicada: {result.consolidation_date}</span><span>{result.effectiveness_verified?"Intervalo verificado":"Vigencia por verificar"}</span></div><div className="reason-box">{result.reasons.map((r,i)=><p key={i}>{r.message}</p>)}</div><div className="result-bottom"><p className="legal-note">{result.warnings.map(message).join(" ")}</p>{!result.section_version_id.startsWith("bulletin:")&&<Button variant="ghost" disabled={!book||session?.role==="reader"} onClick={()=>save(result.section_version_id)}>Guardar referencia</Button>}<Link href={"/instruments/"+encodeURIComponent(result.instrument_id)+"?version="+encodeURIComponent(result.section_version_id)+"&start="+result.start_offset+"&end="+result.end_offset}>Ver documento y versión</Link><a href={safeOfficialUrl(result.official_url)} target="_blank" rel="noreferrer">Fuente oficial <ExternalLink size={14}/></a></div></article>)}</div>;}

