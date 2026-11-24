import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Bot, Code2, Database, FileText, LoaderCircle, Power, RefreshCw, Search, ShieldCheck, Square, Video } from 'lucide-react';
import { formatDate, kindLabel, rag, stateLabel, warningText, type AskState, type RagHealth, type RagSource, type Retrieval } from './rag';
import './rag.css';

const ASK_KEY = 'orq.rag.lastAsk.v1';
const label = (state?: string) => (state && stateLabel[state]) || state || '—';

function Sources({sources}:{sources:RagSource[]}) {
  if (!sources.length) return <p className="muted">Nenhuma fonte retornada.</p>;
  return <div className="rag-sources">{sources.map(source => {
    const origin = source.provenance.source_url ? String(source.provenance.source_url) : '';
    return <details key={source.id} className={`rag-source ${source.included === false ? 'omitted' : ''}`}>
      <summary>
        <span className={`rag-kind ${source.kind}`}>{source.kind === 'code_pointer' ? <Code2 size={14}/> : source.provenance.source_type === 'video' ? <Video size={14}/> : <FileText size={14}/>}</span>
        <span className="rag-source-title"><strong>[{source.id}] {source.relpath}</strong>
          <small>{kindLabel(source)}{source.section ? ` › ${source.section}` : ''}{source.lines ? ` · linhas ${source.lines[0]}-${source.lines[1]}` : ''} · dist. {source.distance.toFixed(3)}{source.scope ? ` · ${source.scope === 'omitted' ? 'fora do prompt' : source.scope === 'full' ? 'arquivo completo no prompt' : source.scope === 'chunk' ? 'no prompt' : `prompt: ${source.scope}`}` : ''}</small></span>
        <span className={`badge ${source.state === 'stale_summary' ? 'yellow' : source.kind === 'code_pointer' ? 'mint' : 'gray'}`}>{source.state === 'current' ? 'lido agora' : source.state === 'stale_summary' ? 'resumo desatualizado' : 'snapshot'}</span>
      </summary>
      <div className="rag-source-meta">
        <code title={source.hash}>sha256 {source.hash.slice(0, 12)}</code>
        {source.read_at && <span>Lido em {formatDate(source.read_at)}</span>}
        {origin && <span>Fonte: <code>{origin}</code></span>}
        {source.provenance.extracted_at && <span>Extraído em {formatDate(String(source.provenance.extracted_at))}</span>}
        {source.provenance.main_class && <span>Classe: {String(source.provenance.main_class)}</span>}
      </div>
      <pre>{source.text}{source.text_truncated ? '\n… (texto limitado na resposta)' : ''}</pre>
    </details>;
  })}</div>;
}

function Warnings({items}:{items:string[]}) {
  if (!items.length) return null;
  return <ul className="rag-warnings">{items.map((w, i) => <li key={i}><AlertCircle size={13}/>{warningText(w)}</li>)}</ul>;
}

export default function RagPanel({embedded = false}:{embedded?: boolean}) {
  const [health, setHealth] = useState<RagHealth | null>(null);
  const [offline, setOffline] = useState('');
  const [query, setQuery] = useState('');
  const [retrieval, setRetrieval] = useState<Retrieval | null>(null);
  const [ask, setAsk] = useState<AskState | null>(null);
  const [askId, setAskId] = useState<string>(() => { try { return localStorage.getItem(ASK_KEY) || ''; } catch { return ''; } });
  const [busy, setBusy] = useState(''), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const pendingAsk = useRef<{query: string; request_id: string} | null>(null);
  const [folder, setFolder] = useState<{path: string; formats: string[]} | null>(null);
  useEffect(() => { if (health?.online) void rag<{path: string; formats: string[]}>('document-folder').then(setFolder).catch(() => setFolder(null)); }, [health?.online]);

  const refresh = useCallback(async () => {
    try { setHealth(await rag<RagHealth>('health')); setOffline(''); }
    catch (e) { setHealth(null); setOffline(e instanceof Error ? e.message : 'RAG indisponível.'); }
  }, []);
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 5000); return () => clearInterval(timer); }, [refresh]);

  useEffect(() => {
    if (!askId) return;
    let stop = false;
    const poll = async () => {
      try {
        const state = await rag<AskState>(`asks/${askId}`);
        if (stop) return;
        setAsk(state);
        if (!['queued', 'running'].includes(state.state)) return;
      } catch (e) { if (stop) return; setError(e instanceof Error ? e.message : String(e)); }
      if (!stop) setTimeout(() => void poll(), 2500);
    };
    void poll();
    return () => { stop = true; };
  }, [askId]);

  async function search() {
    if (!query.trim() || busy) return;
    setBusy('search'); setError('');
    try { setRetrieval(await rag<Retrieval>('retrieve', { project_id: 'dicevtt', query: query.trim(), text_limit: 40000 })); }
    catch (e) { setError((e as Error).message); } finally { setBusy(''); }
  }
  async function startAsk() {
    if (!query.trim() || busy) return;
    setBusy('ask'); setError('');
    if (pendingAsk.current?.query !== query.trim()) pendingAsk.current = { query: query.trim(), request_id: crypto.randomUUID() };
    try {
      const created = await rag<{ask_id: string}>('asks', { project_id: 'dicevtt', ...pendingAsk.current });
      pendingAsk.current = null;
      setAsk(null); setAskId(created.ask_id);
      try { localStorage.setItem(ASK_KEY, created.ask_id); } catch { /* conveniência opcional */ }
    } catch (e) { setError((e as Error).message); } finally { setBusy(''); }
  }
  async function cancelAsk() {
    if (!askId) return;
    try { await rag(`asks/${askId}/cancel`, {}); setNotice('Cancelamento pedido: o modelo para no próximo token.'); } catch (e) { setError((e as Error).message); }
  }
  async function reindex(scope: 'code' | 'documents' | 'all') {
    setBusy(`index-${scope}`); setError('');
    try {
      const job = await rag<{job_id: string}>('index-jobs', { project_id: 'dicevtt', scope });
      setNotice('Indexação iniciada.');
      for (let i = 0; i < 240; i++) {
        await new Promise(r => setTimeout(r, 1500));
        const state = await rag<{state: string; report?: Record<string, {added: number; updated: number; removed: number; errors: string[]}>; error?: string}>(`index-jobs/${job.job_id}`);
        if (state.state !== 'running' && state.state !== 'queued') {
          if (state.error) throw new Error(state.error);
          setNotice(Object.entries(state.report || {}).map(([k, r]) => `${k === 'code' ? 'Código' : 'Documentos'}: ${r.added} novos · ${r.updated} atualizados · ${r.removed} removidos${r.errors.length ? ` · ${r.errors.length} erro(s): ${r.errors.join('; ')}` : ''}`).join(' · ') || 'Indexação concluída.');
          break;
        }
        if (i === 239) setNotice(`A indexação continua em segundo plano (pedido ${job.job_id}). Consulte a última indexação nesta seção antes de iniciar outra.`);
      }
      await refresh();
    } catch (e) { setError((e as Error).message); } finally { setBusy(''); }
  }
  async function power(on: boolean) {
    setError('');
    if (!on && !confirm('Desligar o RAG também desliga o helper Jarvis Desktop. Projects e o RAG nos celulares ficarão offline até religar. Continuar?')) return;
    setBusy('power');
    try {
      if (on) { const r = await fetch('/api/rag-control/start', { method: 'POST', headers: { 'X-Orchestrator-Request': '1' } }); if (!r.ok) throw new Error((await r.json()).message); setNotice('Helper iniciando; o RAG sobe junto em alguns segundos.'); }
      else { await rag('shutdown', {}); setNotice('RAG desligando; o helper encerra junto.'); }
      setTimeout(() => void refresh(), 4000);
    } catch (e) { setError((e as Error).message); } finally { setBusy(''); }
  }

  const online = !!health?.online;
  const index = health?.index;
  const model = health?.model;
  const running = ask && ['queued', 'running'].includes(ask.state);
  return <section className={`rag-panel ${embedded ? 'embedded' : ''}`} aria-label="RAG local do DiceVTT">
    {!embedded && <div className="page-heading"><div><span className="eyebrow">RAG LOCAL · CHROMA + AIRLLM</span><h1>Conhecimento do DiceVTT</h1><p>Scripts C# lidos do disco agora e documentação coletada, com a origem de cada trecho.</p></div><button className="button" onClick={() => void refresh()}><RefreshCw size={16}/>Atualizar</button></div>}
    {embedded && <div className="panel-heading"><h2><Database size={17}/> RAG local · scripts e documentação</h2><button className="button small" onClick={() => void refresh()}><RefreshCw size={14}/>Atualizar</button></div>}
    <div className={`rag-status ${online ? 'online' : 'offline'}`}>
      <span className="rag-status-icon">{online ? <ShieldCheck size={22}/> : <Power size={22}/>}</span>
      <div>
        <strong>{online ? (health?.starting ? 'RAG iniciando…' : 'Helper + RAG ligados neste PC') : 'Helper + RAG desligados'}</strong>
        <p>{online
          ? `${index?.code_pointers ?? 0} scripts · ${index?.document_chunks ?? 0} trechos de ${index?.documents ?? 0} documentos · watcher ${label(health?.watcher?.state).toLowerCase()} · embeddings ${label(health?.embeddings?.state).toLowerCase()} · modelo ${label(model?.state).toLowerCase()}${model?.name ? ` (${model.name}, ${model.device})` : ''}`
          : offline || 'Verificando…'}</p>
        {health?.startup_error && <p className="warning-text">{health.startup_error}</p>}
        {model?.state === 'error' && model.reason && <p className="warning-text">Geração indisponível: {model.reason}</p>}
      </div>
      <div className="rag-status-actions">
        {online ? <>
          <button className="button small" disabled={!!busy} onClick={() => void reindex('code')}>{busy === 'index-code' ? <LoaderCircle size={14} className="spin"/> : <Code2 size={14}/>}Reindexar scripts</button>
          <button className="button small" disabled={!!busy} onClick={() => void reindex('documents')}>{busy === 'index-documents' ? <LoaderCircle size={14} className="spin"/> : <FileText size={14}/>}Reindexar documentos</button>
          <button className="button small danger" disabled={!!busy} onClick={() => void power(false)}><Power size={14}/>Desligar</button>
        </> : <button className="button small primary" disabled={!!busy} onClick={() => void power(true)}><Power size={14}/>Ligar helper + RAG</button>}
      </div>
    </div>
    {error && <div className="notice error" role="alert"><AlertCircle size={16}/>{error}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
    <section className="panel rag-document-folder" aria-label="Pasta de documentos">
      <div className="panel-heading"><h2><FileText size={19}/> Indexar uma pasta de PDFs e documentos</h2><span className="badge gray">Neste PC</span></div>
      <p>1. Abra a pasta abaixo. 2. Copie seus arquivos para ela (subpastas também são lidas). 3. Clique em <strong>Indexar pasta agora</strong>.</p>
      <label className="field">Pasta usada pelo RAG<input readOnly aria-label="Caminho da pasta de documentos" value={folder?.path || health?.roots?.docs || 'Ligue o RAG para consultar o caminho configurado'}/></label>
      <div className="rag-query-actions">
        <button className="button" disabled={!online || !folder} onClick={() => { void rag('document-folder/open', {}).catch(e => setError(e.message)); }}>Abrir pasta no Windows</button>
        <button className="button" disabled={!folder} onClick={() => { if (folder) void navigator.clipboard.writeText(folder.path).then(() => setNotice('Caminho copiado.')).catch(() => setError('Não foi possível copiar. Selecione o caminho acima.')); }}>Copiar caminho</button>
        <button className="button primary" disabled={!online || !!busy || !folder} onClick={() => void reindex('documents')}>{busy === 'index-documents' ? <LoaderCircle size={15} className="spin"/> : <Database size={15}/>}Indexar pasta agora</button>
      </div>
      <p className="muted">Formatos: {folder?.formats.join(', ') || 'PDF, Markdown, TXT, CSV, TSV, JSON, YAML, XML e LOG'}. Até 32 MB por arquivo. Exporte planilhas Excel como CSV. PDFs precisam de texto selecionável; documentos digitalizados precisam de OCR antes da cópia.</p>
      <p className="muted">A indexação é manual: clique novamente após adicionar, alterar ou excluir arquivos. Arquivos sem alterações são reaproveitados. Outros formatos são ignorados. Depois, use “Buscar fontes” abaixo para consultar o conteúdo.</p>
      {health?.index?.last_reports?.documents && <p role="status">Última indexação: {formatDate(health.index.last_reports.documents.finished_at)} · {health.index.last_reports.documents.added} novos · {health.index.last_reports.documents.updated} atualizados · {health.index.last_reports.documents.skipped} sem alterações · {health.index.last_reports.documents.errors.length} erros</p>}
    </section>
    <form className="panel rag-query" onSubmit={e => { e.preventDefault(); void search(); }}>
      <label className="field" htmlFor="rag-query">Pergunta sobre o projeto
        <textarea id="rag-query" rows={3} maxLength={2000} value={query} onChange={e => setQuery(e.target.value)} placeholder="Ex.: Como o SteamLobbyManager.cs cria o lobby e como os jogadores entram?"/></label>
      <div className="rag-query-actions">
        <button className="button" type="submit" disabled={!online || !query.trim() || !!busy}>{busy === 'search' ? <LoaderCircle size={15} className="spin"/> : <Search size={15}/>}Buscar fontes</button>
        <button className="button primary" type="button" disabled={!online || !query.trim() || !!busy || !!running || model?.state === 'not_configured'} onClick={() => void startAsk()}><Bot size={15}/>Perguntar ao modelo local</button>
        <span className="muted">Buscar é imediato. A resposta do AirLLM roda no CPU deste PC e leva alguns minutos.</span>
      </div>
    </form>
    {ask && <section className="panel rag-answer">
      <div className="panel-heading"><h2><Bot size={17}/> Resposta do modelo local</h2><span className={`badge ${ask.state === 'completed' ? 'mint' : ask.state === 'failed' ? 'red' : 'yellow'}`}>{label(ask.state)}</span></div>
      <p className="muted">“{ask.query}”</p>
      {running && <div className="rag-progress"><LoaderCircle size={16} className="spin"/>{ask.progress?.message || 'Na fila de geração…'}<span>{ask.progress ? `${Math.round(ask.progress.elapsed_ms / 1000)} s` : ''}</span><button className="button small" onClick={() => void cancelAsk()}><Square size={12}/>Cancelar</button></div>}
      {ask.error && <p className="warning-text">{ask.error}</p>}
      {ask.result && <>
        <div className="rag-answer-text">{ask.result.answer}</div>
        <p className="muted">{ask.result.model} · prompt {ask.result.prompt_tokens} tokens · {ask.result.generated_tokens} gerados · {Math.round((ask.result.timings_ms.total || 0) / 1000)} s</p>
        <Warnings items={ask.result.warnings}/>
        <h3>Fontes da resposta</h3>
        <Sources sources={ask.result.sources}/>
      </>}
    </section>}
    {retrieval && <section className="panel rag-results">
      <div className="panel-heading"><h2><Search size={17}/> Fontes encontradas</h2><span className="count">{retrieval.sources.length}</span></div>
      <p className="muted">{retrieval.files_read.length} scripts lidos do disco ({Math.round(retrieval.bytes_read / 1024)} KB) · embedding {retrieval.timings_ms.embedding} ms · código {retrieval.timings_ms.code} ms · documentos {retrieval.timings_ms.documents} ms</p>
      <Warnings items={retrieval.warnings}/>
      <Sources sources={retrieval.sources}/>
    </section>}
  </section>;
}
