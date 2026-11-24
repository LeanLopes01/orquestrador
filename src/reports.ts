import { ServiceError } from './rag';

// Preferências reais vivem no runner (.local/audits/config.json). O rascunho antigo deste
// navegador (versão "ui_only") só entra por importação explícita, nunca ativa nada sozinho.
export const LEGACY_DRAFT_KEY = 'orchestrator.audit-draft.v1';
export const LAST_KNOWN_KEY = 'orchestrator.audits.last-known.v1';

export type Profile = 'startup-light' | 'full-audit';
export type AiProvider = 'local-rag' | 'claude-code';
export type AuditSettings = {
  version: 1; revision: number; on_startup: boolean; profile: Profile; sync_to_server: boolean;
  investigate_with_ai: boolean; workflow_url: string; ai_provider: AiProvider; allow_code_to_provider: boolean;
  updated_at: string | null;
};
export type EditableSettings = Pick<AuditSettings, 'on_startup' | 'profile' | 'sync_to_server' | 'investigate_with_ai' | 'workflow_url' | 'ai_provider' | 'allow_code_to_provider'>;
export type RunState = 'queued' | 'collecting' | 'completed' | 'partial' | 'failed' | 'cancelled' | 'interrupted';
export type CheckStatus = 'collected' | 'partial' | 'error' | 'skipped';
export type Severity = 'high' | 'medium' | 'low' | 'info';
export type Comparison = 'new' | 'recurring' | 'resolved' | 'not_rechecked';
export type Summary = {
  findings: number; by_severity: Record<Severity, number>; new: number; recurring: number; resolved: number;
  not_rechecked: number; coverage: Record<CheckStatus, number>;
};
export type Revision = {
  vcs: string | null; source_state: string; git_root: string | null; project_relative_path: string | null;
  commit: string | null; branch: string | null; dirty: boolean | null;
  plastic: { repository: string | null; branch: string | null; changeset: number | null; pending: number | null; private: number | null } | null;
};
export type RunRow = {
  id: string; project: string; profile: Profile; trigger: 'startup' | 'manual'; state: RunState;
  created_at: string; started_at: string | null; finished_at: string | null; summary: Summary | null;
  revision: Revision | null; error: string | null; sync_state: string; checks_total: number; checks_done: number;
};
export type Evidence = { id: string; kind: string; source: string; detail: string; sha256: string | null; observed_at: string | null };
export type ValidatorOutcome = { id: string; name: string; status: 'passed' | 'failed' | 'error' | 'timeout' | 'skipped'; note?: string; exit_code?: number | null; duration_ms?: number; failures?: number; result?: string | null };
export type ReportCheck = { id: string; name: string; status: CheckStatus; note: string; problems: string[]; duration_ms: number; evidence: Evidence[]; data?: { validators?: ValidatorOutcome[] } & Record<string, unknown> };
export type ReportFinding = {
  fingerprint: string; check_id: string; rule: string; severity: Severity; state: 'suspected' | 'confirmed';
  comparison: Comparison; summary: string; file: string | null; line: number | null; evidence: string[];
  recommendation: string; occurrences: number;
};
export type Report = {
  schema_version: 1; kind: 'audit'; executed: true; run_id: string; state: RunState; profile: Profile; trigger: string;
  started_at: string | null; finished_at: string | null; duration_ms: number | null; revision: Revision;
  summary: Summary; checks: ReportCheck[]; findings: ReportFinding[]; previous_run_id: string | null;
  sync: { state: string; note: string }; startup_ids: string[];
};
export type InvestigationState = 'queued' | 'running' | 'completed' | 'partial' | 'failed' | 'skipped' | 'cancelled' | 'interrupted';
export type HypothesisItem = {
  fingerprint: string; rule: string; severity: Severity; finding_summary: string; file: string | null;
  status: 'supported' | 'unsupported' | 'failed' | 'timeout' | 'skipped' | 'cancelled'; hypothesis?: string;
  confidence?: 'low' | 'medium' | 'high' | null; error?: string | null; duration_ms?: number; cost_usd?: number | null;
  sources?: { ref: string | null; path: string | null; lines?: [number, number] | null; valid: boolean }[]; suggested_checks?: string[];
};
export type Investigation = {
  run_id: string; state: InvestigationState; trigger: string; attempt: number; provider: AiProvider | null; model: string | null;
  prompt_version: string | null; requested_at: string; started_at: string | null; finished_at: string | null; error: string | null;
  findings_total: number; findings_done: number; result_error?: string;
  result?: { state: InvestigationState; reason: string | null; provider: AiProvider; model: string | null; prompt_version: string;
    report_sha256: string; data_left_pc: boolean; note: string; items: HypothesisItem[] };
};
export type RunDetail = RunRow & {
  startup_ids: string[]; checks: { id: string; name: string; status: CheckStatus; note: string; duration_ms: number }[];
  artifacts: { kind: string; name: string; sha256: string; bytes: number }[]; report?: Report; report_error?: string;
  investigation?: Investigation;
};
export type AuditHealth = {
  service: 'dicevtt-diagnostics'; online: true; version: string; project: string; project_root: string;
  capabilities: { profiles: Profile[]; full_audit: boolean; sync: boolean; ai_investigation: boolean; auto_fix: boolean };
  settings: AuditSettings | null; settings_error: string | null; current: string | null; investigating: string | null;
  active: { id: string; state: RunState; profile: Profile; trigger: string; checks_done: number; checks_total: number }[];
  last_run: RunRow | null; last_startup: { startup_id: string; run_id: string | null; outcome: string; created_at: string } | null;
  sync: { state: string; message: string };
};
export type SubmitResult = { run_id: string | null; outcome: 'created' | 'coalesced' | 'disabled'; duplicate: boolean; coalesced: boolean };

export async function audits<T>(path: string, init?: { method: 'POST' | 'PUT'; body: unknown; key?: string }): Promise<T> {
  const response = await fetch(`/api/audits/${path}`, init ? {
    method: init.method, body: JSON.stringify(init.body),
    headers: { 'Content-Type': 'application/json', 'X-Orchestrator-Request': '1', ...(init.key ? { 'Idempotency-Key': init.key } : {}) },
  } : { cache: 'no-store' });
  let data: Record<string, unknown> = {};
  try { data = await response.json(); } catch { /* corpo vazio */ }
  if (!response.ok) throw new ServiceError(String(data.message || `Runner respondeu HTTP ${response.status}.`), response.status, data.error as string | undefined);
  return data as T;
}

export const reportUrl = (id: string, format: 'json' | 'html') => `/api/audits/runs/${encodeURIComponent(id)}/report?format=${format}`;

// Links são navegação administrativa, nunca endpoints de execução ou credenciais.
export function safeWorkflowUrl(value: string): string | null {
  if (!value.trim()) return null;
  try {
    const url = new URL(value.trim());
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) return null;
    if (!/^\/workflow\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)) return null;
    return url.href;
  } catch { return null; }
}

export const editable = (s: AuditSettings): EditableSettings => ({
  on_startup: s.on_startup, profile: s.profile, sync_to_server: s.sync_to_server,
  investigate_with_ai: s.investigate_with_ai, workflow_url: s.workflow_url,
  ai_provider: s.ai_provider ?? 'local-rag', allow_code_to_provider: s.allow_code_to_provider ?? false,
});

// Aceita o rascunho antigo da UI (camelCase, "ui_only") e a exportação atual. Só preenche o formulário.
export function parseImportedSettings(raw: string): EditableSettings {
  const data = JSON.parse(raw);
  const s = data?.settings;
  if (!data || data.version !== 1 || typeof s !== 'object' || !s) throw new Error('invalid');
  const pick = (snake: string, camel: string) => s[snake] ?? s[camel];
  const result = {
    on_startup: pick('on_startup', 'onStartup'), profile: s.profile, sync_to_server: pick('sync_to_server', 'syncToServer'),
    investigate_with_ai: pick('investigate_with_ai', 'investigateWithAI'), workflow_url: pick('workflow_url', 'workflowUrl') ?? '',
    // A autorização para enviar código nunca vem de um arquivo importado: precisa ser marcada aqui.
    ai_provider: s.ai_provider === 'claude-code' ? 'claude-code' : 'local-rag', allow_code_to_provider: false,
  };
  if (typeof result.on_startup !== 'boolean' || !['startup-light', 'full-audit'].includes(result.profile) ||
      typeof result.sync_to_server !== 'boolean' || typeof result.investigate_with_ai !== 'boolean' ||
      typeof result.workflow_url !== 'string' || (result.workflow_url && !safeWorkflowUrl(result.workflow_url))) throw new Error('invalid');
  return result as EditableSettings;
}

export function settingsExport(settings: EditableSettings, revision: number | null) {
  return {
    version: 1, kind: 'dicevtt-audit-settings', exported_at: new Date().toISOString(), runner_revision: revision,
    executed: false, delivery: 'export_only', auto_fix: false,
    settings: { ...settings, workflow_url: safeWorkflowUrl(settings.workflow_url) ?? '' },
  };
}

export const runStateLabel: Record<RunState, string> = {
  queued: 'Na fila', collecting: 'Coletando', completed: 'Concluído', partial: 'Parcial', failed: 'Falhou',
  cancelled: 'Cancelado', interrupted: 'Interrompido',
};
export const runStateBadge: Record<RunState, string> = {
  queued: 'gray', collecting: 'blue', completed: 'mint', partial: 'yellow', failed: 'red', cancelled: 'gray', interrupted: 'yellow',
};
export const checkLabel: Record<CheckStatus, string> = { collected: 'Coletado', partial: 'Parcial', error: 'Erro na coleta', skipped: 'Não executado' };
export const severityLabel: Record<Severity, string> = { high: 'Alta', medium: 'Média', low: 'Baixa', info: 'Informativa' };
export const severityBadge: Record<Severity, string> = { high: 'red', medium: 'yellow', low: 'blue', info: 'gray' };
export const comparisonLabel: Record<Comparison, string> = { new: 'Nova', recurring: 'Recorrente', resolved: 'Resolvida', not_rechecked: 'Não reverificada' };
export const triggerLabel: Record<string, string> = { startup: 'Abertura do CMD', manual: 'Manual' };
export const investigationLabel: Record<InvestigationState, string> = {
  queued: 'Na fila', running: 'Investigando', completed: 'Concluída', partial: 'Parcial', failed: 'Falhou',
  skipped: 'Não executada', cancelled: 'Cancelada', interrupted: 'Interrompida',
};
export const hypothesisLabel: Record<HypothesisItem['status'], string> = {
  supported: 'Hipótese com fonte', unsupported: 'Hipótese sem fonte', failed: 'Falhou', timeout: 'Tempo esgotado',
  skipped: 'Não investigada', cancelled: 'Cancelada',
};
export const validatorLabel: Record<ValidatorOutcome['status'], string> = {
  passed: 'Sem falhas', failed: 'Com falhas', error: 'Não rodou', timeout: 'Tempo esgotado', skipped: 'Não executado',
};
export const startupOutcomeLabel: Record<string, string> = { created: 'gerou relatório', coalesced: 'juntou-se à coleta em andamento', disabled: 'desativado nas preferências' };

export const formatLocal = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
};

export const workflowSteps = [
  { title: 'Abrir o ambiente', location: 'PC · iniciar-tudo.cmd', description: 'Depois de iniciar o helper, o CMD pede um relatório em segundo plano, antes de abrir a interface. O pedido tem um startup_id próprio e nunca bloqueia o site.', output: 'startup_id + pedido idempotente', state: 'Implementado' },
  { title: 'Coletar evidências', location: 'PC · runner 127.0.0.1:8768', description: 'Perfil leve: Unity Version Control e Git, versão da Unity, pacotes, scripts, Editor.log, Player.log, RAG e MCP. O que não pôde ser verificado fica registrado como parcial, erro ou não executado.', output: 'run_id + checks + evidências com hash', state: 'Implementado' },
  { title: 'Salvar o relatório', location: 'PC · .local/audits', description: 'SQLite com histórico e comparação entre runs, mais JSON e HTML conferidos por hash. Funciona sem internet e sem servidor.', output: 'Relatório local (JSON/HTML)', state: 'Implementado' },
  { title: 'Auditoria completa', location: 'PC · C:/DiceVTT-Audit', description: 'Sob demanda: cópia isolada do projeto, importação e compilação, referências de assets, testes EditMode e os validadores do próprio projeto na Unity em lote. A origem só é lida e seu hash é conferido no fim.', output: 'Checks completos + logs por etapa', state: 'Implementado' },
  { title: 'Receber no n8n', location: 'Servidor · gateway Jarvis → n8n', description: 'O helper enviará pelo canal autenticado existente. O gateway encaminhará o evento a um webhook dedicado, que valida a versão e ignora duplicatas.', output: 'Recibo por event_id + histórico central', state: 'A implementar' },
  { title: 'Investigar com IA', location: 'PC · fila própria do runner', description: 'Se habilitado, as ocorrências mais graves recebem hipóteses do modelo local (AirLLM pelo RAG) ou do Claude Code com autorização. Hipóteses ficam à parte do relatório e só contam como sustentadas com fonte citada.', output: 'investigation.json versionado', state: 'Implementado' },
];

// Exemplo didático: nunca misturar com runs retornados pela API.
export const exampleReport = {
  kind: 'example', executed: false, id: 'EXEMPLO-001', status: 'partial', commit: null,
  summary: 'Coleta parcial: uma hipótese ilustrativa e testes não executados.',
  findings: [{ id: 'EXEMPLO-H01', status: 'suspected', severity: 'medium',
    summary: 'Possível referência ausente em um prefab de exemplo',
    evidence: [], file: 'Assets/Exemplo/PrefabIlustrativo.prefab', line: null,
    recommendation: 'Validar a propriedade serializada em uma cópia isolada antes de confirmar a ocorrência.' }],
  checks: [
    { name: 'Estado do Git', status: 'passed', note: 'Coleta ilustrativa; nenhum commit real foi consultado para esta prévia.' },
    { name: 'Logs do Editor', status: 'partial', note: 'Uma hipótese de exemplo, sem evidência real anexada.' },
    { name: 'EditMode / PlayMode', status: 'skipped', note: 'Fora do perfil leve. Não significa que os testes passaram.' },
    { name: 'Compilação e assets', status: 'skipped', note: 'Dependem de uma auditoria completa em cópia isolada.' },
  ],
};
