import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, BookOpen, Database, Globe, HardDrive, LoaderCircle, RefreshCw, Square } from 'lucide-react';
import { createManifest, type IngestionSource } from './ingestion';
import { formatDate, localApi, rag, stateLabel } from './rag';

type Item = { position: number; raw_url: string; catalog_id: string | null; status: string; result: { reason_code: string | null; message: string; output_path: string | null; hash: string | null; extracted_at: string | null; acquired_at: string | null; noop: boolean; warnings: string[] } | null };
type Batch = { id: string; mode: string; state: string; created_at: string; total: number; input: string | null; counts: Record<string, number>; items?: Item[] };
type Health = { online: boolean; default_mode: string; output_root: string; writable: Record<string, boolean>; catalog_available: boolean; running_batch: string | null };
const api = <T,>(path: string, body?: unknown) => localApi<T>('/api/ingestion', path, body);
const label = (s: string) => stateLabel[s] || ({ completed_with_errors: 'Concluído com falhas', fetching: 'Coletando', reading_cache: 'Lendo cache', extracting: 'Extraindo', writing: 'Gravando', validating: 'Validando', skipped: 'Ignorado', retrying: 'Nova tentativa' } as Record<string, string>)[s] || s;

export default function IngestionRunPanel({sources}:{sources: IngestionSource[]}) {
  const [health, setHealth] = useState<Health | null>(null), [offline, setOffline] = useState('');
  const [batches, setBatches] = useState<Batch[]>([]), [current, setCurrent] = useState<Batch | null>(null);
  const [busy, setBusy] = useState(''), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const selected = useRef<string | null>(null);
  const requests = useRef(new Map<string, string>());

  const refresh = useCallback(async () => {
    try {
      const [h, list] = await Promise.all([api<Health>('health'), api<{batches: Batch[]}>('batches?limit=8')]);
      setHealth(h); setBatches(list.batches); setOffline('');
      const id = selected.current || list.batches[0]?.id;
      if (id) { selected.current = id; setCurrent(await api<Batch>(`batches/${id}?limit=200`)); }
    } catch (e) { setHealth(null); setOffline(e instanceof Error ? e.message : 'Ingestão indisponível.'); }
  }, []);
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 4000); return () => clearInterval(timer); }, [refresh]);

  async function start(kind: 'manifest' | 'catalog', mode: 'online' | 'offline') {
    setBusy(`${kind}-${mode}`); setError(''); setNotice('');
    const payload = kind === 'catalog' ? { catalog: true } : { manifest: createManifest(sources) };
    const key = `${kind}-${mode}-${JSON.stringify(kind === 'catalog' ? 'catalog' : sources.map(s => s.canonicalUrl))}`;
    if (!requests.current.has(key)) requests.current.set(key, crypto.randomUUID());
    try {
      const batch = await api<Batch>('batches', { request_id: requests.current.get(key), project_id: 'dicevtt', mode, ...payload });
      requests.current.delete(key);
      selected.current = batch.id; setCurrent(batch);
      setNotice(mode === 'online' ? 'Coleta iniciada: acessa os sites e o YouTube.' : 'Reprocessando somente o cache local, sem rede.');
      await refresh();
    } catch (e) { setError((e as Error).message); } finally { setBusy(''); }
  }
  async function cancel(id: string) {
    try { await api(`batches/${id}/cancel`, {}); setNotice('Cancelamento pedido; documentos já salvos são mantidos.'); } catch (e) { setError((e as Error).message); }
  }
  async function indexDocuments() {
    setBusy('index'); setError('');
    try {
      const job = await rag<{job_id: string}>('index-jobs', { project_id: 'dicevtt', scope: 'documents' });
      setNotice('Indexação dos documentos no RAG iniciada.');
      for (let i = 0; i < 240; i++) {
        await new Promise(r => setTimeout(r, 1500));
        const state = await rag<{state: string; error?: string; report?: {documents?: {added: number; updated: number; removed: number; skipped: number; errors: string[]}}}>(`index-jobs/${job.job_id}`);
        if (!['queued', 'running'].includes(state.state)) {
          if (state.error) throw new Error(state.error);
          const r = state.report?.documents;
          setNotice(r ? `Índice atualizado: ${r.added} novos, ${r.updated} atualizados, ${r.removed} removidos, ${r.skipped} sem mudança${r.errors.length ? `, ${r.errors.length} erro(s)` : ''}.` : 'Indexação concluída.');
          break;
        }
      }
    } catch (e) { setError(`Indexação: ${(e as Error).message}`); } finally { setBusy(''); }
  }

  const online = !!health?.online;
  const running = current && ['queued', 'running'].includes(current.state);
  return <section className="panel ingestion-run" aria-label="Coleta e indexação">
    <div className="panel-heading"><h2><Database size={17}/> Coletar e indexar</h2><span className={`badge ${online ? 'mint' : 'yellow'}`}>{online ? 'Serviço local ativo' : 'Serviço desligado'}</span></div>
    {!online && <p className="warning-text">{offline || 'Verificando…'} </p>}
    {online && health && <p className="muted">Destino: <code>{health.output_root}</code>{!health.writable.output && ' · sem permissão de escrita'}</p>}
    <div className="ingestion-run-actions">
      <button className="button primary" disabled={!online || !sources.length || !!busy} onClick={() => void start('manifest', 'online')}>{busy === 'manifest-online' ? <LoaderCircle size={15} className="spin"/> : <Globe size={15}/>}Coletar online ({sources.length})</button>
      <button className="button" disabled={!online || !health?.catalog_available || !!busy} onClick={() => void start('catalog', 'online')}><BookOpen size={15}/>Coletar catálogo (online)</button>
      <button className="button" disabled={!online || !!busy} onClick={() => void start(sources.length ? 'manifest' : 'catalog', 'offline')}><HardDrive size={15}/>Reprocessar cache offline</button>
      <button className="button" disabled={!!busy} onClick={() => void indexDocuments()}>{busy === 'index' ? <LoaderCircle size={15} className="spin"/> : <Database size={15}/>}Indexar documentos no RAG</button>
      <button className="button subtle" onClick={() => void refresh()}><RefreshCw size={14}/>Atualizar</button>
    </div>
    <p className="ingestion-hint">Coleta salva os .md em documentacao_rag/. Salvo não é indexado: use “Indexar documentos no RAG” depois.</p>
    {error && <div className="notice error" role="alert"><AlertCircle size={16}/>{error}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
    {!!batches.length && <div className="ingestion-batches">{batches.map(batch => <button key={batch.id} className={`report-item ${current?.id === batch.id ? 'selected' : ''}`} onClick={() => { selected.current = batch.id; void refresh(); }}>
      <span><strong>{batch.input || 'Lote'} · {batch.mode}</strong><small>{label(batch.state)} · {formatDate(batch.created_at)} · ✓{batch.counts.completed ?? 0} ↷{batch.counts.skipped ?? 0} ✕{batch.counts.failed ?? 0}</small></span></button>)}</div>}
    {current?.items && <div className="ingestion-items">
      <div className="panel-heading"><h3>{label(current.state)} · {current.total} fontes</h3>{running && <button className="button small" onClick={() => void cancel(current.id)}><Square size={12}/>Cancelar</button>}</div>
      {current.items.map(item => <div key={item.position} className={`ingestion-item ${item.status}`}>
        <span className="badge gray">{item.catalog_id || `#${item.position + 1}`}</span>
        <span className="ingestion-item-body"><strong>{item.raw_url}</strong>
          <small>{label(item.status)}{item.result?.reason_code ? ` · ${item.result.reason_code}` : ''}{item.result?.message ? ` — ${item.result.message}` : ''}</small>
          {item.result?.extracted_at && <small>Extraído {formatDate(item.result.extracted_at)}{item.result.acquired_at ? ` · aquisição ${formatDate(item.result.acquired_at)}` : ''}{item.result.hash ? ` · sha256 ${item.result.hash.slice(0, 10)}` : ''}</small>}
          {!!item.result?.warnings?.length && <small className="warning-text">{item.result.warnings.join(' · ')}</small>}
        </span>
      </div>)}
    </div>}
  </section>;
}
