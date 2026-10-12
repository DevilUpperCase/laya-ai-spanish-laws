export type Session={token?:string;tenant_id:string;email?:string;role?:string};

export type BrowserSession={email:string;expires_at:string;tenants:Array<{id:string;name:string;role:string}>};

export type Reason={kind:string;message:string;evidence:Record<string,unknown>};

export type Result={start_offset:number;end_offset:number;candidate_id:string;instrument_id:string;section_version_id:string;heading:string;passage:string;language_code:string;jurisdiction_code:string;official_reference:string;official_url:string;publication_date:string;consolidation_date:string;effective_from:string|null;effectiveness_verified:boolean;validity_status:string;warnings:string[];reasons:Reason[]};

export type Coverage={document_processing?:{generated_at?:string;snapshot_processing?:string;national_coverage?:string;freshness?:string;all_complete?:boolean;integrated_items?:number;bulletin_index_pending?:number};status:string;total_jurisdictions:number;verified_jurisdictions:number;missing_jurisdictions:number;legal_instruments:number;section_versions:number;embedded_chunks:number;sources:Array<{id:string;name:string;official_url:string;audit_status:string;last_successful_sync:string|null}>;gaps:string[];limitations:string[]};

export type SearchResponse={interpreted_query?:Record<string,unknown>;context_evidence?:Array<{document_id:string;filename:string;page_number:number;passage:string}>;private_results?:Array<{document_id:string;filename:string;page_number:number;passage:string;ocr_uncertain:boolean;retrieval_evidence:Array<{engine:string;rank:number}>}>;results:Result[];warnings:string[];coverage:Coverage;engines:{retrieval:string;laya_mode:string;laya_status:string};trace_id:string};

export type DocumentRecord={folder_id?:string|null;trashed_at?:string|null;id:string;filename:string;mime_type:string;parse_status:string;failure_code:string|null;pages:Array<{page_number:number;text:string;ocr_uncertain:boolean}>};

export const API_BASE="/api";

const messages:Record<string,string>={AUTH_INVALID:"La sesión ha caducado o no es válida.",TENANT_FORBIDDEN:"No tienes acceso a este espacio.",DOCUMENT_NOT_FOUND:"El documento ya no está disponible.",OCR_REQUIRED:"Este PDF requiere OCR local. Actívalo en el servidor.",ARCHIVE_LIMIT:"El documento supera los límites de descompresión.",UPLOAD_TOO_LARGE:"El archivo supera el tamaño permitido.",SELECTION_MISMATCH:"La selección no coincide con el texto guardado.",NATIONAL_COVERAGE_INCOMPLETE:"Cobertura nacional pendiente de auditoría. Puede faltar normativa relevante.",SEMANTIC_INDEX_PARTIAL:"El índice semántico está en proceso. La búsqueda textual incluye los textos importados.",LAYA_DEGRADED:"Clasificación temporalmente no disponible. Se conserva la búsqueda de referencia.",LAYA_INCOMPLETE:"La clasificación ha leído evidencia incompleta. El orden de búsqueda se conserva.",EMBEDDINGS_UNAVAILABLE:"Búsqueda semántica no disponible. Se usa la búsqueda textual.",UNKNOWN_EFFECTIVENESS:"Vigencia jurídica no verificada.",CONSOLIDATED_INFORMATIONAL:"Texto consolidado de carácter meramente informativo."};

Object.assign(messages,{TEXT_RETRIEVAL_DEGRADED:"Una parte de la búsqueda textual ha superado el tiempo disponible. Los resultados pueden estar incompletos.",OFFICIAL_ANNEXES_NOT_INDEXED:"Los anexos oficiales todavía no se han comprobado por completo.",AVAILABLE_HISTORY_NOT_RECONCILED:"El historial disponible en la fuente todavía no está auditado por completo.",OFFICIAL_TRANSLATION_MISSING:"Una traducción oficial no se ha podido importar.",AUTH_UNAVAILABLE:"El servicio de acceso no está disponible. Inténtalo de nuevo cuando termine el inicio o mantenimiento.",AUTH_RATE_LIMIT:"Demasiados intentos de acceso. Espera un minuto.",CSRF_REJECTED:"La solicitud de sesión no procede de un origen permitido.",PASSWORD_REJECTED:"No se ha podido cambiar la contraseña. Comprueba los requisitos."});

export function message(code:string){return messages[code]??"No se ha podido completar la operación. Código: "+code;}

export async function api<T>(path:string,session:Session,init:RequestInit={}):Promise<T>{

 const headers=new Headers(init.headers);if(session.token)headers.set("Authorization","Bearer "+session.token);headers.set("X-Tenant-ID",session.tenant_id);headers.set("X-Requested-With","LAYA");

 if(init.body && !(init.body instanceof FormData)) headers.set("Content-Type","application/json");

 const response=await fetch(API_BASE+path,{...init,headers,credentials:"include",cache:"no-store"});

 if(!response.ok){const body=await response.json().catch(()=>({error:"SERVICE_UNAVAILABLE"}));throw new Error(message(body.error??"SERVICE_UNAVAILABLE"));}

 return response.status===204?undefined as T:response.json();

}

export async function auth<T>(path:string,body?:unknown):Promise<T>{

 const response=await fetch(API_BASE+"/auth/"+path,{method:body===undefined?"GET":"POST",credentials:"include",cache:"no-store",headers:{"Content-Type":"application/json","X-Requested-With":"LAYA"},...(body===undefined?{}:{body:JSON.stringify(body)})});

 if(!response.ok){const payload=await response.json().catch(()=>({}));throw new Error(message(payload.error??"AUTH_INVALID"));}

 return response.status===204?undefined as T:response.json();

}

export function unicodeOffset(text:string,utf16Offset:number){return Array.from(text.slice(0,utf16Offset)).length;}

export function safeOfficialUrl(url:string){try{const u=new URL(url);return ["https:","http:"].includes(u.protocol)?u.href:"#";}catch{return "#";}}



Object.assign(messages,{REVISION_CONFLICT:"La nota ha cambiado. Recarga y revisa antes de guardar.",ATTACHMENT_NOT_READY:"Un archivo adjunto a?n no est? procesado.",ATTACHMENT_NOT_AVAILABLE:"Un adjunto no est? disponible o est? en Papelera.",PRIVATE_INDEX_PENDING:"El ?ndice de documentos est? pendiente. Se usa la recuperaci?n textual disponible.",ATTACHMENT_CONTEXT_BOUNDED:"Se han usado los pasajes m?s relevantes de los adjuntos; no todo su contenido.",WRITE_FORBIDDEN:"Tu permiso es de lectura.",NAME_INVALID:"Introduce un nombre v?lido.",BULLETIN_INDEX_PARTIAL:"El ?ndice de publicaciones oficiales est? incompleto."});


Object.assign(messages,{INDIVIDUAL_PUBLICATION_NOT_GENERAL_RULE:"Publicaci?n individual; no es una norma general.",BULLETIN_RETRIEVAL_DEGRADED:"La b?squeda de boletines est? temporalmente incompleta."});
