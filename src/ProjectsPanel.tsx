import { useCallback, useEffect, useRef, useState } from 'react';
import { Radio, RefreshCw, Send, ShieldCheck } from 'lucide-react';
import ExecutionMonitor from './ExecutionMonitor';
import PlanReview from './PlanReview';
import { api, label, when, type Conversation, type Item, type Plan, type Runtime } from './projects';
import './projects.css';
import ProjectPipeline, { loadPipeline, type Pipeline } from './ProjectPipeline';

export default function ProjectsPanel() {
  const [items, setItems] = useState<Item[]>([]);
  const [current, setCurrent] = useState<Conversation | null>(null);
  const [id, setId] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<boolean | null>(null);
  const [routing, setRouting] = useState<Runtime['planning_routing']>();
  const [pipeline, setPipeline] = useState<Pipeline>(loadPipeline);
  const planningAgent = pipeline.planning.agent;
  const executionAgent = pipeline.coding.agent;
  function changePipeline(value: Pipeline) {
    setPipeline(value);
    try { localStorage.setItem('orq.project-pipeline.v1', JSON.stringify(value)); } catch { /* Session still works. */ }
  }
  const [connectionError, setConnectionError] = useState('');
  const [actionError, setActionError] = useState('');
  const [receipt, setReceipt] = useState('');
  const [text, setText] = useState(() => sessionStorage.getItem('jarvis.project.prompt') || '');
  useEffect(() => { sessionStorage.removeItem('jarvis.project.prompt'); }, []);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const [fresh, setFresh] = useState(false);
  const [now, setNow] = useState(Date.now());
  const selected = useRef(id);
  const sequence = useRef(0);
  const inFlight = useRef<number | null>(null);
  const working = useRef(false);
  const pending = useRef<{ text: string; id: string | null; pipelineKey: string; request_id: string } | null>(null);
  const refresh = useCallback(async () => {
    if (inFlight.current === sequence.current) return;
    const request = ++sequence.current;
    inFlight.current = request;
    const target = selected.current;
    setRefreshing(true);
    const [list, status, conversation] = await Promise.allSettled([
      api<{ conversations: Item[] }>('conversations'),
      api<Runtime>('orchestration/runtime'),
      target ? api<Conversation>(`conversations/${target}`) : Promise.resolve(null),
    ]);
    if (request !== sequence.current || selected.current !== target) return;
    if (list.status === 'fulfilled') setItems(list.value.conversations);
    setRuntime(status.status === 'fulfilled' ? status.value.online : null);
    setRouting(status.status === 'fulfilled' ? status.value.planning_routing : undefined);
    if (conversation.status === 'fulfilled') {
      setCurrent(conversation.value); setFresh(true); setSyncedAt(Date.now());
    } else setFresh(false);
    const failure = [list, status, conversation].find(result => result.status === 'rejected');
    setConnectionError(failure?.status === 'rejected' ? `Falha ao atualizar. ${String(failure.reason instanceof Error ? failure.reason.message : failure.reason)} Os dados já recebidos continuam visíveis.` : '');
    setRefreshing(false);
    inFlight.current = null;
  }, []);
  useEffect(() => {
    if (!working.current) void refresh();
    const timer = setInterval(() => { if (!working.current) void refresh(); }, 5000);
    return () => { clearInterval(timer); sequence.current++; };
  }, [id, refresh]);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const freshEnough = fresh && syncedAt !== null && now - syncedAt < 30000;
  const supportedExecutors = routing?.execution_agents?.length ? routing.execution_agents : routing?.execution_agent ? [routing.execution_agent] : [];
  const routingReady = routing?.version === 1 && Array.isArray(routing.agents) && routing.agents.some(agent => agent === planningAgent) && supportedExecutors.includes(executionAgent) && routing.pipeline_version === 1 && (!pipeline.ui.enabled || supportedExecutors.includes(pipeline.ui.agent));
  function choose(next: string | null) {
    sequence.current++; selected.current = next;
    setId(next); setCurrent(null); setText(''); setFresh(false); setSyncedAt(null); setActionError(''); setReceipt('');
    if (next === id) void refresh();
  }
  function begin() {
    if (working.current) return false;
    working.current = true; sequence.current++; setRefreshing(false); setBusy(true); setActionError(''); setReceipt(''); return true;
  }
  async function finish() { working.current = false; setBusy(false); await refresh(); }
  async function send() {
    if (!text.trim() || runtime !== true || !routingReady || !freshEnough || !begin()) return;
    if (pending.current?.text !== text || pending.current?.id !== id || pending.current?.pipelineKey !== JSON.stringify(pipeline)) pending.current = { text, id, pipelineKey: JSON.stringify(pipeline), request_id: crypto.randomUUID() };
    try {
      const conv = await api<Conversation>(id ? `conversations/${id}/messages` : 'conversations', { project: 'dicevtt', text: text.trim(), request_id: pending.current.request_id, planning_agent: planningAgent, execution_agent: executionAgent, routing_version: 1, pipeline });
      pending.current = null; setText(''); selected.current = conv.id; setId(conv.id); setCurrent(conv); setReceipt('Pedido recebido pelo Jarvis.');
    } catch (error) { setActionError((error as Error).message); }
    finally { await finish(); }
  }
  async function decide(plan: Plan, decision: 'approve' | 'reject') {
    if (!freshEnough || (decision === 'approve' && runtime !== true) || !begin()) return;
    try {
      await api(`plans/${plan.id}/${decision}`, { version: plan.version, hash: plan.hash });
      setFresh(false);
      setReceipt(decision === 'approve' ? `Aprovação do plano ${plan.version} registrada. Acompanhe o despacho no monitor dos agentes.` : `Plano ${plan.version} rejeitado.`);
    } catch (error) { setActionError((error as Error).message); setFresh(false); }
    finally { await finish(); }
  }
  async function cancel(runId: string) {
    if (!begin()) return;
    try { await api(`runs/${runId}/cancel`, {}); setReceipt('Cancelamento solicitado. Acompanhe a confirmação no estado da execução.'); }
    catch (error) { setActionError((error as Error).message); }
    finally { await finish(); }
  }
  const plans = [...(current?.plans || [])].sort((a, b) => b.version - a.version);
  const proposed = plans.filter(plan => plan.state === 'proposed');
  return <div className={`projects-page ${proposed.length ? 'has-pending-plan' : ''}`}>
    <div className="page-heading"><div><span className="eyebrow">JARVIS · PEDIDOS REAIS</span><h1>Projects · DiceVTT</h1><p>Planos, agentes e resultados em um só lugar.</p></div><button className="button" disabled={refreshing || busy} onClick={() => void refresh()}><RefreshCw size={16} className={refreshing ? 'spin' : ''}/>{refreshing ? 'Atualizando…' : 'Atualizar'}</button></div>
    <div className="jarvis-banner"><Radio size={24}/><div><h2>{runtime === true ? 'Orquestrador disponível neste PC' : runtime === false ? 'Executor local indisponível' : 'Conexão com o executor não confirmada'}</h2><p>O Jarvis guarda as conversas. Para novos pedidos e execução, mantenha o Orquestrador e o helper abertos no PC.</p></div><span className={`badge ${runtime ? 'mint' : 'yellow'}`}>{runtime ? 'Conectado' : runtime === false ? 'Offline' : 'Sem confirmação'}</span></div>
    <p className="sync-status">Consulta automática a cada 5 s · {syncedAt ? `última leitura: ${when(syncedAt / 1000)}` : 'aguardando primeira leitura'} · o estado salvo não comprova atividade do processo.</p>
    {connectionError && <div className="notice" role="alert">{connectionError}</div>}
    <div className="projects-layout">
      <aside className="panel projects-list"><div className="monitor-heading"><h2>Conversas</h2><span className="muted">{items.length}</span></div><button className="button primary full" disabled={busy} onClick={() => choose(null)}>Novo pedido</button>
        {items.map(item => <button className={`report-item ${id === item.id ? 'selected' : ''}`} disabled={busy} key={item.id} onClick={() => { if (id !== item.id) choose(item.id); }}><span><strong>{item.title}</strong><small>{label(item.state)} · {when(item.updated_at)}</small></span></button>)}
        {!items.length && <p className="muted">As conversas reais aparecerão aqui após a conexão.</p>}
      </aside>
      <section className="panel projects-conversation">
        <div className="conversation-heading"><h2>{current?.title || (id ? 'Carregando conversa…' : 'O que vamos fazer no DiceVTT?')}</h2>{current && <span className="badge blue">{label(current.state)}</span>}</div>
        {actionError && <div className="notice action-error" role="alert"><p>{actionError}</p><button type="button" aria-label="Fechar erro da ação" onClick={() => setActionError('')}>×</button></div>}
        {receipt && <p className="action-receipt" role="status">{receipt}</p>}
        {proposed.map(plan => <PlanReview key={plan.id} plan={plan} busy={busy} runtime={runtime} fresh={freshEnough} onDecide={(plan, decision) => void decide(plan, decision)}/>)}
        {current && <ExecutionMonitor key={current.id} jobs={current.jobs || []}/>}
        {!!current?.messages.length && <h3 className="conversation-section-title">Conversa com o Jarvis</h3>}
        {current?.messages.map(message => <article className="project-message" key={message.seq}><small>{message.author === 'user' ? 'Você' : message.author}</small><p>{message.text}</p></article>)}
        {plans.some(plan => plan.state !== 'proposed') && <details className="plan-history"><summary>Histórico de planos ({plans.filter(plan => plan.state !== 'proposed').length})</summary>{plans.filter(plan => plan.state !== 'proposed').map(plan => <PlanReview key={plan.id} plan={plan} busy={busy} runtime={runtime} fresh={freshEnough} onDecide={(plan, decision) => void decide(plan, decision)}/>)}</details>}
        {current?.runs.map(run => <article className="project-message" key={run.id}><h3>Execução · {label(run.state)}</h3><p className="muted">{run.id}</p><details><summary>Relatório e tarefas</summary><pre>{JSON.stringify(run.report || run.tasks, null, 2)}</pre></details>{['running', 'reviewing'].includes(run.state) && <button className="button" disabled={busy} onClick={() => void cancel(run.id)}>Cancelar execução</button>}</article>)}
        <form onSubmit={event => { event.preventDefault(); void send(); }} className="project-input">
          <ProjectPipeline value={pipeline} onChange={changePipeline} disabled={busy}/>
          {!routingReady && <p className="planning-warning" role="status">O servidor e o helper precisam confirmar suporte às três etapas para enviar. Suas escolhas ficam salvas neste navegador.</p>}
          <label className="field">{id ? 'Continuar conversa' : 'Novo pedido'}<textarea aria-label="Pedido para o Jarvis" disabled={busy} rows={4} maxLength={6000} value={text} onChange={event => setText(event.target.value)} placeholder="Descreva o objetivo e como saberemos que está pronto…"/></label>
          <button className="button primary" disabled={busy || runtime !== true || !routingReady || !freshEnough || !text.trim()}><Send size={16}/>{busy ? 'Aguarde…' : 'Enviar ao Jarvis'}</button>
          <p className="muted">{runtime !== true ? 'O envio ficará disponível quando a conexão com o executor for confirmada.' : 'O plano volta para sua aprovação. A aplicação das mudanças ao projeto continua sendo uma decisão separada.'}</p>
        </form>
      </section>
    </div>
    {!!proposed.length && <a className="mobile-plan-shortcut" href={`#plan-${proposed[0].id}`} onClick={event => { event.preventDefault(); const target = document.getElementById(`plan-${proposed[0].id}`); target?.scrollIntoView({ block: 'start' }); target?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus({ preventScroll: true }); }}><ShieldCheck size={19}/><span>Plano {proposed[0].version} aguarda sua decisão</span><strong>Revisar</strong></a>}
  </div>;
}
