# Handoff para Claude — seleção do agente de planejamento

22/10/2026. Pedido: substituir temporariamente Antigravity por Codex na preliminar e no planejamento; Claude executa após aprovação. Permitir selecionar o planejador na UI, com Grok reservado para integração futura.

## Entrega de UI

- `src/ProjectsPanel.tsx`: seletor no formulário de Projects, Codex padrão na primeira visita, Antigravity selecionável, Grok desabilitado. Preferência local em `orq.planning-agent.v1`, com tolerância a armazenamento indisponível. Vale para o próximo envio, novo pedido ou continuação, sem alterar jobs antigos.
- Fluxo visível: planejador → aprovação do usuário → Claude. A UI exige a capacidade do backend antes de enviar: um servidor antigo não pode ignorar o campo e executar Antigravity silenciosamente.
- `src/projects.ts`: contrato aditivo de runtime; agentes nulos aparecem como Coordenador, sem inferir Antigravity pelo propósito. O backend deve sempre registrar o agente real nos novos jobs.
- Idempotência inclui a escolha do planejador: mesma mensagem, conversa e agente reutilizam request_id após erro; mudança de agente gera outro identificador. Após timeout, conferir o pedido anterior antes de enviar outro.

Esta entrega altera somente UI, testes e documentação. O roteamento real ainda depende da implementação abaixo. Não anuncia Codex como operacional sem confirmação do executor.

Validação da entrega: `npm.cmd run build` passou; `node scripts/test-ui.mjs projects` passou com 15 testes. Inclui contrato dos dois agentes, persistência, continuação, idempotência, bloqueio do backend legado, aprovação e recuperação de erros. Captura mobile de 390 px inspecionada visualmente, sem overflow horizontal. Capturas em `.local/screenshots/planner-desktop.png` e `planner-mobile.png`. Não houve chamada real aos agentes.

## Contrato que a UI já utiliza

GET `/v1/orchestration/runtime`, mantendo campos existentes:

```json
{"online":true,"planning_routing":{"version":1,"agents":["codex","antigravity"],"execution_agent":"claude"}}
```

Retornar apenas planejadores implementados e habilitados. Não publicar a capacidade até servidor e helper suportarem o contrato completo. CLI instalado não comprova login/cota; falhas de execução devem retornar diagnóstico real.

POST `/v1/conversations` e `/v1/conversations/{id}/messages`:

```json
{"project":"dicevtt","text":"Pedido do usuário","request_id":"uuid","routing_version":1,"planning_agent":"codex","execution_agent":"claude"}
```

O servidor deve validar versão, enums, disponibilidade e autorização antes de enfileirar. Rejeitar agentes desconhecidos, Grok ainda não implementado e executor diferente de Claude com erro explícito. Nunca ignorar os campos ou trocar de provedor silenciosamente. A bridge existente já encaminha o JSON dessas rotas.

## Implementação do backend

1. Ler instruções do checkout real `C:\J.A.R.V.I.S\jarvis`. Inspecionar `src/jarvis_control/orchestrator.py`, `src/jarvis_desktop/agent_jobs.py` e `src/jarvis_desktop/coding.py`; confirmar o fluxo atual antes de editar. A pasta `.local/jarvis-work` não é a instalação ativa.
2. Persistir planning_agent e execution_agent no pedido e no plano produzido, além do agent explícito no job. Jobs `plan` usam o planejador escolhido; tarefas aprovadas usam Claude. Preservar o contrato de plano estruturado, versão/hash, objetivos, passos e critérios de aceitação. Codex deve fazer a inspeção preliminar e produzir esse contrato, sem aplicar mudanças no projeto durante o planejamento.
3. Adaptar o executor Codex existente para a finalidade `plan`, verificando as flags da versão instalada. Reutilizar isolamento, contexto/RAG, captura de eventos, cancelamento e limites. Não liberar permissões gerais para contornar erros. Sucesso requer resultado estruturado válido, além de saída/processo bem-sucedidos.
4. Aprovação deve despachar Claude usando o roteamento imutável do plano aprovado. Uma seleção posterior na UI não modifica planos, jobs ou execuções anteriores. Preservar a revisão/aprovação para aplicação de mudanças ao projeto.
5. Auditar também jobs `report` e qualquer dependência oculta de Antigravity: para pedidos novos roteados para Codex, usar Codex na síntese final, ou concluir com relatório estruturado do executor sem nova chamada a Antigravity. Persistir essa decisão por execução. Documentar o comportamento adotado.
6. Compatibilidade: dados históricos sem roteamento mantêm sua origem; não reescrever histórico. Para novos pedidos de clientes antigos que omitem campos, usar Codex → Claude como padrão temporário no servidor. Não reexecutar automaticamente jobs falhos/pendentes antigos; uma retomada deve ser uma ação explícita, com novo plano quando necessário.
7. A idempotência deve comparar o conteúdo completo, inclusive roteamento. Repetição idêntica retorna o mesmo pedido; mesma chave com conteúdo diferente retorna conflito. Guardar seleção por pedido, não em variável global mutável.
8. Ao esgotar cota, registrar falha e horário de liberação quando disponível; não insistir em loop nem fazer fallback silencioso. Disponibilizar agente real, etapa, eventos, uso e erros ao monitor. Manter processos não interativos sem janela vazia.
9. Integrar servidor e helper e só então anunciar `planning_routing`. Atualizar o cliente móvel posteriormente para a mesma escolha; até lá ele usa o padrão explícito do servidor.

## Critérios de aceitação para Claude

- Pedido novo e continuação com Codex geram um job Codex de planejamento; nenhum subprocesso Antigravity é iniciado nesse fluxo, inclusive na conclusão.
- Plano só executa após aprovação válida de versão/hash e despacha Claude. Rejeição não executa nada.
- Antigravity selecionado usa Antigravity; cota esgotada é reportada sem repetição infinita. Grok continua indisponível.
- Trocar agente com jobs em andamento não altera esses jobs. Pedidos simultâneos preservam suas próprias escolhas.
- Testar idempotência, agentes inválidos, backend/helper incompatíveis, falhas de login/cota, cancelamento e retomada explícita.
- Testes da UI usam respostas simuladas; validar o fluxo real com um pedido pequeno após implementar backend. Não confundir build/UI aprovada com integração funcional.

## Implementação do backend (22/10/2026)

Arquivos em `C:\J.A.R.V.I.S\jarvis`: `src/jarvis_control/orchestrator.py`, `src/jarvis_control/web.py`, `src/jarvis_desktop/agent_jobs.py`, `src/jarvis_desktop/orchestrator_runtime.py`; testes em `tests/test_planner_routing.py` e `tests/test_orchestration.py`. Backup do que foi substituído: `.local/backups/20261022-193342`.

- **Capacidade.** O helper responde `routing_version: 1` e `planning_agents: ["codex","antigravity"]` em `orchestrator.runtime`. O servidor só publica `planning_routing` quando o helper anuncia isso, e lista apenas os planejadores aceitos pelos dois lados. Com helper antigo, a capacidade fica oculta e qualquer pedido, inclusive o padrão, recebe 503 `planner_unavailable`. Nada é enviado a um helper que planejaria com Antigravity sem avisar. A lista não confere login nem cota: esses erros aparecem na execução.
- **Validação.** `routing_version` precisa ser o inteiro 1. Grok retorna 400 `agent_unavailable`; um planejador desconhecido, 400 `unknown_agent`; executor diferente de `claude`, 400 `unsupported_executor`. Campos parciais retornam 400 `unsupported_routing`. Pedido sem nenhum campo (app móvel atual) usa Codex → Claude, e esse padrão fica registrado no pedido.
- **Persistência.** A mensagem do usuário guarda `data.routing` e `request_hash`. Os jobs `coordinate` levam `agent`, `planning_agent` e `execution_agent` em `params`, então o monitor mostra o agente real. `plans` e `runs` ganharam colunas próprias. Linhas antigas ficam NULL e mantêm a origem.
- **Plano.** No pedido roteado, o schema só permite tarefas com `agent` igual ao executor. Se o plano trouxer outro agente, ele é recusado com motivo, sem troca automática. O hash continua calculado sobre o corpo do plano. A aprovação exige a versão e o hash como antes e confere de novo o executor registrado.
- **Codex planejador.** O comando é `codex exec -C <cópia de referência> -s read-only --skip-git-repo-check --json --output-schema schema.json -o last_message.txt -`, com o prompt pelo stdin e sem janela de console. O sucesso exige saída 0, nenhum `turn.failed` e JSON válido em `last_message.txt`. A cópia de referência ainda é conferida pelo manifesto. A nova tentativa após comando recusado continua exclusiva do Antigravity.
- **Relatório final (item 5).** A run guarda `report_agent`, que é o planejador do plano aprovado. Em pedido roteado para Codex, o próprio Codex escreve o relatório, em modo somente leitura, e nenhum processo Antigravity é iniciado. Runs de planos antigos, sem roteamento, continuam com relatório do Antigravity.
- **Cota.** Quando um job falha, o helper procura sinais de limite de uso nos erros, no stderr e no texto. Ele registra `quota_exhausted`, `retry_at` quando o CLI informa o horário e a mensagem original. O problema aparece na conversa. Não há nova tentativa nem troca de agente. A retomada acontece só com uma nova mensagem explícita, que gera novo plano. O `tick` não reenvia jobs que falharam.
- **Idempotência.** O `request_hash` cobre projeto, conversa, texto e roteamento. Repetir o mesmo pedido devolve a mesma conversa. Reusar a chave com outro conteúdo retorna 409 `request_conflict`. Mensagens antigas sem hash mantêm o comportamento anterior.

Validação: suíte completa do Jarvis com 234 testes, ruff check/format limpos e `node scripts/test-ui.mjs projects` com 15 testes. Também rodei o Codex 0.163 de verdade com o comando acima e o schema do plano num projeto mínimo. Ele retornou plano estruturado válido, todas as tarefas com `claude`, e o arquivo continuou intacto. O helper do PC foi atualizado e reiniciado. **Falta:** o deploy do servidor (`scripts/publicar-roteamento-planejador.cmd`, pede sudo) e, depois dele, um pedido pequeno real pela UI. Sem esse deploy, a UI continua bloqueada como esperado.

## Grok futuro

Adicionar adaptador e validar autenticação, assinatura/cobrança, execução headless e formato de plano antes de anunciar disponibilidade. Depois estender o enum/capacidades e liberar a opção na UI. Assinar Grok Bot não comprova acesso programático ao executor desejado.
