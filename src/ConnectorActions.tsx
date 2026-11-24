import { useEffect, useState } from 'react';

type Plan={id:string;connection:string;tool:string;arguments:unknown;digest:string;message:string};
async function request(path:string,method='GET',body?:unknown){
 const response=await fetch('/api/orchestrator/v1/'+path,{method,headers:{'Content-Type':'application/json','X-Orchestrator-Request':'1'},body:body===undefined?undefined:JSON.stringify(body)});
 const value=await response.json().catch(()=>({message:`HTTP ${response.status}`}));
 if(!response.ok)throw Error(value.message||`HTTP ${response.status}`);
 return value;
}
export default function ConnectorActions({id,tools}:{id:string;tools:string[]}){
 const [enabled,setEnabled]=useState(false),[installed,setInstalled]=useState(false),[tool,setTool]=useState(tools[0]||''),[args,setArgs]=useState('{}'),[plan,setPlan]=useState<Plan|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[call,setCall]=useState('');
 useEffect(()=>{let mounted=true;void request('extensions').then(v=>{const entry=v.entries.find((e:{id:string})=>e.id===id);if(mounted){setInstalled(!!entry&&v.configured);setEnabled(!!entry?.enabled);}}).catch(()=>{if(mounted)setMessage('Instale o pacote do servidor para usar este conector.');});return()=>{mounted=false;};},[id]);
 async function action(fn:()=>Promise<void>){setBusy(true);setMessage('');try{await fn();}catch(e){setMessage(String(e));}finally{setBusy(false);}}
 return <div className="connector-actions"><h3>Usar no servidor</h3><p>Primeiro preencha a credencial deste conector no n8n. Habilitar permite preparar chamadas; não confirma que a conta foi autorizada.</p><button className="button secondary" disabled={!installed||busy} onClick={()=>void action(async()=>{await request(`extensions/${id}`,'PATCH',{enabled:!enabled});setEnabled(!enabled);setPlan(null);})}>{enabled?'Pausar conector':'Habilitar após configurar'}</button>
 {enabled&&<><label>Ferramenta<select value={tool} onChange={e=>{setTool(e.target.value);setPlan(null);}}>{tools.map(t=><option key={t}>{t}</option>)}</select></label><label>Argumentos JSON<textarea rows={5} value={args} onChange={e=>{setArgs(e.target.value);setPlan(null);}} spellCheck={false}/></label><button className="button secondary" disabled={busy} onClick={()=>void action(async()=>{const parsed=JSON.parse(args);setPlan(await request(`extensions/${id}/prepare`,'POST',{tool,arguments:parsed}));})}>Preparar chamada</button></>}
 {plan&&<div className="notice"><strong>{plan.connection} · {plan.tool}</strong><pre>{JSON.stringify(plan.arguments,null,2)}</pre><p>{plan.message}</p><button className="button primary" disabled={busy} onClick={()=>void action(async()=>{const id=plan.id;setCall(id);const result=await request(`extension-calls/${id}/execute`,'POST',{digest:plan.digest});setPlan(null);setMessage(JSON.stringify(result,null,2));})}>Confirmar esta execução</button></div>}
 {call&&<button className="button secondary" disabled={busy} onClick={()=>void action(async()=>{setMessage(JSON.stringify(await request(`extension-calls/${call}`),null,2));})}>Consultar resultado sem repetir</button>}
 {message&&<pre role="status" className="connector-result">{message}</pre>}
 </div>;
}
