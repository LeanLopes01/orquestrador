import { agentName, type ExecutionAgent } from './projects';

export type StageSettings = {agent: ExecutionAgent; model: string; effort: string; enabled: boolean};
export type Pipeline = Record<'planning' | 'ui' | 'coding', StageSettings>;
export const defaultPipeline: Pipeline = {
  planning: {agent: 'antigravity', model: 'gemini-4-argon', effort: 'high', enabled: true},
  ui: {agent: 'codex', model: '', effort: 'high', enabled: true},
  coding: {agent: 'claude', model: '', effort: 'high', enabled: true},
};
export function loadPipeline(): Pipeline {
  try {
    const saved = JSON.parse(localStorage.getItem('orq.project-pipeline.v1') || 'null');
    if (saved && Object.keys(defaultPipeline).every(k => saved[k] && ['antigravity', 'codex', 'claude'].includes(saved[k].agent) && typeof saved[k].model === 'string' && typeof saved[k].effort === 'string' && typeof saved[k].enabled === 'boolean') && saved.planning.agent !== 'claude') return saved;
  } catch { /* Use defaults when storage is unavailable. */ }
  return structuredClone(defaultPipeline);
}
const models = {
  antigravity: ['gemini-4-argon', 'gemini-3.8-flash'],
  codex: ['gpt-6.1-sol', 'gpt-6-astra', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-luna'],
  claude: ['opus', 'sonnet', 'haiku'],
};
export default function ProjectPipeline({value, onChange, disabled}: {value: Pipeline; onChange: (value: Pipeline) => void; disabled: boolean}) {
  const update = (key: keyof Pipeline, patch: Partial<StageSettings>) => onChange({...value, [key]: {...value[key], ...patch}});
  return <fieldset className="planning-selector" disabled={disabled}>
    <legend>Agentes e modelos por etapa</legend>
    <div className="project-pipeline">
      {(['planning', 'ui', 'coding'] as const).map((key, index) => {
        const stage = value[key];
        const efforts = stage.agent === 'antigravity' && stage.model.startsWith('gemini-') ? ['low', 'medium', 'high'] : stage.agent === 'claude' ? ['low', 'medium', 'high', 'max'] : stage.agent === 'codex' ? ['low', 'medium', 'high', 'xhigh', 'max', 'ultra'] : ['low', 'medium', 'high', 'xhigh', 'max'];
        return <section key={key} className="pipeline-stage" aria-label={`Etapa ${index + 1}`}>
          <h3>{index + 1}. {key === 'planning' ? 'Planejamento' : key === 'ui' ? 'Interface (UI)' : 'Implementação / código'}</h3>
          <p className="muted">{key === 'planning' ? 'Investiga e prepara o plano para sua aprovação.' : key === 'ui' ? 'Cria a interface quando o pedido precisar de UI.' : 'Implementa a lógica e integra o resultado da UI.'}</p>
          {key === 'ui' && <label><input type="checkbox" checked={stage.enabled} onChange={e => update(key, {enabled: e.target.checked})}/> Incluir UI quando necessária</label>}
          <fieldset disabled={!stage.enabled}>
            <label className="field">Agente — {index + 1}<select value={stage.agent} onChange={e => update(key, {agent: e.target.value as ExecutionAgent, model: '', effort: 'high'})}>{(key === 'planning' ? ['antigravity', 'codex'] : ['codex', 'claude', 'antigravity']).map(agent => <option key={agent} value={agent}>{agentName(agent)}</option>)}</select></label>
            <label className="field">Modelo — {index + 1}<input list={`models-${key}`} value={stage.model} maxLength={120} pattern="[A-Za-z0-9][A-Za-z0-9._:/-]*" placeholder="Padrão configurado no agente" onChange={e => update(key, {model: e.target.value, effort: 'high'})}/><datalist id={`models-${key}`}>{models[stage.agent].map(model => <option key={model} value={model}/>)}</datalist></label>
            <label className="field">Esforço — {index + 1}<select value={stage.effort} onChange={e => update(key, {effort: e.target.value})}><option value="">Padrão do agente</option>{efforts.map(e => <option key={e} value={e}>{e}</option>)}</select></label>
          </fieldset>
        </section>;
      })}
    </div>
    <p className="muted">Modelo vazio usa a configuração do agente. As sugestões foram verificadas neste PC; disponibilidade e combinações de esforço dependem da conta e do modelo. Não há troca automática se o modelo falhar.</p>
    <p className="planning-flow">Planejar → Você aprova → UI (se necessária) → Código → Revisão</p>
    <p className="muted">As escolhas valem para o próximo envio. Planos anteriores mantêm suas configurações.</p>
  </fieldset>;
}
