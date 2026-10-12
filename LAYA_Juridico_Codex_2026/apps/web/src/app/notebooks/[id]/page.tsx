"use client";
import {useParams} from "next/navigation";
import {NotebookEditor} from "@/components/notebook-editor";
export default function Notebook(){const {id}=useParams<{id:string}>();return <NotebookEditor id={id}/>;}
