"use client";

import React,{createContext,useContext,useEffect,useState} from "react";

import Link from "next/link";

import {usePathname} from "next/navigation";

import {Scale,LogOut,ShieldCheck} from "lucide-react";

import {Button} from "@/components/ui/button";

import {auth,BrowserSession,Session} from "@/lib/api";

const Context=createContext<{session:Session|null}>({session:null});

export function useSession(){return useContext(Context).session;}

export function Workspace({children}:{children:React.ReactNode}){

 const [session,setSession]=useState<Session|null>(null),[identity,setIdentity]=useState<BrowserSession|null>(null);

 const [email,setEmail]=useState(""),[password,setPassword]=useState(""),[newPassword,setNewPassword]=useState("");

 const [change,setChange]=useState(false),[error,setError]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true);const path=usePathname();

 function apply(value:BrowserSession){setIdentity(value);setSession({tenant_id:value.tenants[0].id,email:value.email,role:value.tenants[0].role});}

 useEffect(()=>{let active=true;auth<BrowserSession>("session").then(value=>{if(active)apply(value);}).catch(()=>{}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);

 useEffect(()=>{if(!identity)return;const timer=setTimeout(()=>{setSession(null);setIdentity(null);setError("La sesión ha caducado. Vuelve a entrar.");},Math.max(0,new Date(identity.expires_at).getTime()-Date.now()));return()=>clearTimeout(timer);},[identity]);

 async function connect(event:React.FormEvent){event.preventDefault();setBusy(true);setError("");try{apply(await auth<BrowserSession>("login",{email:email.trim(),password}));setPassword("");}catch(e){setError(e instanceof Error?e.message:"Error de conexión");}finally{setBusy(false);}}

 async function logout(){setBusy(true);setError("");try{await auth("logout",{});setSession(null);setIdentity(null);setPassword("");setChange(false);}catch{setError("No se ha podido cerrar la sesión. Inténtalo de nuevo.");}finally{setBusy(false);}}

 async function updatePassword(event:React.FormEvent){event.preventDefault();setBusy(true);setError("");try{await auth("password",{email:identity?.email,password,new_password:newPassword});setPassword("");setNewPassword("");setChange(false);setSession(null);setIdentity(null);}catch(e){setError(e instanceof Error?e.message:"No se ha podido cambiar la contraseña.");}finally{setBusy(false);}}

 return <Context.Provider value={{session}}><a className="skip" href="#main">Saltar al contenido</a>

 <header className="header"><Link className="brand" href="/"><span className="brand-mark"><Scale size={22}/></span><span>LAYA <span className="brand-secondary">Jurídico</span></span></Link><nav aria-label="Principal">{[["/","Consultas"],["/documents","Documentos"],["/coverage","Cobertura"]].map(([href,label])=><Link key={href} href={href} className={path===href?"nav-active":""}>{label}</Link>)}</nav><div className="session-label"><ShieldCheck size={16}/><span>Espacio privado</span>{session&&<Button disabled={busy} variant="ghost" onClick={logout} aria-label="Cerrar sesión"><LogOut size={17}/></Button>}</div></header>

 <div className="status-strip"><span className="status-dot"/> Entorno interno · La cobertura nacional aún no está verificada</div>

 <main id="main" className="main">{loading?<p role="status">Comprobando sesión…</p>:!session?<section className="login"><p className="eyebrow">Tu espacio de trabajo</p><h1>Consulta el derecho.<br/>Conserva la evidencia.</h1><p className="lead">Normativa oficial, versiones históricas y búsqueda a partir de tus documentos.</p><form onSubmit={connect} className="panel login-form"><h2>Entrar a tu espacio</h2><label>Correo electrónico<input required type="email" value={email} onChange={e=>setEmail(e.target.value)} autoComplete="username"/></label><label>Contraseña<input required type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/></label><p className="muted">Tu cuenta es privada. La sesión se conserva al recargar y caduca automáticamente.</p>{error&&<p role="alert" className="error">{error}</p>}<Button disabled={busy}>{busy?"Entrando…":"Entrar al espacio"}</Button></form></section>:<>

 <div className="workspace-account"><label>Espacio de trabajo<select aria-label="Espacio de trabajo" value={session.tenant_id} onChange={e=>{setSession({tenant_id:e.target.value,email:identity?.email,role:identity?.tenants.find(t=>t.id===e.target.value)?.role});setError("");}}>{identity?.tenants.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}</select></label><Button variant="ghost" onClick={()=>{setChange(!change);setPassword("");setNewPassword("");}}>Cambiar contraseña</Button></div>

 {error&&<p role="alert" className="error">{error}</p>}{change&&<form className="panel login-form" onSubmit={updatePassword}><h2>Cambiar contraseña</h2><label>Contraseña actual<input required type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label><label>Nueva contraseña (mínimo 12 caracteres)<input required minLength={12} type="password" autoComplete="new-password" value={newPassword} onChange={e=>setNewPassword(e.target.value)}/></label><p className="muted">Se cerrarán tus sesiones. Después podrás entrar con la nueva contraseña.</p><Button disabled={busy}>Guardar contraseña</Button></form>}<div key={session.tenant_id}>{children}</div></>}

 </main><footer className="footer"><span>LAYA Jurídico</span><p>Basado en datos de la <a href="https://www.boe.es" target="_blank" rel="noreferrer">Agencia Estatal Boletín Oficial del Estado</a>. Los textos consolidados son informativos.</p></footer></Context.Provider>;

}

