import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import { RefreshCw, Search, FileText, Network, Layers, Plus, Check, X, Download, Database, AlertCircle, ZoomIn, ZoomOut } from 'lucide-react';
import { download, type Vault, type Note } from './domain';
import RagPanel from './RagPanel';

export function Graph({notes,edges,selected,onSelect,compact=false}:{notes:Note[];edges:string[][];selected?:string;onSelect?:(id:string)=>void;compact?:boolean}) {
  const [zoom,setZoom]=useState(1);
  const displayed=notes.slice(0,compact?22:80);
  const positions=new Map(displayed.map((n,i)=>{
    const angle=i*2.399963, radius= i===0?0:35+Math.sqrt(i)*22;
    return [n.id,{x:300+Math.cos(angle)*radius*1.25,y:180+Math.sin(angle)*radius*.78}];
  }));
  return <div className={`graph ${compact?'compact':''}`}>
    <svg viewBox="0 0 600 360" role="img" aria-label={`Grafo de ${displayed.length} notas e seus wikilinks`}>
      <defs><radialGradient id={compact?'glow-small':'glow'}><stop stopColor="#69d6ba" stopOpacity=".1"/><stop offset="1" stopColor="#69d6ba" stopOpacity="0"/></radialGradient></defs>
      <circle cx="300" cy="180" r="160" fill={`url(#${compact?'glow-small':'glow'})`}/>
      <g transform={`translate(300 180) scale(${zoom}) translate(-300 -180)`}>
      {edges.map(([a,b],i)=>{const p=positions.get(a),q=positions.get(b);return p&&q?<line key={i} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={selected===a||selected===b?'#75d7ba':'#344b44'} strokeWidth="1"/>:null;})}
      {displayed.map((n,i)=>{const p=positions.get(n.id)!;return <g key={n.id} role={onSelect?'button':undefined} tabIndex={onSelect?0:undefined} aria-label={n.title} onClick={()=>onSelect?.(n.id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onSelect?.(n.id);}}} className="graph-node">
        {selected===n.id&&<circle cx={p.x} cy={p.y} r="17" fill="#68dbb320" stroke="#68dbb3"/>}
        <circle cx={p.x} cy={p.y} r={i===0?8:4+(n.links.length%4)} fill={['#7bdcba','#879cdd','#b49acd','#d4b17b'][i%4]}/>
        {(!compact||i<5)&&<text x={p.x} y={p.y+20} textAnchor="middle" fill="#9aa9a3" fontSize="9">{n.title.slice(0,24)}</text>}
      </g>;})}</g>
    </svg>
    {!compact&&<div className="graph-controls"><button aria-label="Diminuir zoom" onClick={()=>setZoom(v=>Math.max(.6,v-.2))}><ZoomOut size={16}/></button><button onClick={()=>setZoom(1)}>{Math.round(zoom*100)}%</button><button aria-label="Aumentar zoom" onClick={()=>setZoom(v=>Math.min(2,v+.2))}><ZoomIn size={16}/></button></div>}
    {!notes.length&&<div className="graph-empty"><Network size={32}/><span>Carregue suas fontes para explorar as conexões.</span></div>}
  </div>;
}

export default function ContextPanel({vault,setVault,selectedIds,setSelectedIds,notify}:{vault:Vault|null;setVault:(v:Vault)=>void;selectedIds:string[];setSelectedIds:Dispatch<SetStateAction<string[]>>;notify:(s:string)=>void}) {
  const [loading,setLoading]=useState(false),[error,setError]=useState(''),[query,setQuery]=useState(''),[groupFilter,setGroupFilter]=useState('all'),[categoryFilter,setCategoryFilter]=useState('all'),[visibleCount,setVisibleCount]=useState(120),[active,setActive]=useState(''),[view,setView]=useState<'graph'|'list'>('graph'),[limit,setLimit]=useState(6000);
  const request=useRef<AbortController|null>(null);
  async function load(){request.current?.abort();const controller=new AbortController();request.current=controller;setLoading(true);setError('');try {const response=await fetch('/api/context',{signal:controller.signal});if(!response.ok)throw new Error('A leitura local está indisponível. Inicie com npm run dev ou npm run preview e confira o caminho do vault.');const data=await response.json() as Vault;if(controller.signal.aborted)return;if(!Array.isArray(data.notes))throw new Error('Resposta de contexto inválida.');setVault(data);setActive(current=>data.notes.some(n=>n.id===current)?current:data.notes[0]?.id||'');setSelectedIds(current=>current.filter(id=>data.notes.some(n=>n.id===id)));} catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Falha ao ler contexto.');}finally{if(!controller.signal.aborted)setLoading(false);}}
  useEffect(()=>{if(!vault)void load();return()=>request.current?.abort();},[]);
  const groups=useMemo(()=>{
    const counts=new Map<string,number>();
    for(const n of vault?.notes||[])counts.set(n.group,(counts.get(n.group)||0)+1);
    return [...counts.entries()].sort((a,b)=>b[1]-a[1]);
  },[vault]);
  const categories=useMemo(()=>{
    const counts=new Map<string,number>();
    for(const n of vault?.notes||[]){const c=n.category||'nota';counts.set(c,(counts.get(c)||0)+1);}
    return counts;
  },[vault]);
  const filtered=useMemo(()=>{
    const q=query.trim().toLowerCase();
    return (vault?.notes||[]).filter(n=>{
      if(groupFilter!=='all'&&n.group!==groupFilter)return false;
      if(categoryFilter!=='all'&&(n.category||'nota')!==categoryFilter)return false;
      if(!q)return true;
      return n.title.toLowerCase().includes(q)||n.id.toLowerCase().includes(q)||n.body.toLowerCase().includes(q);
    });
  },[vault,query,groupFilter,categoryFilter]);
  const visibleNotes=useMemo(()=>filtered.slice(0,visibleCount),[filtered,visibleCount]);
  const note=vault?.notes.find(n=>n.id===active);
  const selected=vault?.notes.filter(n=>selectedIds.includes(n.id))||[];
  const full=selected.map(n=>`Fonte: ${n.id}\nSHA256: ${n.hash}\nModificado: ${n.modified}\n\n${n.body}`).join('\n\n---\n\n');
  const windowText=full.slice(0,limit);
  function toggle(id:string){setSelectedIds(selectedIds.includes(id)?selectedIds.filter(x=>x!==id):[...selectedIds,id]);}
  return <>
    <div className="page-heading"><div><span className="eyebrow">MEMÓRIA DO PROJETO</span><h1>Janela de contexto</h1><p>Fontes rastreáveis. Só o contexto que a tarefa precisa.</p></div><button className="button" onClick={load} disabled={loading}><RefreshCw size={16} className={loading?'spin':''}/>{loading?'Lendo fontes…':'Atualizar fontes'}</button></div>
    <div className="notice"><Database size={17}/><span>Leitura local da sua Janela de Contexto Pessoal (notas, códigos, XMLs de regras, PDFs e documentos). Scripts C# do projeto Unity e documentação coletada também são consultados pelo RAG local, abaixo.</span><span className="badge mint">Somente leitura</span></div>
    {error&&<div className="notice error" role="alert"><AlertCircle size={17}/>{error}</div>}
    <div className="context-layout">
      <section className="panel sources"><div className="panel-heading"><h2>Fontes</h2><span className="count">{filtered.length}</span></div>
        <label className="search"><Search size={16}/><input aria-label="Buscar nas fontes" placeholder="Buscar título, caminho ou conteúdo…" value={query} onChange={e=>{setQuery(e.target.value);setVisibleCount(120);}}/></label>
        <div className="source-filters">
          <select aria-label="Filtrar por pasta" value={groupFilter} onChange={e=>{setGroupFilter(e.target.value);setVisibleCount(120);}}>
            <option value="all">Todas as pastas ({vault?.notes.length||0})</option>
            {groups.map(([g,c])=><option key={g} value={g}>{g} ({c})</option>)}
          </select>
          <select aria-label="Filtrar por tipo" value={categoryFilter} onChange={e=>{setCategoryFilter(e.target.value);setVisibleCount(120);}}>
            <option value="all">Todos os tipos ({vault?.notes.length||0})</option>
            <option value="nota">Notas .md / .txt ({categories.get('nota')||0})</option>
            <option value="codigo">Código .py / .cs / .ino ({categories.get('codigo')||0})</option>
            <option value="dados">Dados .xml / .json / .csv ({categories.get('dados')||0})</option>
            <option value="documento">Docs .pdf / .docx ({categories.get('documento')||0})</option>
          </select>
        </div>
        <div className="source-list">
          {visibleNotes.map(n=><button key={n.id} onClick={()=>setActive(n.id)} className={`source-row ${active===n.id?'selected':''}`}><FileText size={16}/><span><strong>{n.title}</strong><small>{n.group}{n.ext?` · ${n.ext}`:''}</small></span>{selectedIds.includes(n.id)&&<Check size={14} className="mint-text"/>}</button>)}
          {filtered.length>visibleCount&&<button className="button small full" onClick={()=>setVisibleCount(c=>c+250)}>Mostrar mais ({filtered.length-visibleCount} restantes)</button>}
          {!filtered.length&&<p className="empty">{loading?'Lendo notas locais…':'Nenhuma fonte encontrada.'}</p>}
        </div>
        <div className="panel-foot">{vault?.truncated?'Leitura limitada a 5.000 arquivos.':`${vault?.notes.length.toLocaleString('pt-BR')||0} arquivos lidos · ${groups.length} pastas`}</div>
      </section>
      <section className="panel graph-panel"><div className="panel-heading"><h2><Network size={17}/> Mapa de conhecimento</h2><div className="segmented"><button className={view==='graph'?'active':''} onClick={()=>setView('graph')}>Grafo</button><button className={view==='list'?'active':''} onClick={()=>setView('list')}>Conexões</button></div></div>
        {view==='graph'?<Graph notes={filtered} edges={vault?.edges||[]} selected={active} onSelect={setActive}/>:<div className="connections">{vault?.edges.filter(([a,b])=>filtered.some(n=>n.id===a||n.id===b)).map(([a,b],i)=><button key={i} onClick={()=>setActive(b)}>{a.replace('.md','')} <span>→</span> {b.replace('.md','')}</button>)}{!vault?.edges.length&&<p className="empty">Nenhum wikilink resolvido nas fontes lidas.</p>}</div>}
        <div className="graph-legend"><span><i className="dot"/>Arquivos locais</span><span>{Math.min(filtered.length,80)} nós visíveis (de {filtered.length})</span><span>{vault?.edges.length||0} conexões no vault lido</span></div>
        <div className="note-preview">{note?<><div className="panel-heading"><div><span className="eyebrow">FONTE ORIGINAL · {note.id}</span><h2>{note.title}</h2></div><button className={`button small ${selectedIds.includes(note.id)?'subtle':'primary'}`} onClick={()=>toggle(note.id)}>{selectedIds.includes(note.id)?<Check size={14}/>:<Plus size={14}/>} {selectedIds.includes(note.id)?'Selecionada':'Usar no contexto'}</button></div><div className="note-meta"><span className={`badge ${note.status==='processed'?'mint':'gray'}`}>{note.status==='processed'?'LightRAG: processada':note.status==='failed'?'LightRAG: falhou':note.status==='processing'?'LightRAG: processando':'Arquivo local'}</span>{note.size!==undefined&&<span className="badge gray">{(note.size/1024).toFixed(1)} KB</span>}<code title={note.hash}>sha256 {note.hash.slice(0,12)}</code></div><pre>{note.body.slice(0,12000)}</pre>{note.body.length>12000&&<small>Prévia limitada a 12.000 caracteres.</small>}</>:<p className="empty">Selecione uma nota para inspecionar sua origem.</p>}</div>
      </section>
      <section className="panel context-window"><div className="panel-heading"><h2><Layers size={17}/> Contexto da tarefa</h2>{selected.length>0&&<button className="text-button" onClick={()=>setSelectedIds([])}>Limpar ({selected.length})</button>}</div><p className="muted">Monte a janela que poderá acompanhar a próxima tarefa.</p><label className="field">Limite de caracteres<select value={limit} onChange={e=>setLimit(Number(e.target.value))}><option value={3000}>3.000 caracteres (~750 tokens)</option><option value={6000}>6.000 caracteres (~1,5 mil tokens)</option><option value={12000}>12.000 caracteres (~3 mil tokens)</option><option value={24000}>24.000 caracteres (~6 mil tokens)</option><option value={50000}>50.000 caracteres (~12,5 mil tokens)</option><option value={100000}>100.000 caracteres (~25 mil tokens)</option><option value={200000}>200.000 caracteres (~50 mil tokens)</option><option value={500000}>500.000 caracteres (~125 mil tokens)</option></select></label><div className="budget-line"><strong>{windowText.length.toLocaleString('pt-BR')}</strong><span>/ {limit.toLocaleString('pt-BR')} (~{Math.ceil(windowText.length/4).toLocaleString('pt-BR')} tok)</span></div><div className="progress"><i style={{width:`${Math.min(full.length/limit*100,100)}%`}}/></div><small>Limite textual. Tokens dependem do modelo.</small>
        <div className="selected-notes">{selected.map(n=><div key={n.id}><FileText size={15}/><span>{n.title}</span><button aria-label={`Remover ${n.title}`} onClick={()=>toggle(n.id)}><X size={14}/></button></div>)}{!selected.length&&<div className="empty"><Layers size={26}/><p>Adicione fontes a partir do grafo ou da lista.</p></div>}</div>
        {full.length>limit&&<p className="warning-text">O pacote será truncado em {limit.toLocaleString('pt-BR')} caracteres. Revise a prévia antes de usar.</p>}
        <details><summary>Ver pacote de contexto</summary><pre className="context-output">{windowText||'Nenhuma fonte selecionada.'}</pre></details>
        <button className="button full" disabled={!selected.length} onClick={()=>{download('contexto-tarefa.txt',windowText);notify('Janela exportada localmente.');}}><Download size={15}/> Exportar contexto</button>
        <div className="privacy-note"><Check size={14}/> Nenhuma fonte enviada a modelos.</div>
      </section>
    </div>
    {vault&&<div className="context-footer"><span>Origem: <code>{vault.root}</code></span><span>Lido em {new Date(vault.readAt).toLocaleString('pt-BR')}</span></div>}
    {vault?.warnings.map((w,i)=><p className="warning-text" key={i}>{w}</p>)}
    <RagPanel embedded/>
  </>;
}
