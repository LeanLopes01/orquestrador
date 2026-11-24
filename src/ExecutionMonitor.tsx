import { useEffect, useState } from 'react';
import { Activity, Clock3, Terminal } from 'lucide-react';
import { activeJob, age, jobAgentName, label, tone, when, type Job, type Usage } from './projects';

const metric = (value: number | undefined) => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value.toLocaleString('pt-BR') : 'Não informado';
function UsageView({ usage }: { usage?: Usage }) {
  return <><dl className="usage-grid">
    <div><dt>Tokens de entrada</dt><dd>{metric(usage?.input_tokens)}</dd></div>
    <div><dt>Tokens de saída</dt><dd>{metric(usage?.output_tokens)}</dd></div>
    <div><dt>Custo (USD)</dt><dd>{typeof usage?.cost_usd === 'number' && Number.isFinite(usage.cost_usd) && usage.cost_usd >= 0 ? usage.cost_usd.toLocaleString('pt-BR', { style: 'currency', currency: 'USD', maximumFractionDigits: 4 }) : 'Não informado'}</dd></div>
  </dl>{usage?.model && <p className="muted">Modelo: {usage.model}</p>}{usage?.source && <p className="muted">Fonte: {usage.source}</p>}</>;
}
function JobDetail({ job, now }: { job: Job; now: number }) {
  const [tab, setTab] = useState('activity');
  const progress = job.progress;
  const last = job.updated_at ?? job.started_at;
  const stale = activeJob(job.state) && last != null && now - last >= 90;
  const tabs = [ ['activity', 'Atividade'], ['stdout', 'Saída'], ['stderr', 'Erros'], ['summary', 'Resumo de raciocínio'], ['usage', 'Uso'] ];
  return <article className="job-detail" aria-label={`Job ${job.id}`}>
    <header className="monitor-heading"><div><h3>{jobAgentName(job)} <span className={`badge ${tone(job.state)}`}>{label(job.state)}</span></h3><p className="muted">{job.purpose || 'Tarefa do orquestrador'} · <code>{job.id}</code></p></div>
      <span className="muted"><Clock3 size={13}/> {job.started_at ? (job.finished_at || activeJob(job.state) ? `Duração: ${age((job.finished_at ?? now) - job.started_at)}` : 'Duração indisponível · término não informado') : 'Início não informado'}</span></header>
    <p className="job-stage">{progress?.activity || (progress?.stage ? label(progress.stage) : 'O executor ainda não informou a etapa atual.')}</p>
    <p className="muted">{job.updated_at ? `Último sinal: ${when(job.updated_at)} · há ${age(now - job.updated_at)}` : 'Nenhum sinal de progresso recebido.'}</p>
    {stale && <p className="telemetry-warning" role="status">Sem atualização há {age(now - last!)}. Isso pode indicar espera ou perda de conexão; não confirma travamento. Confira a saída e os erros.</p>}
    <div className="monitor-tabs" role="group" aria-label={`Detalhes de ${jobAgentName(job)}`}>{tabs.map(([key, name]) => <button type="button" key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{name}{key === 'stderr' && progress?.stderr_tail && <span className="log-dot"/>}</button>)}</div>
    <div className="monitor-content">
      {tab === 'activity' && (progress?.events?.length ? <ol className="event-feed">{progress.events.map(event => <li key={event.id}><time>{when(event.at)}</time><span className="badge gray">{event.kind}</span><p>{event.text}</p></li>)}</ol> : <div className="monitor-empty"><Activity size={22}/><p>{progress?.stage ? `Etapa recebida: ${label(progress.stage)}.` : 'Aguardando atividade do executor.'}</p><small>A sequência de ferramentas e eventos ainda não foi enviada para esta tarefa.</small></div>)}
      {tab === 'stdout' && <><p className="muted">Trecho mais recente recebido do processo. O servidor pode limitar o histórico.</p><pre className="terminal-output">{progress?.stdout_tail || 'Nenhuma saída recebida. Alguns executores só enviam texto ao terminar.'}</pre></>}
      {tab === 'stderr' && <><p className="muted">Mensagens de stderr podem incluir avisos; não significam necessariamente falha.</p><pre className="terminal-output stderr-output">{progress?.stderr_tail || 'Nenhuma mensagem de erro recebida.'}</pre></>}
      {tab === 'summary' && <><p className="muted">Resumo de decisões disponibilizado pelo agente. O pensamento interno privado não é exposto.</p><pre>{progress?.reasoning_summary || 'Este executor ainda não forneceu um resumo de raciocínio.'}</pre></>}
      {tab === 'usage' && <><p className="muted">Consumo desta tarefa, informado pelo provedor.</p><UsageView usage={progress?.usage}/><p className="muted">Cotas da assinatura e limites da conta não são fornecidos por esta integração.</p></>}
    </div>
  </article>;
}
export default function ExecutionMonitor({ jobs }: { jobs: Job[] }) {
  const [filter, setFilter] = useState('Todos');
  const [now, setNow] = useState(Date.now() / 1000);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now() / 1000), 1000); return () => clearInterval(timer); }, []);
  const sorted = [...jobs].sort((a, b) => Number(activeJob(b.state)) - Number(activeJob(a.state)) || (b.started_at ?? b.updated_at ?? 0) - (a.started_at ?? a.updated_at ?? 0));
  const names = [...new Set(['Antigravity', 'Claude', 'Codex', ...jobs.map(job => jobAgentName(job))])];
  const shown = sorted.filter(job => filter === 'Todos' || jobAgentName(job) === filter);
  return <section className="execution-monitor" aria-label="Monitor dos agentes">
    <div className="monitor-heading"><div><span className="eyebrow">VISIBILIDADE DA EXECUÇÃO</span><h2><Terminal size={18}/> Monitor dos agentes</h2></div><span className="muted">{jobs.filter(job => activeJob(job.state)).length} em andamento · {jobs.length} jobs recebidos</span></div>
    <p className="muted">Dados da conversa selecionada. Consumo ausente aparece como não informado.</p>
    <div className="agent-monitor-grid">{names.map(name => {
      const matches = sorted.filter(job => jobAgentName(job) === name);
      const job = matches[0];
      return <button type="button" key={name} className={`agent-monitor-card ${filter === name ? 'selected' : ''}`} aria-pressed={filter === name} onClick={() => setFilter(filter === name ? 'Todos' : name)}>
        <span className="agent-card-title"><strong>{name}</strong><span className={`badge ${job ? tone(job.state) : 'gray'}`}>{job ? label(job.state) : 'Sem tarefa'}</span></span>
        <span className="agent-card-stage">{job?.progress?.activity || (job?.progress?.stage ? label(job.progress.stage) : 'Sem atividade informada')}</span>
        <span className="muted">{matches.length} jobs · {job?.updated_at ? `sinal há ${age(now - job.updated_at)}` : 'sem sinal recebido'}</span>
        <span className="agent-card-usage">Entrada / saída: {metric(job?.progress?.usage?.input_tokens)} / {metric(job?.progress?.usage?.output_tokens)}</span>
        <small>Tokens do job em destaque</small>
      </button>;
    })}</div>
    <div className="monitor-filter"><label htmlFor="agent-filter">Exibir jobs</label><select id="agent-filter" value={filter} onChange={event => setFilter(event.target.value)}>{['Todos', ...names].map(name => <option key={name}>{name}</option>)}</select></div>
    <div className="job-list">{shown.map(job => <JobDetail key={job.id} job={job} now={now}/>)}</div>
    {!shown.length && <div className="monitor-empty"><Terminal size={24}/><p>{jobs.length ? 'Nenhuma tarefa recebida para este agente.' : 'As tarefas aparecerão aqui quando o servidor as informar.'}</p><small>Você poderá acompanhar a etapa, os logs e o consumo disponível.</small></div>}
  </section>;
}
