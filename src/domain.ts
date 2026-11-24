export type Page = 'home'|'projects'|'context'|'rag'|'ingestion'|'reports'|'connections'|'updates'|'routines'|'system';
export type Note = { id:string; title:string; body:string; hash:string; modified:string; status:string; links:string[]; group:string; ext?:string; category?:string; size?:number };
export type Vault = {root:string; readAt:string; notes:Note[]; edges:string[][]; truncated:boolean; warnings:string[]; kind:string};
export function download(name:string, data:string, type='text/plain') {
  const url=URL.createObjectURL(new Blob([data],{type})); const a=document.createElement('a'); a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
