export type Item = { id: string; title: string; state: string; updated_at: number };
export type PlanningAgent = 'codex' | 'antigravity';
export type ExecutionAgent = 'claude' | 'antigravity' | 'codex';
export type Runtime = { online: boolean; planning_routing?: { version: 1; pipeline_version?: number; agents: PlanningAgent[]; execution_agent: ExecutionAgent; execution_agents?: ExecutionAgent[] } };
export type Plan = { id: string; version: number; hash: string; state: string; body: Record<string, unknown> };
// Optional display fields: the current server only supplies stage and log tails.
// The additive telemetry contract is described in docs/claude-execucao-e-aprovacao.md.
export type Usage = { input_tokens?: number; output_tokens?: number; cost_usd?: number; model?: string; source?: string };
export type Job = {
  id: string; agent: string | null; state: string; updated_at: number | null;
  started_at?: number | null; finished_at?: number | null; purpose?: string;
  progress: {
    stage?: string; stdout_tail?: string; stderr_tail?: string;
    activity?: string; reasoning_summary?: string; usage?: Usage;
    events?: { id: string; at: number; kind: string; text: string }[];
  } | null;
};
export type Conversation = Item & {
  messages: { seq: number; author: string; text: string }[];
  plans: Plan[]; jobs: Job[];
  runs: { id: string; state: string; report: unknown; tasks: unknown[] }[];
};
const states: Record<string, string> = {
  planning: 'Preparando plano', awaiting_approval: 'Aguardando aprovação', needs_input: 'Precisa da sua resposta',
  running: 'Executando', reviewing: 'Revisando resultados', idle: 'Conversa disponível', failed: 'Falhou',
  completed: 'Concluído', cancelled: 'Cancelado', queued: 'Na fila', preparing: 'Preparando ambiente',
  proposed: 'Aguardando aprovação', approved: 'Aprovado', rejected: 'Rejeitado', superseded: 'Substituído',
  timed_out: 'Tempo esgotado', skipped: 'Não executado', waiting_input: 'Aguardando entrada',
};
export const label = (state: string) => states[state] || state;
export const activeJob = (state: string) => ['queued', 'preparing', 'running', 'planning', 'reviewing', 'waiting_input'].includes(state);
export const when = (time: number) => new Date(time * 1000).toLocaleString('pt-BR');
export const age = (seconds: number) => seconds < 60 ? `${Math.floor(Math.max(0, seconds))} s` : seconds < 3600 ? `${Math.floor(seconds / 60)} min` : `${Math.floor(seconds / 3600)} h ${Math.floor(seconds % 3600 / 60)} min`;
export const agentName = (agent: string | null | undefined) => {
  const name = typeof agent === 'string' ? agent.trim() : '';
  return ({ claude: 'Claude', claude_code: 'Claude', 'claude-code': 'Claude', codex: 'Codex', antigravity: 'Antigravity', grok: 'Grok' }[name.toLowerCase()] || name || 'Coordenador');
};
// A missing agent is unknown: never infer a provider from the job purpose.
export const jobAgentName = (job: Job) => agentName(job.agent);
export const tone = (state: string) => ['failed', 'timed_out'].includes(state) ? 'danger' : activeJob(state) ? 'blue' : state === 'completed' ? 'mint' : 'gray';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(`/api/orchestrator/v1/${path}`, {
      signal: controller.signal, cache: 'no-store',
      ...(body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Orchestrator-Request': '1' }, body: JSON.stringify(body) }),
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const hint = response.status === 403 ? 'Este dispositivo não tem autorização para esta ação. O acesso precisa ser verificado no Jarvis.'
        : response.status === 409 ? 'O plano mudou ou já recebeu uma decisão. Atualize e confira a versão antes de tentar novamente.'
        : response.status === 503 ? 'Executor indisponível. Confira o Orquestrador e o helper no PC.' : `Jarvis respondeu HTTP ${response.status}.`;
      throw new ApiError(response.status, result.message ? `${hint} ${result.message}` : hint);
    }
    return result;
  } catch (error) {
    if (controller.signal.aborted) throw new Error('O Jarvis não respondeu em 20 segundos. Atualize para conferir se a ação foi registrada antes de tentar novamente.');
    throw error;
  } finally { clearTimeout(timer); }
}
