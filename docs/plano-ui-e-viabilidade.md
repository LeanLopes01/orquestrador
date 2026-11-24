# Orquestrador — UI primeiro

> Plano inicial da UI. A rota Projects agora executa pedidos reais pelo Jarvis; as demais telas de demonstração continuam identificadas. Estado atual e trabalho restante: [Integração Jarvis e S23 FE](integracao-companion.md).

## Decisão e escopo desta entrega

Criar a interface em React + TypeScript, com Vite para desenvolvimento e uma casca Tauri 2 para desktop. A UI terá navegação, formulários, filtros, inspeção de tarefas, revisão, reports exportáveis e preferências persistidas. Execuções de exemplo serão explicitamente marcadas como demonstração. Tarefas criadas serão rascunhos locais: nenhuma chamada paga, comando Git, execução Unity ou merge será disparado nesta fase.

## Composição visual

Tema escuro de estação de trabalho, acento verde-menta, tipografia de sistema, navegação lateral persistente e conteúdo com boa densidade. Telas: Visão geral, Tarefas, Execuções, Revisão, Contexto, Reports Jarvis e Configurações. Estados vazios, falhas, carregamento, responsividade e navegação por teclado fazem parte da entrega.

- Visão geral: próxima decisão, pipeline, tarefas recentes e disponibilidade dos agentes.
- Tarefas: kanban filtrável, criação com objetivo/escopo/aceite/orçamento, detalhes e cancelamento de rascunhos.
- Execuções: etapas, evidências e logs de demonstração.
- Revisão: diff ilustrativo, testes e decisão simulada. Aprovar não significa integrar Git.
- Contexto: grafo de wikilinks, busca e seleção de fontes reais; prévia, status LightRAG e composição de uma janela com limite explícito. Conteúdo mantido localmente.
- Reports: prévia Markdown e exportação JSON no contrato observado do Jarvis, sem envio implícito.
- Configurações: caminhos, orçamento e política de compartilhamento; segredos fora do navegador.

## Descobertas locais (19/10/2026)

O workspace tinha apenas o plano original, sem aplicativo ou repositório Git inicializado.

`C:\J.A.R.V.I.S\jarvis` já contém `jarvis_control/orchestrator.py`, `jarvis_desktop/agent_jobs.py`, workspaces, outbox persistente e eventos confirmados pelo servidor. Eventos entram pelo WebSocket do desktop; `GET /v1/events` e `GET /v1/reports/{event_id}` são leitura. Não existe um `POST /v1/reports` genérico no código inspecionado. Não criar um segundo executor disputando as mesmas tarefas: definir um único dono de cada execução.

`C:\J.A.R.V.I.S\JanelaContextoPessoal\Interface` é o Cérebro em PyQt6: grafo Obsidian, chat JSONL e telemetria. `.brain` contém LightRAG e um servidor `/query` na porta 8765. A configuração atual exclui C# e Assets por custo/latência. Logo, esse índice sozinho não representa o contexto do VTT. A UI será portada conceitualmente, com adaptador de leitura local e sem copiar todo o acervo, caches ou credenciais.

## Sequência para viabilidade

1. **UI validada:** fluxos navegáveis, contexto real em leitura, contrato dos reports e empacotamento inicial.
2. **Núcleo durável:** FastAPI + SQLite WAL, migrações, projetos/tarefas/eventos, máquina de estados, cancelamento, leases e recuperação após reinício. Migrar rascunhos do navegador com validação.
3. **Uma fatia vertical:** um planejador e um implementador, worktree por tarefa, evidências versionadas, teste Unity real e revisão humana. Revisores adicionais entram depois de esse fluxo funcionar; evitar tornar seis fornecedores requisito inicial.
4. **Contexto confiável:** indexação incremental de Markdown e C#, SQLite FTS5, hash/commit/símbolo por trecho, detecção de fonte alterada e orçamento pelo tokenizer do modelo. O grafo de notas e status LightRAG são visões auxiliares, não prova de contexto atualizado.
5. **Jarvis:** adaptador autenticado via helper/outbox existente, contrato versionado, IDs idempotentes, ACK, retry/backoff e remoção de segredos. Exportar agora; enviar somente após configurar destino e autenticação. Aprovação remota exige identidade e vínculo com o hash exato do diff.
6. **Produção local:** cofre Windows, allowlist de comandos, limites de custo/tempo, testes de falha, backup, instalador assinado e atualização.

## Dados ainda necessários

- Caminho Git do VTT e versão/caminho exatos do Editor Unity.
- CLIs/APIs autorizadas, modelos e método de autenticação. Não pressupor créditos API por assinatura de chat.
- Limites de custo e quais fontes podem sair do computador.
- Escolha de autoridade: este serviço executa e Jarvis recebe reports, ou este painel controla o executor do Jarvis. Recomendação inicial: serviço local executa tarefas Unity e publica reports; Jarvis não as executa novamente.
- Credenciais de pareamento do helper Jarvis, fornecidas pelo cofre, não por formulários persistidos no frontend.
- Projeto pequeno com testes EditMode/PlayMode para validar o ciclo real.

## Estado após a primeira implementação

- [x] Sete telas navegáveis, criação/cancelamento de rascunhos, persistência local, filtros e preferências.
- [x] Revisão com diff e confirmação explicitamente simulados; reports Markdown/JSON exportáveis.
- [x] Leitor local do vault e portabilidade conceitual da janela Cérebro: grafo, busca, fonte, SHA-256, data e seleção limitada por caracteres.
- [x] Leitura verificada: 34 notas, 33 wikilinks resolvidos e 34 estados `processed` no LightRAG; nenhum arquivo do acervo copiado.
- [x] Frontend compilado; quatro testes de leitor/contrato de reports; cinco cenários de UI incluindo 1440, 1024 e 390 px; `cargo check --offline` passou.
- [ ] Runtime FastAPI/SQLite, autenticação de adaptadores, comandos e agentes reais.
- [ ] Transporte autenticado e confirmação de entrega de reports ao Jarvis.
- [ ] Ponte de contexto no Tauri de produção, instalador e teste do executável empacotado. A ponte atual funciona em Vite dev/preview e no Tauri de desenvolvimento.

### Projeto confirmado e pré-checagem

O usuário confirmou `C:\ProjetoTablepRPG\DiceVTT`. `ProjectSettings/ProjectVersion.txt` aponta para **6000.3.10f1**, e `C:\Program Files\Unity\Hub\Editor\6000.3.10f1\Editor\Unity.exe` existe.

A raiz Git detectada é **C:\ProjetoTablepRPG**, não a subpasta DiceVTT. O serviço precisa conhecer separadamente `repository_root` e `unity_project_relative_path=DiceVTT`. Uma worktree deve ser criada a partir da raiz Git e os testes devem apontar para a subpasta Unity correspondente. O status inicial mostrou `.gitattributes` e `README.md` removidos no working tree; essas mudanças foram preservadas. Antes da primeira execução, decidir se essas exclusões são intencionais e preparar um estado inicial reproduzível.

O usuário de sandbox encontrou a proteção Git de ownership. Apenas o comando de leitura recebeu `-c safe.directory=C:/ProjetoTablepRPG`; nenhuma configuração global foi modificada. O aplicativo final deverá rodar no contexto do usuário dono do projeto.

## Critérios para chamar o MVP de operacional

Uma tarefa pequena sai do pedido, recupera fontes citadas, produz commit isolado, compila/testa no Editor correto, recebe revisão, apresenta diff e custo e só integra após aprovação humana vinculada ao commit. Reiniciar o aplicativo não perde nem duplica a tarefa; indisponibilidade do Jarvis não interrompe o trabalho; reports são entregues uma única vez do ponto de vista do usuário.

## Referências técnicas

- Tauri/Windows: https://v2.tauri.app/start/prerequisites/ (Rust, MSVC Build Tools e WebView2).
- Vite: https://vite.dev/guide/.
- Busca local FTS5: https://www.sqlite.org/fts5.html.
