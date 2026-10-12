import type {Metadata} from "next";
import {Workspace} from "@/components/workspace";
import "./globals.css";
export const metadata:Metadata={title:"LAYA Jurídico · Búsqueda con evidencia",description:"Búsqueda privada de normativa oficial y versiones históricas."};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="es"><body><Workspace>{children}</Workspace></body></html>;}
