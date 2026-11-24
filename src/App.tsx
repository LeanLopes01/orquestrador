import { useEffect, useState } from 'react';
import { BookOpen, Blocks, ChevronRight, Database, FileText, FolderGit2, Network, Radio, ShieldCheck, type LucideIcon } from 'lucide-react';
import ContextPanel from './ContextPanel';
import ProjectsPanel from './ProjectsPanel';
import ProjectsErrorBoundary from './ProjectsErrorBoundary';
import IngestionPanel from './IngestionPanel';
import RagPanel from './RagPanel';
import ReportsPanel from './ReportsPanel';
import type { Page, Vault } from './domain';
import { JarvisHome, ConnectionsPanel, UpdatesPanel, RoutinesPanel, SystemPanel } from './JarvisHub';

// Relatórios é uma preparação explícita; as demais telas usam serviços reais.
const navigation:{id:Page;label:string;icon:LucideIcon}[]=[{id:'home',label:'Central Jarvis',icon:Blocks},{id:'projects',label:'Projects · Jarvis',icon:Radio},{id:'context',label:'Janela de contexto',icon:Network},{id:'rag',label:'RAG local',icon:Database},{id:'ingestion',label:'Ingestão de fontes',icon:BookOpen},{id:'reports',label:'Relatórios',icon:FileText},{id:'connections',label:'Contas e integrações',icon:ShieldCheck},{id:'routines',label:'Rotinas',icon:Radio},{id:'updates',label:'Atualizações',icon:FileText},{id:'system',label:'Sistema',icon:Blocks}];
const pageFromHash=():Page=>{const p=location.hash.slice(1);return navigation.some(n=>n.id===p)?p as Page:'home';};

export default function App(){
  const [page,setPage]=useState<Page>(pageFromHash);
  const [vault,setVault]=useState<Vault|null>(null),[contextIds,setContextIds]=useState<string[]>([]),[toast,setToast]=useState('');
  function go(p:Page){setPage(p);location.hash=p;}
  useEffect(()=>{const handler=()=>setPage(pageFromHash());window.addEventListener('hashchange',handler);return()=>window.removeEventListener('hashchange',handler);},[]);
  useEffect(()=>{if(!toast)return;const timer=setTimeout(()=>setToast(''),5000);return()=>clearTimeout(timer);},[toast]);
  const current=navigation.find(n=>n.id===page);
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#home" onClick={()=>go('home')}><span className="brand-mark"><Blocks size={23}/></span><span>J.A.R.V.I.S.<small>PERSONAL WORKSPACE</small></span></a>
      <div className="project-switch"><span className="project-icon"><Blocks size={20}/></span><span><strong>DiceVTT</strong><small>Unity · projeto local</small></span></div>
      <span className="nav-label">WORKSPACE</span><nav aria-label="Navegação principal">{navigation.map(n=><button key={n.id} aria-label={n.label} title={n.label} onClick={()=>go(n.id)} className={`nav-item ${page===n.id?'active':''}`} aria-current={page===n.id?'page':undefined}><n.icon size={18}/><span>{n.label}</span></button>)}</nav>
      <div className="sidebar-bottom"><div className="local-card"><span className="local-symbol"><ShieldCheck size={19}/></span><strong>Seu workspace, local.</strong><p>Você decide o que sai<br/>do seu computador.</p></div><div className="user-card"><div className="avatar user">LL</div><span>Workspace pessoal<small>Jarvis · v0.3</small></span><span className="online-dot"/></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><FolderGit2 size={16}/><span>DiceVTT</span><ChevronRight size={13}/><strong>{current?.label}</strong></div><div className="top-actions"><span className="connection"><i className="dot"/>{page==='projects'?'Local · Jarvis':page==='rag'?'Local · RAG':'Local'}</span><span className="avatar user small-avatar">LL</span></div></header>
    <main>
      {page==='home'&&<JarvisHome go={go}/>}
      {page==='connections'&&<ConnectionsPanel/>}
      {page==='updates'&&<UpdatesPanel/>}
      {page==='routines'&&<RoutinesPanel/>}
      {page==='system'&&<SystemPanel/>}
      {page==='projects'&&<ProjectsErrorBoundary><ProjectsPanel/></ProjectsErrorBoundary>}
      {page==='context'&&<ContextPanel vault={vault} setVault={setVault} selectedIds={contextIds} setSelectedIds={setContextIds} notify={setToast}/>}
      {page==='rag'&&<RagPanel/>}
      {page==='ingestion'&&<IngestionPanel/>}
      {page==='reports'&&<ReportsPanel/>}
      <footer className="workspace-footer"><span><ShieldCheck size={13}/> Mudanças no projeto só com sua aprovação</span><span>LOCAL FIRST <i/> UI v0.3</span></footer>
    </main></div>
    {toast&&<div className="toast" role="status">{toast}<button aria-label="Fechar notificação" onClick={()=>setToast('')}>×</button></div>}
  </div>;
}
