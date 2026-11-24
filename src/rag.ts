export type RagSource = {
  id: string; record_id: string; kind: 'code_pointer' | 'documentation'; filepath: string; relpath: string; text: string;
  text_truncated?: boolean; distance: number; hash: string; read_at: string; lines: [number, number] | null;
  chunk_index: number | null; state: string; section: string | null; full_file: boolean;
  provenance: Record<string, string | number | boolean | null>; included?: boolean; scope?: string;
};
export type Retrieval = { query: string; sources: RagSource[]; warnings: string[]; bytes_read: number; files_read: string[]; timings_ms: Record<string, number> };
export type AskState = {
  id: string; ask_id?: string; query: string; state: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted';
  progress?: { stage: string; message: string; elapsed_ms: number } | null; error?: string | null;
  result?: { answer: string; sources: RagSource[]; warnings: string[]; timings_ms: Record<string, number>; model: string; prompt_tokens: number; generated_tokens: number } | null;
};
export type RagHealth = {
  service: string; online: boolean; starting: boolean; startup_error: string | null; version: string;
  embeddings?: { state: string; model: string; error: string | null };
  index?: { state: string; code_pointers?: number; document_chunks?: number; documents?: number; writer?: string | null; queued_tasks?: number; last_reports?: Record<string, { added: number; updated: number; removed: number; skipped: number; errors: string[]; finished_at: number }> };
  watcher?: { state: string; error: string | null; events_seen: number };
  model?: { state: string; reason: string | null; name: string | null; device: string; max_new_tokens: number };
  roots?: { scripts: string; docs: string; scripts_available: boolean; docs_available: boolean };
};

export class ServiceError extends Error {
  constructor(message: string, public status: number, public code?: string) { super(message); }
}

export async function localApi<T>(base: '/api/rag' | '/api/ingestion', path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${base}/${path}`, body === undefined ? { cache: 'no-store' } : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Orchestrator-Request': '1' }, body: JSON.stringify(body),
  });
  let data: Record<string, unknown> = {};
  try { data = await response.json(); } catch { /* corpo vazio */ }
  if (!response.ok) throw new ServiceError(String(data.message || `Serviço respondeu HTTP ${response.status}.`), response.status, data.error as string | undefined);
  return data as T;
}

export const rag = <T,>(path: string, body?: unknown) => localApi<T>('/api/rag', path, body);

export const stateLabel: Record<string, string> = {
  ready: 'Pronto', loading: 'Carregando', unloaded: 'Sob demanda', not_configured: 'Não configurado', error: 'Erro',
  running: 'Ativo', stopped: 'Parado', disabled: 'Desligado', documents_recovering: 'Recuperando documentos', unavailable: 'Indisponível',
  queued: 'Na fila', completed: 'Concluído', failed: 'Falhou', cancelled: 'Cancelado', interrupted: 'Interrompido',
};

export const kindLabel = (source: RagSource) => source.kind === 'code_pointer' ? 'Script C#' : source.provenance.source_type === 'video' ? 'Vídeo' : 'Documentação';

export function warningText(code: string) {
  const [key, ...rest] = code.split(': ');
  const message = rest.join(': ');
  const labels: Record<string, string> = {
    context_excerpt: 'Trecho parcial', context_omitted: 'Fonte omitida', document_needs_reindex: 'Documento mudou — reindexe',
    documents_recovering: 'Documentos em recuperação', no_context: 'Sem contexto', source_missing: 'Script sumiu',
    source_unreadable: 'Script ilegível', pointer_outside_root: 'Ponteiro fora da raiz', mention_not_indexed: 'Arquivo citado não indexado',
    source_changed_after_read: 'Script mudou após a leitura',
  };
  return labels[key] ? `${labels[key]}: ${message}` : code;
}

export const formatDate = (value?: string | number | null) => {
  if (!value) return '';
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
};
