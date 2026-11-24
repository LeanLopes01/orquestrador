# Plano técnico — Orquestrador local de IAs para VTT Unity

## 1. Objetivo
Aplicativo independente instalado no computador para coordenar agentes de IA na evolução de um VTT feito em Unity 6.3 e C#. Execução automática das etapas, com aprovação humana obrigatória antes de integrar alterações à branch principal. O aplicativo funciona localmente; APIs de modelos externos exigem internet, autenticação e podem gerar custos.

## 2. Arquitetura proposta
- **Interface:** Tauri 2 + React + TypeScript. Painel de projetos, tarefas, agentes, diffs, logs, custos e aprovações.
- **Serviço local:** Python 3.12+ com FastAPI, processos assíncronos, filas persistidas e adaptadores de provedores.
- **Persistência:** SQLite em modo WAL para tarefas, estados, auditoria e custos; arquivos grandes de logs/artifacts em disco.
- **Controle de versão:** Git, branch ou worktree isolado por tarefa; nunca editar diretamente `main`.
- **Busca contextual (RAG):** documentos Markdown, código C#, decisões de arquitetura e documentação Unity indexados localmente; iniciar com busca textual/FTS5 e adicionar embeddings apenas quando necessário.
- **Ferramentas (MCP):** servidores MCP com permissões restritas para ler projeto, consultar cenas/objetos da Unity, disparar comandos permitidos e obter resultados. MCP não substitui RAG nem um orquestrador.
- **Execução de Unity:** testes EditMode e PlayMode por Unity Test Framework, preferencialmente em batchmode, com captura de relatórios e logs. PlayMode pode exigir ambiente gráfico e configuração específica.

## 3. Papéis dos agentes
| Agente | Papel | Entrega verificável |
|---|---|---|
| Codex / OpenAI | Planejamento técnico, decomposição, critérios de aceite | Plano JSON, lista de arquivos afetados, riscos e testes previstos |
| Claude / Anthropic | Implementação principal em C# | Commit isolado e explicação das mudanças |
| Gemini / Google | Revisão independente de arquitetura, bugs e desempenho | Parecer estruturado com severidade e referências aos diffs |
| OpenCode | Interface/runner de agentes para diagnóstico e correção, configurado com um modelo | Diagnóstico, patch e novos testes; OpenCode não é um modelo por si só |
| Grok / xAI | Segunda revisão e hipóteses alternativas | Lista priorizada de possíveis problemas |
| Modelo local via Ollama | Classificação de logs, resumo e tarefas auxiliares de baixo risco | Resumo de falhas e documentação |

**Importante:** disponibilidade de CLI, APIs, assinaturas, limites, integração MCP e autenticação varia conforme cada fornecedor. O orquestrador deve suportar adaptadores substituíveis e testar cada integração antes de ativar o fluxo automático. Evitar assumir que uma assinatura de chat inclui créditos de API.

## 4. Workflow automático — opção A
1. **Pedido:** usuário descreve a funcionalidade e define critérios de aceite.
2. **Pré-checagem:** validar estado limpo do Git, Unity instalada, orçamento, permissões e espaço em disco.
3. **Contexto:** recuperar documentação, código e decisões relevantes pelo RAG, citando arquivos e versões.
4. **Planejamento:** Codex devolve tarefas com dependências, riscos, interfaces, arquivos autorizados e testes.
5. **Validação do plano:** máquina valida esquema e conflitos; tarefas arriscadas exigem aprovação antecipada.
6. **Implementação:** Claude trabalha em worktree isolada; ferramentas limitadas ao escopo aprovado.
7. **Testes:** compilação, testes EditMode/PlayMode, verificações estáticas e análise de logs.
8. **Correção:** em falhas, OpenCode + modelo configurado recebem logs e diff; no máximo 2–3 tentativas, sempre reexecutando testes.
9. **Revisões:** Gemini e Grok revisam o diff, contratos e possíveis regressões; achados críticos voltam para correção.
10. **Entrega:** mostrar diff, resultados, custos, riscos e evidências; **usuário aprova** merge. Nunca fazer merge ou publicar automaticamente.

Estados sugeridos: `queued → retrieving → planning → implementing → testing → fixing/reviewing → awaiting_approval → merged`; também `failed`, `blocked`, `cancelled`.

## 5. Módulos da interface
- **Dashboard:** tarefas em andamento, agentes ativos, filas, erros, consumo de tokens/custo estimado.
- **Projetos:** diretório Unity, versão, branch principal, ambientes e configurações.
- **Kanban de tarefas:** backlog, planejamento, implementação, testes, revisão, aprovação.
- **Execuções:** linha do tempo com logs, comandos, artefatos e status por etapa.
- **Revisão:** diff Git lado a lado, resultados de testes, comentários de Gemini/Grok e botões aprovar/rejeitar.
- **Conhecimento/RAG:** fontes indexadas, versão, data, filtros e trechos recuperados.
- **Integrações:** configuração de provedores, MCPs, Ollama e Unity; teste de conexão.
- **Segurança e orçamento:** permissões, segredos, limite por tarefa e travas de execução.

## 6. Integração MCP com Unity
Criar adaptador que exponha apenas operações necessárias: `unity.get_project_info`, `unity.list_scenes`, `unity.inspect_gameobject`, `unity.run_editmode_tests`, `unity.run_playmode_tests`, `unity.get_console_errors`, `unity.refresh_assets`. O nome e a disponibilidade exatos dependem do servidor MCP escolhido ou implementado. Separar operações somente leitura de operações que alteram cenas/assets. Exigir confirmação para exclusão em massa, mudanças de configurações do projeto ou comandos arbitrários. Serializar operações que dependem de uma única instância do Editor.

## 7. RAG para o VTT
Fontes iniciais: `Assets/**/*.cs`, `Packages/manifest.json`, documentação técnica, ADRs, arquitetura de mapas/campanhas, grid, tokens, paredes, terreno, elevação, autenticação e contratos de API. Excluir `Library/`, `Temp/`, `Logs/`, builds, segredos e arquivos binários grandes. Armazenar `path`, `git_commit`, `symbol`, `chunk`, `hash` e data da indexação. Recuperar primeiro por caminho/símbolo e busca textual; expandir para embeddings locais conforme a qualidade das respostas. Cada agente deve receber somente trechos pertinentes e links internos para os arquivos originais.

## 8. Segurança e isolamento
- Credenciais no cofre do sistema operacional ou armazenamento criptografado; nunca em prompts, logs ou Git.
- Comandos em allowlist, execução com usuário sem privilégios administrativos, limites de tempo e recursos.
- Evitar transmitir código privado a provedores externos sem consentimento; configurar políticas por projeto/provedor.
- Bloquear acesso automático a produção, Stripe, Firebase, Supabase e credenciais reais.
- Usar banco e dados de teste, nunca banco de produção.
- Worktree por tarefa, snapshots, backup e rollback; aprovação manual para merge e mudanças destrutivas.
- Limitar custo por tarefa, tentativas de correção e profundidade de delegação.

## 9. Estrutura sugerida
```text
vtt-ai-orchestrator/
  apps/desktop/              # Tauri + React
  services/orchestrator/     # FastAPI + motor de estados
    agents/                  # codex, claude, gemini, grok, opencode, local
    workflows/               # definições e transições
    integrations/            # git, unity, mcp, rag
    storage/                 # SQLite, migrações
    security/                # políticas e credenciais
  config/                    # modelos de configuração sem segredos
  prompts/                   # instruções versionadas por papel
  tests/                     # testes do orquestrador
  docs/                      # ADRs e especificações
```

## 10. Contrato de tarefa (exemplo)
```json
{
  "task_id": "VTT-001",
  "goal": "Adicionar iluminação dinâmica aos mapas",
  "scope": ["Assets/Scripts/Lighting/**"],
  "acceptance": ["Sem erros de compilação", "Testes EditMode passam", "Sem regressão no carregamento de mapas"],
  "max_fix_attempts": 3,
  "max_budget_usd": 5,
  "merge_requires_human_approval": true
}
```

## 11. Plano de construção
**Fase 1 — Fundamentos:** Tauri, FastAPI, SQLite, abertura de projeto, logs, Git worktrees, configurações de modelos e cofres de segredo.

**Fase 2 — Pipeline ponta a ponta:** adaptadores de Codex e Claude; tarefas com estado persistido; execução de Unity Test Framework; correção com OpenCode; revisões Gemini e Grok; aprovação final. Todas as etapas presentes desde a primeira versão utilizável.

**Fase 3 — Contexto:** RAG local, indexação incremental, fontes citadas e integração MCP com Unity.

**Fase 4 — Robustez:** recuperação após falhas, retomada de tarefas, limites de custo, telemetria local, testes de regressão e instalador.

## 12. Primeiro teste real
Escolher uma tarefa pequena no VTT, por exemplo corrigir um bug de grid ou token. Registrar o estado inicial, gerar plano, implementar em worktree, executar testes, fazer revisões cruzadas e apresentar diff para aprovação. Medir taxa de sucesso, tempo, custo, número de tentativas e erros encontrados por cada agente antes de escalar para recursos complexos.

## 13. Decisões pendentes
1. Sistema operacional do computador (Windows/Linux/macOS) e caminho da instalação Unity.
2. Quais CLIs/APIs já estão instaladas e quais planos/chaves de API estão disponíveis.
3. Localização do repositório Git do VTT e se contém cenas grandes, assets binários e testes existentes.
4. Orçamento máximo por tarefa e quais arquivos/serviços podem sair do computador.
5. Qual implementação de MCP para Unity será utilizada e quais ferramentas ela realmente disponibiliza.

**Recomendação:** construir o aplicativo independente como orquestrador real, sem depender de automação de cliques no VS Code. Roo Code pode continuar como ferramenta opcional, mas não precisa ser o núcleo do sistema.

## 14. Execução iniciada — UI primeiro (19/10/2026)

O detalhamento atualizado está em [docs/plano-ui-e-viabilidade.md](docs/plano-ui-e-viabilidade.md). A primeira UI React/TypeScript foi implementada com dashboard, tarefas, execuções, revisão, janela de contexto, reports Jarvis e configurações. Instruções em [README.md](README.md).

Projeto confirmado: `C:\ProjetoTablepRPG\DiceVTT`; Unity `6000.3.10f1`. A raiz Git é `C:\ProjetoTablepRPG`, portanto o serviço deve distinguir raiz do repositório e subpasta Unity.

A janela de contexto reutiliza o conceito do Cérebro em `C:\J.A.R.V.I.S\JanelaContextoPessoal\Interface` e lê as notas e os status LightRAG locais por um adaptador somente leitura. Não foi copiado o acervo completo. C# ainda precisa de indexação própria.

Reports já podem ser exportados em Markdown e em JSON compatível com o validador de eventos inspecionado no Jarvis. A entrega autenticada pelo helper/outbox ainda será implementada. Jarvis já possui orquestrador: a integração deverá definir qual serviço é dono de cada execução para evitar duplicidade.

**Ajuste de prioridade à fase 2:** validar primeiro uma tarefa ponta a ponta com um planejador e um implementador, testes Unity e aprovação humana. Depois adicionar correções e revisores adicionais. Exigir todos os provedores antes do primeiro fluxo funcional aumenta o risco e o esforço inicial.

**Limite desta entrega:** a UI funciona, os rascunhos persistem localmente e o vault é lido de verdade no modo Vite. Execuções, testes, diffs e custos exibidos nos exemplos são simulados. Ainda não há execução de agentes, merge ou envio de reports ao Jarvis. A ponte de contexto no executável Tauri de produção é uma pendência explícita.
