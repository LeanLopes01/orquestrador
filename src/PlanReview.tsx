import { CheckCircle2, ShieldCheck } from 'lucide-react';
import { label, type Plan } from './projects';

const fieldLabels: Record<string, string> = { pipeline: 'Configuração das etapas', planning: 'Planejamento', ui: 'Interface', coding: 'Implementação', stage: 'Etapa', model: 'Modelo', effort: 'Esforço', enabled: 'Habilitada', title: 'Título', goal: 'Objetivo', summary: 'Resumo', tasks: 'Tarefas', tests: 'Testes previstos', risks: 'Riscos', agent: 'Agente', key: 'Identificador', depends_on: 'Dependências', files: 'Arquivos', allowed_paths: 'Caminhos permitidos', acceptance: 'Critérios de aceite', instructions: 'Instruções', description: 'Descrição', prompt: 'Instruções' };
function PlanValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined || value === '') return <span className="muted">Não informado</span>;
  if (depth > 5) return <pre>{JSON.stringify(value, null, 2)}</pre>;
  if (Array.isArray(value)) return value.length ? <ol className="plan-values">{value.map((item, index) => <li key={index}><PlanValue value={item} depth={depth + 1}/></li>)}</ol> : <span className="muted">Nenhum item informado</span>;
  if (typeof value === 'object') return <dl className="plan-fields">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{fieldLabels[key] || key}</dt><dd><PlanValue value={item} depth={depth + 1}/></dd></div>)}</dl>;
  return <p>{String(value)}</p>;
}
export default function PlanReview({ plan, busy, runtime, fresh, onDecide }: {
  plan: Plan; busy: boolean; runtime: boolean | null; fresh: boolean;
  onDecide: (plan: Plan, decision: 'approve' | 'reject') => void;
}) {
  const proposed = plan.state === 'proposed';
  const blocked = !fresh ? 'Atualize a conversa para confirmar a versão mais recente do plano.' : runtime === false ? 'Para executar, abra o Orquestrador e o helper no PC. Depois toque em Atualizar.' : runtime === null ? 'A conexão com o executor ainda não foi confirmada. Toque em Atualizar.' : '';
  return <article id={`plan-${plan.id}`} className={`plan-review ${proposed ? 'pending' : ''}`} aria-label={`Plano ${plan.version}`}>
    <header className="monitor-heading"><div><span className="eyebrow">{proposed ? 'SUA DECISÃO' : 'HISTÓRICO DO PLANO'}</span><h3><ShieldCheck size={19}/> Plano {plan.version} · {label(plan.state)}</h3></div><span className={`badge ${proposed ? 'yellow' : 'gray'}`}>v{plan.version}</span></header>
    <PlanValue value={plan.body}/>
    <details className="plan-technical"><summary>Versão, hash e dados completos</summary><p>Versão {plan.version} · <code>{plan.hash}</code></p><pre>{JSON.stringify(plan.body, null, 2)}</pre></details>
    {proposed && <div className="plan-decision">
      <p>A aprovação autoriza a execução desta versão do plano. Aplicar as mudanças ao projeto é uma decisão separada.</p>
      {blocked && <p id={`blocked-${plan.id}`} className="telemetry-warning">{blocked}</p>}
      <div className="plan-buttons"><button type="button" className="button primary" disabled={busy || !!blocked} aria-describedby={blocked ? `blocked-${plan.id}` : undefined} onClick={() => onDecide(plan, 'approve')}><CheckCircle2 size={17}/>{busy ? 'Aguarde…' : `Aprovar plano ${plan.version} e executar`}</button><button type="button" className="button" disabled={busy || !fresh} onClick={() => onDecide(plan, 'reject')}>Rejeitar plano {plan.version}</button></div>
    </div>}
  </article>;
}
