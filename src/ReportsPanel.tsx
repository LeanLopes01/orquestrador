import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, ArrowRight, Bot, Boxes, Check, ChevronRight, CircleAlert, ClipboardList, Clock3, ExternalLink, FileCheck2, FileText, FolderOpen, GitBranch, HardDrive, Laptop, LoaderCircle, Network, Play, RefreshCw, Save, Server, Settings2, ShieldCheck, Sparkles, Square, Upload, Workflow, XCircle } from 'lucide-react';
import { download } from './domain';
import { ServiceError } from './rag';
import {
  audits, checkLabel, comparisonLabel, editable, exampleReport, formatLocal, LAST_KNOWN_KEY, LEGACY_DRAFT_KEY, parseImportedSettings,
  hypothesisLabel, investigationLabel, reportUrl, runStateBadge, runStateLabel, safeWorkflowUrl, settingsExport, severityBadge,
  severityLabel, startupOutcomeLabel, triggerLabel, validatorLabel, workflowSteps, type AuditHealth, type AuditSettings,
  type CheckStatus, type EditableSettings, type Investigation, type Profile, type ReportFinding, type RunDetail, type RunRow,
  type Severity, type SubmitResult, type ValidatorOutcome,
} from './reports';
import handoff from '../docs/plano-relatorios-automaticos-claude.md?raw';
import './reports.css';

type ReportView = 'overview' | 'routine' | 'flow';
type LastKnown = { id: string; state: RunRow['state']; finished_at: string | null; findings: number | null; seen_at: string };

const ACTIVE = new Set(['queued', 'collecting']);
const INVESTIGATING = new Set(['queued', 'running']);
const message = (error: unknown) => error instanceof Error ? error.message : String(error);

function readLastKnown(): LastKnown | null {
  try { return JSON.parse(localStorage.getItem(LAST_KNOWN_KEY) || 'null'); } catch { return null; }
}
function rememberRun(run: RunRow | null) {
  if (!run) return;
  try { localStorage.setItem(LAST_KNOWN_KEY, JSON.stringify({ id: run.id, state: run.state, finished_at: run.finished_at, findings: run.summary?.findings ?? null, seen_at: new Date().toISOString() })); } catch { /* conveniência opcional */ }
}

function CheckIcon({ status }: { status: CheckStatus | string }) {
  return <span className={`audit-check-icon ${status}`}>{status === 'collected' || status === 'passed' ? <Check size={15}/> : status === 'error' ? <XCircle size={15}/> : status === 'partial' ? <CircleAlert size={15}/> : <Clock3 size={15}/>}</span>;
}

function FindingItem({ finding, evidence }: { finding: ReportFinding; evidence: Map<string, { source: string; detail: string; sha256: string | null }> }) {
  const gone = finding.comparison === 'resolved' || finding.comparison === 'not_rechecked';
  return <details className={`audit-finding sev-${finding.severity} ${gone ? 'gone' : ''}`}>
    <summary><span className={`badge ${severityBadge[finding.severity]}`}>{severityLabel[finding.severity]}</span><span>{finding.summary}<small>{comparisonLabel[finding.comparison]} · {finding.state === 'confirmed' ? 'Confirmada por evidência' : 'Suspeita: evidência possivelmente desatualizada'}{finding.occurrences > 1 ? ` · ${finding.occurrences} ocorrências` : ''}</small></span><ChevronRight size={16}/></summary>
    <div>
      <p><strong>Regra:</strong> <code>{finding.rule}</code>{finding.file && <> · <strong>Local:</strong> <code>{finding.file}{finding.line ? `:${finding.line}` : ''}</code></>}</p>
      {finding.recommendation && <pre className="audit-advice">{finding.recommendation}</pre>}
      {finding.evidence.length > 0 && <ul className="audit-evidence">{finding.evidence.map(id => { const item = evidence.get(id); return item ? <li key={id}><code>{item.source}</code> {item.detail}{item.sha256 ? <small> · sha256 {item.sha256.slice(0, 12)}</small> : null}</li> : null; })}</ul>}
      {gone && <p className="muted">{finding.comparison === 'resolved' ? 'Não apareceu nesta coleta, e o check correspondente foi coletado por inteiro.' : 'O check correspondente não foi coletado por inteiro nesta execução; a ocorrência pode continuar existindo.'}</p>}
    </div>
  </details>;
}

function ValidatorsTable({ items }: { items: ValidatorOutcome[] }) {
  return <ul className="audit-validators" aria-label="Validadores do projeto">{items.map(v => <li key={v.id}>
    <span className={`badge ${v.status === 'passed' ? 'mint' : v.status === 'failed' ? 'red' : 'yellow'}`}>{validatorLabel[v.status]}</span>
    <span><strong>{v.name}</strong><small>{v.result ?? v.note ?? ''}{v.duration_ms ? ` · ${Math.round(v.duration_ms / 1000)} s` : ''}{v.failures ? ` · ${v.failures} falha(s)` : ''}</small></span>
  </li>)}</ul>;
}

function InvestigationPanel({ investigation, canRequest, requesting, onRequest }: { investigation?: Investigation; canRequest: boolean; requesting: boolean; onRequest: () => void }) {
  const result = investigation?.result;
  const active = investigation ? INVESTIGATING.has(investigation.state) : false;
  const retry = investigation && !active && investigation.state !== 'completed';
  return <section className="audit-investigation" aria-label="Investigação por IA">
    <div className="audit-finding-heading"><h3><Bot size={15}/> Investigação por IA</h3>
      {investigation && <span className="badge gray">{investigationLabel[investigation.state]}</span>}</div>
    {!investigation && <p className="muted">Sem investigação. As hipóteses ficam à parte do relatório e nunca confirmam uma ocorrência sozinhas.</p>}
    {investigation && <p className="muted">{investigation.provider === 'claude-code' ? 'Claude Code' : 'Modelo local (AirLLM via RAG)'}{investigation.model ? ` · ${investigation.model}` : ''}{investigation.prompt_version ? ` · prompt ${investigation.prompt_version}` : ''} · tentativa {investigation.attempt}{active ? ` · ${investigation.findings_done}/${investigation.findings_total || '?'} ocorrências` : ''}</p>}
    {investigation?.error && <p className="audit-inline-warning"><CircleAlert size={16}/>{investigation.error}</p>}
    {investigation?.result_error && <p className="audit-inline-warning" role="alert"><CircleAlert size={16}/>{investigation.result_error}</p>}
    {result?.data_left_pc && <p className="audit-inline-warning"><CircleAlert size={16}/>Trechos do código foram enviados ao provedor, como autorizado nas preferências.</p>}
    {result?.items.map(item => <details key={item.fingerprint} className={`audit-finding audit-hypothesis ${item.status}`}>
      <summary><span className={`badge ${item.status === 'supported' ? 'blue' : 'gray'}`}>{hypothesisLabel[item.status]}</span><span>{item.finding_summary}<small>{item.confidence ? `Confiança declarada: ${item.confidence} · ` : ''}{item.duration_ms ? `${Math.round(item.duration_ms / 1000)} s` : ''}</small></span><ChevronRight size={16}/></summary>
      <div>
        {item.hypothesis && <pre className="audit-advice">{item.hypothesis}</pre>}
        {item.error && <p className="muted">{item.error}</p>}
        {item.sources && item.sources.length > 0 && <ul className="audit-evidence">{item.sources.map((source, i) => <li key={i}>{source.ref ? `[${source.ref}] ` : ''}<code>{source.path ?? '—'}{source.lines ? `:${source.lines[0]}-${source.lines[1]}` : ''}</code>{source.valid ? '' : <small> · fonte inexistente, desconsiderada</small>}</li>)}</ul>}
        {item.suggested_checks && item.suggested_checks.length > 0 && <><p><strong>Como confirmar:</strong></p><ul className="audit-evidence">{item.suggested_checks.map((c, i) => <li key={i}>{c}</li>)}</ul></>}
      </div>
    </details>)}
    {result && <p className="muted">{result.note}</p>}
    {(!investigation || retry) && canRequest && <button className="button small" disabled={requesting} onClick={onRequest}><Bot size={13}/>{requesting ? 'Pedindo…' : retry ? 'Investigar de novo' : 'Investigar com IA'}</button>}
  </section>;
}

function RunDetailPanel({ detail, onCancel, cancelling, onInvestigate, requesting }: { detail: RunDetail; onCancel: () => void; cancelling: boolean; onInvestigate: () => void; requesting: boolean }) {
  const [severity, setSeverity] = useState<'all' | Severity>('all');
  const [showGone, setShowGone] = useState(false);
  const report = detail.report;
  const active = ACTIVE.has(detail.state);
  const evidence = new Map((report?.checks ?? []).flatMap(c => c.evidence.map(e => [e.id, e] as const)));
  const findings = (report?.findings ?? []).filter(f => (severity === 'all' || f.severity === severity) && (showGone || f.comparison === 'new' || f.comparison === 'recurring'));
  const goneCount = (report?.findings ?? []).filter(f => f.comparison === 'resolved' || f.comparison === 'not_rechecked').length;
  const checks = report?.checks ?? detail.checks.map(c => ({ ...c, problems: [] as string[], evidence: [] }));
  const rev = detail.revision ?? report?.revision;
  return <section className="panel audit-detail" aria-label={`Relatório ${detail.id}`}>
    <div className="panel-heading"><h2><FileCheck2 size={17}/> {detail.id}</h2><span className={`badge ${runStateBadge[detail.state]}`}>{runStateLabel[detail.state]}</span></div>
    <div className="audit-detail-body">
      <dl className="audit-kv">
        <div><dt>Disparo</dt><dd>{triggerLabel[detail.trigger] ?? detail.trigger}{detail.startup_ids.length > 1 ? ` · ${detail.startup_ids.length} pedidos agregados` : ''}</dd></div>
        <div><dt>Perfil</dt><dd>{detail.profile === 'startup-light' ? 'Leve' : 'Completo'}</dd></div>
        <div><dt>Início · fim</dt><dd>{formatLocal(detail.started_at)} · {active ? 'em andamento' : formatLocal(detail.finished_at)}</dd></div>
        <div><dt>Revisão analisada</dt><dd>{rev ? <>{rev.plastic ? `Unity VCS ${rev.plastic.branch ?? '?'} · cs ${rev.plastic.changeset ?? '?'} · ${rev.plastic.pending ?? '?'} pendente(s)` : rev.vcs ?? 'sem controle de versão'} · <code>{rev.source_state}</code></> : '—'}</dd></div>
        <div><dt>Sincronização</dt><dd>Somente neste PC <small>(envio ao servidor ainda não implementado)</small></dd></div>
      </dl>
      {active && <div className="audit-progress" role="status"><LoaderCircle size={15} className="spin"/>Coletando: {detail.checks_done} de {detail.checks_total} checks concluídos.<button className="button small" disabled={cancelling} onClick={onCancel}><Square size={12}/>{cancelling ? 'Cancelando…' : 'Cancelar'}</button></div>}
      {detail.error && <p className="audit-inline-warning" role="alert"><CircleAlert size={16}/>{detail.error}</p>}
      {detail.report_error && <p className="audit-inline-warning" role="alert"><CircleAlert size={16}/>{detail.report_error}</p>}
      {report && <div className="audit-metrics compact">
        <div className="audit-metric"><span>Ocorrências atuais</span><strong>{report.summary.findings}</strong><small>alta {report.summary.by_severity.high} · média {report.summary.by_severity.medium} · baixa {report.summary.by_severity.low} · info {report.summary.by_severity.info}</small></div>
        <div className="audit-metric"><span>Comparação</span><strong>{report.summary.new} novas</strong><small>{report.summary.recurring} recorrentes · {report.summary.resolved} resolvidas · {report.summary.not_rechecked} não reverificadas</small></div>
        <div className="audit-metric"><span>Cobertura</span><strong>{report.summary.coverage.collected}/{report.checks.length}</strong><small>parciais {report.summary.coverage.partial} · erros {report.summary.coverage.error} · não executados {report.summary.coverage.skipped}</small></div>
      </div>}
      <h3 className="audit-subtitle">Verificações</h3>
      <div className="audit-checks">{checks.length ? checks.map(check => <div key={check.id}><CheckIcon status={check.status}/><span><strong>{check.name}</strong><small>{check.note}</small>{check.problems.map((p, i) => <small key={i} className="audit-problem">{p}</small>)}{'data' in check && check.data?.validators ? <ValidatorsTable items={check.data.validators}/> : null}</span><span className="badge gray">{checkLabel[check.status]}</span></div>) : <p className="muted">Nenhum check concluído ainda.</p>}</div>
      {report && <>
        <div className="audit-finding-heading"><h3>Ocorrências</h3><div className="audit-filters">
          <label>Gravidade<select aria-label="Filtrar gravidade" value={severity} onChange={e => setSeverity(e.target.value as 'all' | Severity)}><option value="all">Todas</option><option value="high">Alta</option><option value="medium">Média</option><option value="low">Baixa</option><option value="info">Informativa</option></select></label>
          {goneCount > 0 && <label className="audit-check-toggle"><input type="checkbox" checked={showGone} onChange={e => setShowGone(e.target.checked)}/>Resolvidas e não reverificadas ({goneCount})</label>}
        </div></div>
        {findings.length ? findings.map(f => <FindingItem key={f.fingerprint} finding={f} evidence={evidence}/>) : <p className="audit-no-findings">{report.findings.length ? 'Nenhuma ocorrência neste filtro.' : 'Nenhuma ocorrência nos checks coletados. Checks parciais ou não executados não contam como aprovação.'}</p>}
        <div className="audit-example-footer"><span>Gerado em {formatLocal(report.finished_at)} · relatório conferido por hash.</span><span className="audit-actions">
          <a className="button small" href={reportUrl(detail.id, 'html')} download={`${detail.id}.html`}><ArrowDownToLine size={13}/>HTML</a>
          <a className="button small" href={reportUrl(detail.id, 'json')} download={`${detail.id}.json`}><ArrowDownToLine size={13}/>JSON</a>
        </span></div>
        <InvestigationPanel investigation={detail.investigation} canRequest={detail.state === 'completed' || detail.state === 'partial'} requesting={requesting} onRequest={onInvestigate}/>
      </>}
    </div>
  </section>;
}

export default function ReportsPanel() {
  const [view, setView] = useState<ReportView>('overview');
  const [health, setHealth] = useState<AuditHealth | null>(null);
  const [offline, setOffline] = useState('');
  const [lastKnown] = useState(readLastKnown);
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [stateFilter, setStateFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [pending, setPending] = useState<{ key: string; profile: Profile | null } | null>(null);
  const [requesting, setRequesting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const [preview, setPreview] = useState(false);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<EditableSettings | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const activeCount = health?.active.length ?? 0;
  const wasActive = useRef(0);

  const refreshHealth = useCallback(async () => {
    try {
      const data = await audits<AuditHealth>('health');
      setHealth(data); setOffline('');
      rememberRun(data.last_run);
      return data;
    } catch (e) { setOffline(message(e)); return null; }
  }, []);

  const loadRuns = useCallback(async (more = false, after: string | null = null) => {
    const params = new URLSearchParams({ limit: '10' });
    if (stateFilter) params.set('state', stateFilter);
    if (severityFilter) params.set('severity', severityFilter);
    if (more && after) params.set('cursor', after);
    try {
      const page = await audits<{ items: RunRow[]; next_cursor: string | null }>(`runs?${params}`);
      setRuns(current => more ? [...current, ...page.items] : page.items);
      setCursor(page.next_cursor);
      if (!more) setSelected(current => current ?? page.items[0]?.id ?? null);
    } catch (e) { if (!(e instanceof ServiceError && e.status === 503)) setError(message(e)); }
  }, [stateFilter, severityFilter]);

  const loadDetail = useCallback(async (id: string) => {
    try { setDetail(await audits<RunDetail>(`runs/${encodeURIComponent(id)}`)); }
    catch (e) { setError(message(e)); }
  }, []);

  useEffect(() => { void refreshHealth(); }, [refreshHealth]);
  useEffect(() => { if (!offline) void loadRuns(); }, [loadRuns, offline]);
  useEffect(() => { if (selected) void loadDetail(selected); else setDetail(null); }, [selected, loadDetail]);
  // O formulário só acompanha o runner quando a revisão salva muda, e nunca por cima de edição em curso.
  const loadedRevision = useRef<number | null>(null);
  const runnerSettings = health?.settings ?? null;
  useEffect(() => {
    if (!runnerSettings || dirty || loadedRevision.current === runnerSettings.revision) return;
    loadedRevision.current = runnerSettings.revision;
    setForm(editable(runnerSettings));
  }, [runnerSettings, dirty]);

  // Ativo: acompanha de perto. Parado: confere de vez em quando (o CMD pode iniciar um run).
  useEffect(() => {
    const timer = setInterval(() => { void refreshHealth(); }, activeCount ? 2000 : 15000);
    return () => clearInterval(timer);
  }, [activeCount, refreshHealth]);
  useEffect(() => {
    if (wasActive.current !== activeCount) { void loadRuns(); if (selected) void loadDetail(selected); }
    wasActive.current = activeCount;
  }, [activeCount, loadRuns, loadDetail, selected]);
  useEffect(() => {
    if (!activeCount || !selected || !health?.active.some(a => a.id === selected)) return;
    void loadDetail(selected);
  }, [health, activeCount, selected, loadDetail]);
  // Investigação em andamento: o detalhe acompanha sozinho.
  const investigationState = detail?.investigation?.state;
  useEffect(() => {
    if (!selected || !investigationState || !INVESTIGATING.has(investigationState)) return;
    const timer = setInterval(() => { void loadDetail(selected); }, 5000);
    return () => clearInterval(timer);
  }, [selected, investigationState, loadDetail]);

  async function generate(profile: Profile | null = null) {
    // Repetir o mesmo pedido após falha reaproveita a chave; outro perfil é outro pedido.
    const key = pending && pending.profile === profile ? pending.key : crypto.randomUUID();
    setPending({ key, profile }); setSubmitting(true); setError(''); setFeedback('');
    try {
      const body = { trigger: 'manual', auto_fix: false, ...(profile ? { profile } : {}) };
      const result = await audits<SubmitResult>('runs', { method: 'POST', body, key });
      setPending(null);
      setFeedback(result.coalesced ? 'Já havia uma coleta em andamento; o pedido foi agregado a ela.' : profile === 'full-audit' ? 'Auditoria completa iniciada: cópia isolada e Unity em lote, com prioridade baixa. Pode levar dezenas de minutos.' : 'Coleta iniciada. O relatório aparece aqui quando terminar.');
      if (result.run_id) setSelected(result.run_id);
      await refreshHealth(); await loadRuns();
    } catch (e) { setError(`Não foi possível pedir o relatório: ${message(e)} Tentar de novo reaproveita o mesmo pedido.`); }
    finally { setSubmitting(false); }
  }

  async function investigateNow() {
    if (!detail) return;
    setRequesting(true); setError('');
    try {
      await audits(`runs/${encodeURIComponent(detail.id)}/investigation`, { method: 'POST', body: {} });
      setFeedback('Investigação pedida. Ela roda numa fila própria e não atrasa os relatórios.');
      await loadDetail(detail.id);
    } catch (e) { setError(`Não foi possível pedir a investigação: ${message(e)}`); }
    finally { setRequesting(false); }
  }

  async function cancel() {
    if (!detail) return;
    setCancelling(true);
    try { await audits(`runs/${encodeURIComponent(detail.id)}/cancel`, { method: 'POST', body: {} }); await loadDetail(detail.id); await refreshHealth(); }
    catch (e) { setError(message(e)); }
    finally { setCancelling(false); }
  }

  function update(patch: Partial<EditableSettings>) { setForm(current => current ? { ...current, ...patch } : current); setDirty(true); setFeedback(''); }

  async function save() {
    if (!form || !health?.settings) return;
    setSaving(true); setError(''); setFeedback('');
    try {
      const saved = await audits<AuditSettings>('settings', { method: 'PUT', body: { settings: { ...form, workflow_url: safeWorkflowUrl(form.workflow_url) ?? '' }, expected_revision: health.settings.revision } });
      loadedRevision.current = saved.revision; setDirty(false); setForm(editable(saved));
      setFeedback(`Preferências salvas no runner (revisão ${saved.revision}). ${saved.on_startup ? 'A próxima abertura do iniciar-tudo.cmd gera um relatório.' : 'A rotina na abertura está desativada.'}`);
      await refreshHealth();
    } catch (e) {
      if (e instanceof ServiceError && e.code === 'revision_conflict') {
        loadedRevision.current = null; setDirty(false); setForm(null);
        setError('As preferências mudaram em outra janela. A versão atual foi recarregada; revise e salve de novo.');
        await refreshHealth();
      } else setError(`Não foi possível salvar: ${message(e)}`);
    } finally { setSaving(false); }
  }

  function importDraft(raw: string | null) {
    try {
      if (!raw) throw new Error('vazio');
      setForm(parseImportedSettings(raw)); setDirty(true); setError('');
      setFeedback('Rascunho importado para o formulário. Nada foi ativado: revise e salve para aplicar.');
    } catch { setError('Arquivo de preferências inválido. Use a exportação desta tela ou o rascunho antigo.'); }
  }

  let legacyDraft: string | null = null;
  try { legacyDraft = localStorage.getItem(LEGACY_DRAFT_KEY); } catch { /* armazenamento indisponível */ }
  const workflowUrl = safeWorkflowUrl(form?.workflow_url ?? '');
  const invalidUrl = Boolean(form?.workflow_url.trim() && !workflowUrl);
  const lastRun = health?.last_run ?? null;
  const settings = health?.settings ?? null;
  const tabs: { id: ReportView; label: string; icon: typeof FileText }[] = [
    { id: 'overview', label: 'Relatórios', icon: FileText },
    { id: 'routine', label: 'Rotina de abertura', icon: Settings2 },
    { id: 'flow', label: 'Fluxo e conexões', icon: Workflow },
  ];
  const saveButton = <button className="button primary" disabled={invalidUrl || !dirty || saving || !form || Boolean(offline)} onClick={save}><Save size={15}/>{saving ? 'Salvando…' : 'Salvar preferências'}</button>;

  return <div className="audit-page">
    <div className="page-heading audit-heading"><div><span className="eyebrow">DICEVTT · DIAGNÓSTICO CONTÍNUO</span><h1>Relatórios automáticos<span className="mint-text">.</span></h1><p>Abra seu ambiente. Saiba o que merece atenção no projeto.</p></div>
      <div className="audit-actions"><button className="button" onClick={() => { void refreshHealth(); void loadRuns(); }}><RefreshCw size={14}/>Atualizar</button>{health?.capabilities.full_audit && <button className="button" disabled={Boolean(offline) || submitting || activeCount > 0} onClick={() => generate('full-audit')}><Boxes size={14}/>Auditoria completa</button>}<button className="button primary" disabled={Boolean(offline) || submitting || activeCount > 0} onClick={() => generate()}>{submitting ? <LoaderCircle size={15} className="spin"/> : <Play size={14}/>}{activeCount ? 'Coleta em andamento' : 'Gerar agora'}</button></div>
    </div>

    {offline ? <div className="audit-notice audit-error" role="alert"><CircleAlert size={17}/><p><strong>Runner de relatórios indisponível.</strong> {offline}{lastKnown && <> Último relatório conhecido por este navegador: <code>{lastKnown.id}</code> · {runStateLabel[lastKnown.state]} · {formatLocal(lastKnown.finished_at)}{lastKnown.findings !== null ? ` · ${lastKnown.findings} ocorrência(s)` : ''}.</>}</p><span className="badge red">Offline</span></div>
      : <div className="audit-notice audit-ok"><ShieldCheck size={17}/><p><strong>Relatórios reais, gerados neste PC.</strong> Perfil leve a cada abertura; auditoria completa em cópia isolada e investigação por IA sob demanda. A sincronização com o n8n ainda não foi implementada.</p><span className="badge mint">{health ? `Runner v${health.version}` : 'Conectando…'}</span></div>}

    <section className="audit-hero" aria-label="Arquitetura">
      <div className="audit-hero-copy"><span className="eyebrow">DO SEU PC AO HISTÓRICO</span><h2>O diagnóstico começa aqui.</h2><p>Evidências e relatórios no PC.<br/>Orquestração e histórico no servidor.</p><button className="text-button" onClick={() => setView('flow')}>Explorar o fluxo <ArrowRight size={15}/></button></div>
      <div className="audit-topology"><div className="audit-machine"><span className="audit-machine-icon"><Laptop size={26}/></span><strong>Este computador</strong><small>Unity · VCS · logs · runner</small><span className={`badge ${offline ? 'red' : 'mint'}`}>{offline ? 'Runner offline' : 'Execução local ativa'}</span></div><div className="audit-wire"><span>sincronização</span><ArrowRight size={22}/><small>canal Jarvis</small></div><div className="audit-machine"><span className="audit-machine-icon server"><Server size={26}/></span><strong>Seu servidor</strong><small>n8n · orquestrador · histórico</small><span className="badge gray">Integração pendente</span></div></div>
    </section>

    <div className="audit-tabs" role="group" aria-label="Áreas de relatórios">{tabs.map(tab => <button key={tab.id} aria-pressed={view === tab.id} onClick={() => setView(tab.id)}><tab.icon size={16}/>{tab.label}</button>)}</div>
    {error && <p className="audit-notice audit-error" role="alert">{error}</p>}
    <p className="audit-feedback" role="status">{feedback}</p>

    {view === 'overview' && <div className="audit-columns"><div className="audit-main">
      <div className="audit-metrics">
        <div className="audit-metric"><span><FileCheck2 size={16}/>Último relatório</span><strong>{lastRun ? runStateLabel[lastRun.state] : '—'}</strong><small>{lastRun ? formatLocal(lastRun.finished_at) : offline ? 'Runner indisponível' : 'Nenhuma auditoria registrada'}</small></div>
        <div className="audit-metric"><span><CircleAlert size={16}/>Ocorrências atuais</span><strong>{lastRun?.summary ? lastRun.summary.findings : '—'}</strong><small>{lastRun?.summary ? `alta ${lastRun.summary.by_severity.high} · média ${lastRun.summary.by_severity.medium} · baixa ${lastRun.summary.by_severity.low}` : 'Sem auditoria concluída'}</small></div>
        <div className="audit-metric"><span><Clock3 size={16}/>Rotina na abertura</span><strong>{settings ? (settings.on_startup ? 'Ativa' : 'Desativada') : '—'}</strong><small>{health?.last_startup ? `Última abertura ${formatLocal(health.last_startup.created_at)}: ${startupOutcomeLabel[health.last_startup.outcome] ?? health.last_startup.outcome}` : 'Nenhuma abertura registrada'}</small></div>
      </div>
      <section className="panel"><div className="panel-heading"><h2><ClipboardList size={17}/> Histórico de auditorias</h2><div className="audit-filters">
        <select aria-label="Filtrar estado" value={stateFilter} onChange={e => { setStateFilter(e.target.value); setSelected(null); }}><option value="">Todos os estados</option>{Object.entries(runStateLabel).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <select aria-label="Filtrar por gravidade" value={severityFilter} onChange={e => { setSeverityFilter(e.target.value); setSelected(null); }}><option value="">Qualquer gravidade</option>{Object.entries(severityLabel).map(([k, v]) => <option key={k} value={k}>Com ocorrência {v.toLowerCase()}</option>)}</select>
      </div></div>
        {runs.length ? <div className="audit-run-list">{runs.map(run => <button key={run.id} aria-pressed={selected === run.id} onClick={() => setSelected(run.id)}>
          <span><strong>{formatLocal(run.created_at)}</strong><small>{triggerLabel[run.trigger] ?? run.trigger} · {run.profile === 'startup-light' ? 'perfil leve' : 'perfil completo'} · {run.id}</small></span>
          {ACTIVE.has(run.state) ? <small>{run.checks_done}/{run.checks_total} checks</small> : run.summary ? <small>{run.summary.findings} ocorrência(s)</small> : null}
          <span className={`badge ${runStateBadge[run.state]}`}>{runStateLabel[run.state]}</span><ChevronRight size={15}/></button>)}
          {cursor && <button className="text-button audit-more" onClick={() => loadRuns(true, cursor)}>Carregar mais</button>}</div>
        : <div className="audit-empty"><span className="audit-empty-icon"><FileText size={30}/></span><h3>{offline ? 'Sem conexão com o runner.' : stateFilter || severityFilter ? 'Nenhuma auditoria neste filtro.' : 'Nenhuma auditoria executada ainda.'}</h3><p>{offline ? 'Ligue com iniciar-tudo.cmd; o runner sobe junto com o helper e o RAG.' : <>Cada abertura de <code>iniciar-tudo.cmd</code> pede uma coleta. Você também pode gerar agora.</>}</p></div>}
        <div className="audit-history-footer"><button className="button" aria-expanded={preview} aria-controls="audit-example" onClick={() => setPreview(!preview)}><Play size={14}/>{preview ? 'Ocultar exemplo' : 'Ver relatório de exemplo'}</button><small>O exemplo é fictício e nunca entra no histórico.</small></div>
      </section>
      {preview && <section className="panel audit-example" id="audit-example" aria-label="Relatório ilustrativo"><div className="panel-heading"><h2>Prévia de relatório</h2><span className="badge yellow">Exemplo fictício · não executado</span></div><div className="audit-example-body"><p>Os dados abaixo demonstram o formato. Não representam problemas encontrados no DiceVTT.</p>
        <div className="audit-checks">{exampleReport.checks.map(check => <div key={check.name}><CheckIcon status={check.status}/><span><strong>{check.name}</strong><small>{check.note}</small></span><span className="badge gray">{{ passed: 'Coletado', partial: 'Parcial', skipped: 'Não executado' }[check.status]}</span></div>)}</div>
        <div className="audit-example-footer"><span>Testes não executados não contam como aprovação.</span><button className="text-button" onClick={() => download('exemplo-relatorio-nao-executado.json', JSON.stringify(exampleReport, null, 2), 'application/json')}><ArrowDownToLine size={14}/>Exportar exemplo JSON</button></div>
      </div></section>}
      {detail && <RunDetailPanel key={detail.id} detail={detail} onCancel={cancel} cancelling={cancelling} onInvestigate={investigateNow} requesting={requesting}/>}
    </div><aside className="audit-rail">
      <section className="panel audit-side-card"><span className="eyebrow">A CADA ABERTURA</span><h2><Clock3 size={18}/> Uma rotina, sem interromper</h2><ol className="audit-timeline"><li><strong>Iniciar o ambiente</strong><small>Helper, RAG, runner e site.</small></li><li><strong>Coletar em segundo plano</strong><small>VCS, Unity, logs e RAG no perfil leve, em segundos.</small></li><li><strong>Disponibilizar o relatório</strong><small>Aqui, no PC. Sincronização ainda pendente.</small></li></ol><button className="button full" onClick={() => setView('routine')}>Configurar rotina <ArrowRight size={14}/></button></section>
      <section className="panel audit-side-card"><span className="audit-side-icon"><ShieldCheck size={21}/></span><h2>Diagnóstico com evidências</h2><p>Cada resultado tem origem, data, hash e a revisão analisada. Logs mais antigos que os scripts geram ocorrências suspeitas, nunca confirmadas.</p><div className="audit-side-note"><HardDrive size={16}/><span>Servidor indisponível?<br/><strong>O relatório permanece no PC.</strong></span></div></section>
    </aside></div>}

    {view === 'routine' && <div className="audit-columns"><section className="panel audit-settings"><div className="panel-heading"><h2><Settings2 size={17}/> Rotina de abertura</h2><span className={`badge ${dirty ? 'yellow' : 'mint'}`}>{dirty ? 'Alterações não salvas' : settings ? `Salvo no runner · revisão ${settings.revision}` : 'Sem conexão'}</span></div><div className="audit-settings-body">
      {!form ? <p className="audit-no-findings">{offline ? 'As preferências ficam no runner; ligue-o para editar.' : health?.settings_error ?? 'Carregando preferências…'}</p> : <>
      <label className="audit-switch-row"><span><strong>Gerar ao abrir iniciar-tudo.cmd</strong><small>Lido pelo runner a cada abertura. Desativado, a abertura é registrada sem gerar relatório.</small></span><input type="checkbox" role="switch" checked={form.on_startup} onChange={e => update({ on_startup: e.target.checked })}/></label>
      <fieldset className="audit-profiles"><legend>Perfil da coleta</legend><label className={form.profile === 'startup-light' ? 'selected' : ''}><input type="radio" name="audit-profile" value="startup-light" checked={form.profile === 'startup-light'} onChange={() => update({ profile: 'startup-light' })}/><span><strong>Leve <span className="badge mint">Recomendado na abertura</span></strong><small>Controle de versão, Unity, pacotes, scripts, logs, RAG e MCP. Sem abrir a Unity nem iniciar builds.</small></span></label><label className={form.profile === 'full-audit' ? 'selected' : ''}><input type="radio" name="audit-profile" value="full-audit" checked={form.profile === 'full-audit'} onChange={() => update({ profile: 'full-audit' })}/><span><strong>Completo</strong><small>Cópia isolada, importação e compilação, referências de assets, testes EditMode e validadores do projeto na Unity em lote, com prioridade baixa. Leva de minutos a mais de uma hora na primeira vez.</small></span></label></fieldset>
      {form.profile === 'full-audit' && form.on_startup && <p className="audit-inline-warning"><CircleAlert size={16}/>Com o perfil completo na abertura, cada iniciar-tudo.cmd ocupa a CPU por muitos minutos. O recomendado é o leve na abertura e o botão Auditoria completa quando quiser.</p>}
      <label className="audit-switch-row"><span><strong>Sincronizar com o servidor e o n8n</strong><small>Preferência guardada para a entrega 3. Hoje todo relatório fica só neste PC.</small></span><input type="checkbox" role="switch" checked={form.sync_to_server} onChange={e => update({ sync_to_server: e.target.checked })}/></label>
      <label className="audit-switch-row"><span><strong>Investigar com IA ao fim de cada relatório</strong><small>As ocorrências mais graves recebem hipóteses numa fila própria. Também dá para pedir em cada relatório.</small></span><input type="checkbox" role="switch" checked={form.investigate_with_ai} onChange={e => update({ investigate_with_ai: e.target.checked })}/></label>
      <fieldset className="audit-profiles"><legend>Modelo da investigação</legend>
        <label className={form.ai_provider === 'local-rag' ? 'selected' : ''}><input type="radio" name="audit-ai" value="local-rag" checked={form.ai_provider === 'local-rag'} onChange={() => update({ ai_provider: 'local-rag', allow_code_to_provider: false })}/><span><strong>Local · AirLLM pelo RAG <span className="badge mint">Nada sai do PC</span></strong><small>Lento no CPU (minutos por ocorrência). Hipótese só conta como sustentada se citar uma fonte do RAG.</small></span></label>
        <label className={form.ai_provider === 'claude-code' ? 'selected' : ''}><input type="radio" name="audit-ai" value="claude-code" checked={form.ai_provider === 'claude-code'} onChange={() => update({ ai_provider: 'claude-code' })}/><span><strong>Claude Code <span className="badge yellow">Envia código à Anthropic</span></strong><small>Em lote, só ferramentas de leitura e o RAG; nada é editado. Usa a conta do Claude Code deste PC.</small></span></label>
      </fieldset>
      {form.ai_provider === 'claude-code' && <label className="audit-consent"><input type="checkbox" checked={form.allow_code_to_provider} onChange={e => update({ allow_code_to_provider: e.target.checked })}/><span>Autorizo enviar ao Claude (Anthropic) o resumo das ocorrências e os trechos do código do DiceVTT que ele ler durante a investigação.</span></label>}
      {form.ai_provider === 'claude-code' && !form.allow_code_to_provider && <p className="audit-inline-warning"><CircleAlert size={16}/>Sem a autorização, a investigação pelo Claude Code não roda.</p>}
      <div className="audit-paths"><div><FolderOpen size={16}/><span>Projeto de origem<code>{health?.project_root ?? 'C:/ProjetoTablepRPG/DiceVTT'}</code></span></div><div><GitBranch size={16}/><span>Versionamento<code>Unity Version Control (.plastic) · Git pai sem o projeto</code></span></div><div><HardDrive size={16}/><span>Relatórios<code>.local/audits/runs/&lt;run_id&gt;/</code></span></div></div>
      <div className="audit-settings-footer"><p>Salvas no runner, a mesma fonte que o CMD lê. Importar preenche o formulário; só salvar aplica.</p><div className="audit-actions">
        <input ref={fileInput} type="file" accept="application/json,.json" hidden aria-label="Arquivo de preferências" onChange={async e => { const file = e.target.files?.[0]; if (file) importDraft(await file.text()); e.target.value = ''; }}/>
        <button className="button" onClick={() => fileInput.current?.click()}><Upload size={15}/>Importar JSON</button>
        {legacyDraft && <button className="button" onClick={() => importDraft(legacyDraft)}>Importar rascunho antigo</button>}
        <button className="button" disabled={invalidUrl} onClick={() => download('preferencias-relatorios.json', JSON.stringify(settingsExport(form, settings?.revision ?? null), null, 2), 'application/json')}><ArrowDownToLine size={15}/>Exportar</button>
        {saveButton}</div>{invalidUrl && <p role="alert">Corrija o link do workflow em Fluxo e conexões antes de salvar.</p>}</div>
      </>}
    </div></section><aside className="audit-rail"><section className="panel audit-side-card"><span className="eyebrow">COMPORTAMENTO</span><h2>Um relatório por abertura</h2><p>Cada abertura recebe um identificador. Repetir o mesmo pedido devolve o mesmo resultado; abrir de novo durante uma coleta se junta a ela. Abrir depois que ela terminou gera outro relatório, mesmo sem mudanças no projeto.</p><hr/><h2>O site abre normalmente</h2><p>Falha no runner não impede o uso do ambiente. Uma etapa sem evidência aparece como parcial, erro ou não executada.</p><hr/><span className="badge gray">Correção automática desativada</span></section><section className="panel audit-side-card"><Sparkles size={21} className="mint-text"/><h2>IA é uma etapa opcional</h2><p>A coleta e o relatório rodam localmente sem modelo.</p></section></aside></div>}

    {view === 'flow' && <div className="audit-columns"><div className="audit-main"><section className="panel"><div className="panel-heading"><h2><Workflow size={17}/> Da abertura ao relatório</h2><span className="badge gray">Etapas 1–3 ativas</span></div><div className="audit-flow-list">{workflowSteps.map((item, index) => <button key={item.title} aria-pressed={step === index} onClick={() => setStep(index)}><span className="audit-flow-number">0{index + 1}</span><span><strong>{item.title}</strong><small>{item.location}</small></span><span className={`badge ${item.state === 'Implementado' ? 'mint' : 'gray'}`}>{item.state}</span><ChevronRight size={15}/></button>)}</div><div className="audit-flow-detail" aria-live="polite"><span className="eyebrow">ETAPA 0{step + 1}</span><h3>{workflowSteps[step].title}</h3><p>{workflowSteps[step].description}</p><div><ArrowRight size={15}/><span>Saída: {workflowSteps[step].output}</span></div></div></section>
      <section className="panel audit-connections"><div className="panel-heading"><h2><Network size={17}/> Links e conexões</h2><span className="badge gray">Disponibilidade não verificada</span></div><div className="audit-settings-body"><div className="audit-n8n-link"><div><strong>Painel n8n</strong><small>Acesso existente documentado · requer túnel SSH aberto.</small></div><a className="button" href="http://localhost:5679" target="_blank" rel="noreferrer">Abrir n8n <ExternalLink size={14}/></a></div><details className="audit-tunnel"><summary>Como acessar o painel do servidor</summary><p>Execute em um terminal e mantenha-o aberto durante o acesso:</p><pre>ssh -N -L 5679:127.0.0.1:5679 user@your-server-ip</pre><p>Esse túnel serve ao painel administrativo. A sincronização automática usará o canal autenticado do Jarvis.</p></details>
        {form ? <><label className="audit-url-field">Link do workflow de relatórios<input type="url" value={form.workflow_url} placeholder="http://localhost:5679/workflow/ID" maxLength={2048} onChange={e => update({ workflow_url: e.target.value })} aria-invalid={invalidUrl} aria-describedby="audit-url-hint"/><small id="audit-url-hint">Preencher após criar o workflow. Apenas URL do editor, sem token, parâmetros ou webhook.</small></label>{invalidUrl && <p className="audit-inline-warning" role="alert">Use uma URL http(s) terminando em /workflow/ID, sem credenciais, parâmetros ou fragmentos.</p>}<div className="audit-actions">{workflowUrl && !dirty && <a className="button" href={workflowUrl} target="_blank" rel="noreferrer">Abrir workflow <ExternalLink size={14}/></a>}{saveButton}</div></> : <p className="muted">O link do workflow fica nas preferências do runner.</p>}</div></section>
    </div><aside className="audit-rail"><section className="panel audit-side-card"><span className="eyebrow">WORKFLOWS A CRIAR</span><h2>Eventos curtos, coleta local</h2><div className="audit-workflow-card"><span>A</span><div><strong>Receber auditoria</strong><small>Webhook autenticado → validar → deduplicar → persistir → recibo.</small></div></div><div className="audit-workflow-card"><span>B</span><div><strong>Consolidar investigação</strong><small>Evento de conclusão → conferir evidências → atualizar histórico.</small></div></div><p>O n8n não precisa ficar esperando a Unity terminar. O PC envia o resultado quando estiver pronto.</p></section><section className="panel audit-side-card"><span className="eyebrow">PLANO</span><h2>Etapas e critérios de aceite</h2><p>Contrato da API, eventos n8n, etapas restantes e critérios de aceite.</p><button className="button full" onClick={() => download('plano-relatorios-automaticos-claude.md', handoff)}><ArrowDownToLine size={15}/>Baixar plano</button></section></aside></div>}
  </div>;
}
