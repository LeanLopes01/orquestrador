# Handoff para Claude — execução, telemetria e aprovação no celular

Atualização de 22/10/2026: a seleção de Codex/Antigravity para planejamento e o encaminhamento a Claude estão especificados em [Seleção do agente da preliminar](claude-selecao-agente-preliminar.md). Esse novo documento substitui a inferência visual de Antigravity para jobs com agente nulo descrita abaixo: agora eles aparecem como Coordenador, e novos jobs devem informar o agente real.

Data: 22/10/2026. Pedido do usuário: Codex implementa somente a UI; Claude conclui a lógica. O usuário relatou que o executor Claude abriu um CMD vazio e ficou minutos sem atividade aparente, e que consegue ler respostas/reports no celular, mas não aprovar planos.

## Diagnóstico posterior confirmado — tela preta e plano de skins dos dados

Após a entrega inicial, foi reproduzida a tela preta no site real: `Cannot read properties of null (reading 'toLowerCase')`. O servidor retorna `agent: null` nos jobs de coordenação. A UI agora aceita agente nulo/ausente/vazio; propósitos `plan` e `report` são exibidos como Antigravity, conforme o despacho atual do backend. Outros agentes não informados aparecem como Coordenador. Também há recuperação de erro de renderização, preservando a navegação e sem reenviar ações. Testes específicos: `tests/ui/projects-recovery.spec.ts`.

Conversa `6b2bd4b0e0a34888be3ffc2745b9742f`, job `9d42ceef85f044749788c8cc563c110d`: o resultado persistido e o stderr mostram `tools refused: RunCommand`. O CLI não pôde pedir permissão `command` no modo headless e negou a ferramenta automaticamente. Houve nova tentativa e a recusa persistiu. A operação era uma busca de referências C# no workspace. Não foi registrada falha de cota/tokens nessa execução; a telemetria registra consumo, não saldo da assinatura.

O resultado traz `status: SUCCESS` e `exit_code: 0`, mas resposta vazia, `structured: null`, `denied` preenchido e `ok: false`. Preserve a interpretação de falha; não considere só o exit code. A causa específica deste plano não é o travamento de Claude relatado anteriormente.

O backend ativo já entrega `activity`, `events` e `usage` nesta conversa; as descrições abaixo sobre ausência desses campos referem-se à entrega inicial. Antes de alterar o executor, compare a versão atual. Para a recusa de ferramenta, implementar um fluxo explícito de autorização ou política estritamente delimitada para comandos necessários, respeitando recusas. Não habilitar bypass geral de permissões nem repetir silenciosamente a mesma operação negada. Nenhuma permissão ou lógica do executor foi alterada pelo Codex neste diagnóstico.

### Correção da recusa de ferramenta (Claude, 22/10/2026)

**Causa exata.** Os eventos salvos do job `9d42ceef` mostram 9 comandos de busca aceitos e 2 recusados, um em cada tentativa: `… | Select-String -Pattern "Dados3D|GerenciadorDados3D"` e `… | Select-String -Pattern "OpenFileDialog|FileBrowser|LoadImage|persistentDataPath" | …`. Ambos eram somente leitura. A regra de `agy_setup.py` proibia `|` em qualquer argumento, inclusive **dentro de aspas**: a alternância da regex era lida como pipe para um comando não permitido. A nova tentativa recebia um prompt que não explicava isso e caía na mesma armadilha com outro padrão (não repetiu a mesma operação).

**Política (estritamente delimitada, sem bypass).** Continua sendo uma única regra `permissions.allow` em `~/.gemini/antigravity-cli/settings.json`, instalada por `python -m jarvis_desktop install-orchestrator` (backup automático do settings). Mudanças:

- Argumentos entre aspas podem conter `| ; & ( ) { } < >`, que o PowerShell trata como texto. Aspas simples são totalmente literais; dentro de aspas duplas `$` e crase continuam proibidos (expandem variáveis/subexpressões).
- Fora de aspas nada muda: sem `;`, `&`, `$`, crase, parênteses, chaves, redirecionamento; `|` só entre os comandos de leitura permitidos.
- Brechas fechadas, que já existiam ou surgiriam com as aspas: **quebra de linha** (a regra antiga aceitava `\n`, que executa uma segunda linha) e **aspas Unicode** `‘ ’ “ ”`, que o PowerShell também usa como delimitadores e poderiam esconder um `; Remove-Item`.

**Retentativa e diagnóstico.** O prompt da segunda tentativa agora explica a regra das aspas, manda não repetir o comando recusado e, se ainda faltar informação, responder com o que foi verificado e o que falta — sem contornar a recusa. O resultado do job guarda `denied_commands` (as linhas exatas recusadas) e `problem` passa a citar o comando, em vez de só `RunCommand`. Sucesso continua exigindo `structured_output`; `exit_code 0` com recusa segue como falha.

**Evidências.**

- `tests/test_agy_rule.py`: os 2 comandos reais recusados e outros de leitura passam; `;`, `&`, `$(…)`, `"$env:…"`, crase escapando aspas, redirecionamento, `\n`/`\r\n`, aspas Unicode, aspas sem fechamento, pipe para `Remove-Item`, `Set-Content` e `Invoke-Expression` são recusados. Suite Jarvis: 215 testes, ruff limpo.
- `agy` real, modo headless: o comando exato recusado em 22/10 rodou e encontrou o arquivo esperado; `Get-Content victim.txt; Remove-Item victim.txt` em modo `accept-edits` foi negado pela política (`permission check failed`) e o arquivo permaneceu.
- Aplicado ao checkout real (backup `.local/backups/20261022-104712`), regra reinstalada e helper reiniciado. Não exige deploy do servidor.

**Não feito:** um fluxo interativo de autorização (pedir no celular a liberação de um comando fora da política). Com a política corrigida, a busca de referências C# não precisa dele; se for desejado para outros comandos, precisa de contrato próprio (pedido, aprovação com expiração, escopo de um único comando) e não deve virar bypass geral.

## Estado da entrega do Codex

Foram alterados somente componentes e cliente HTTP da interface React, CSS, testes de UI e este documento. Nenhum executor, bridge Python/Node, serviço Jarvis, permissão, app Flutter ou deploy foi alterado. O build gera `dist/`.

- `src/ProjectsPanel.tsx`: sincronização, erros de ações persistentes, feedback da decisão e planos pendentes antes da conversa. Uma falha ao consultar o runtime não impede a leitura da conversa. Respostas de uma seleção anterior são descartadas.
- `src/ExecutionMonitor.tsx`: cartões Antigravity/Claude/Codex, filtro, etapa, tempo desde o sinal, duração, saída e stderr separados, eventos, resumo de raciocínio e consumo por job.
- `src/PlanReview.tsx`: plano legível, todos os campos preservados, JSON/hash acessíveis, aprovação/rejeição com alvos de toque e motivo de bloqueio explícito.
- `src/projects.ts`: tipos e contrato HTTP. Timeout visual de 20 s; não cancela o processo executor. Solicitações POST continuam usando o cabeçalho `X-Orchestrator-Request: 1`.
- `src/projects.css`: layout responsivo e atalho fixo no celular para revisar o plano. O atalho não aprova nada e não altera a rota `#projects`.
- `tests/ui/projects-monitor.spec.ts`: dados simulados para verificar monitor, consumo ausente/zero, aprovação por toque, HTTP 403/409/503 e perda de sincronização. Não executa agentes reais.

A UI considera o snapshot do plano desatualizado após falha de leitura ou 30 s sem leitura bem-sucedida. O servidor continua responsável por autorizar e validar cada decisão. O alerta de 90 s sem sinal é apenas informativo; não diagnostica travamento. Os cartões usam o job ativo em destaque ou o mais recente, dentro dos jobs retornados na conversa; não representam consumo total da conta.

## 1. Investigar e corrigir o executor que fica sem saída

Trabalhe no checkout real `C:\J.A.R.V.I.S\jarvis` após ler suas instruções locais. Não edite `.local/jarvis-work` como se fosse a instalação ativa: essa pasta neste repositório foi usada para preparar uma entrega anterior.

Comece por `src/jarvis_desktop/agent_jobs.py`, `src/jarvis_desktop/coding.py` e `src/jarvis_control/orchestrator.py`. Correlacione conversation_id, plan_id, run_id, task_id e job_id com o log `%LOCALAPPDATA%\JarvisDesktop\desktop.log`. A causa do CMD vazio não foi reproduzida nem confirmada nesta entrega.

Verifique, com evidência:

1. A linha de comando efetivamente iniciada, binário resolvido, versão instalada, diretório de trabalho, ambiente necessário e código de saída. Evite registrar credenciais e prompts sensíveis sem tratamento.
2. Se o processo espera stdin, login, confirmação de ferramenta, shell interativo ou fechamento de um pipe. Consuma stdout e stderr simultaneamente e verifique buffering, encoding e EOF.
3. Se a demora está na cópia/preparação do workspace, no despacho, no primeiro token ou numa ferramenta. Publique a etapa correta desde o início, antes de haver stdout.
4. Heartbeat independente de saída textual, hora da última saída, timeout de inicialização, timeout total, cancelamento e encerramento da árvore de subprocessos. Não finalize só por falta de tokens: alguns CLIs só imprimem ao concluir.
5. Preserve isolamento do workspace, limites de caminhos e revisão antes de aplicar ao projeto. Não contorne aprovação de ferramenta com permissões irrestritas para fazer o CLI funcionar.

Use os formatos de streaming realmente suportados pelas versões instaladas de Claude, Codex e Antigravity; consulte a ajuda/documentação delas antes de escolher flags. Não pressuponha que os três seguem o mesmo protocolo. Evite abrir CMD vazio para um subprocesso não interativo: capture e apresente os eventos pela interface, com diagnóstico claro quando interação externa for necessária.

## 2. Conectar a telemetria preparada na UI

A UI consome `GET /api/orchestrator/v1/conversations/{id}`; a bridge encaminha para `/v1/conversations/{id}`. Hoje os campos reais conhecidos são `jobs[].progress.stage`, `stdout_tail` e `stderr_tail`, além dos estados e timestamps do job. A persistência do servidor consultada mantém uma allowlist desses três campos e converte os valores para string. Portanto, **novos campos estruturados precisam de validação e persistência próprias**, não de conversão indiscriminada para string.

Contrato aditivo esperado pelo frontend (exemplo ilustrativo, não dados reais):

```json
{
  "id": "job-id",
  "agent": "claude",
  "state": "running",
  "purpose": "Implementar seleção por toque",
  "started_at": 1792670000,
  "finished_at": null,
  "updated_at": 1792670030,
  "progress": {
    "stage": "running",
    "activity": "Lendo o controlador de seleção",
    "stdout_tail": "Saída sanitizada do processo",
    "stderr_tail": "",
    "reasoning_summary": "Resumo público das decisões fornecido pelo agente",
    "events": [
      { "id": "job-id:1", "at": 1792670029, "kind": "tool", "text": "Leitura de arquivo iniciada" }
    ],
    "usage": {
      "model": "modelo efetivamente usado",
      "input_tokens": 1234,
      "output_tokens": 42,
      "cost_usd": 0.01,
      "source": "provider"
    }
  }
}
```

Regras do contrato:

- Timestamps são segundos Unix, como no contrato existente. `updated_at` significa sinal recebido do executor, não uma mera leitura da UI. `finished_at` congela a duração ao terminar.
- Campos novos são opcionais. Ausência significa desconhecido, nunca zero. Números de consumo são finitos e não negativos. `cost_usd` só deve ser enviado com evidência de cobrança; não converter tokens em custo da assinatura arbitrariamente.
- `usage` é consumo cumulativo daquele job, e não do último fragmento nem de toda a conta. `events` é uma janela ordenada com IDs estáveis, não apenas o último delta. A UI atual substitui o snapshot a cada leitura, sem agregar eventos nem somar tokens.
- Limite tamanho/quantidade de eventos, activity e summary; preserve limites e remoção de segredos dos logs. Proposta inicial: até 100 eventos por snapshot, 2.000 caracteres por evento e 6.000 por resumo. Ajuste ao limite total da bridge e documente.
- Não envie cadeia de pensamento interna privada, tokens ocultos ou blocos internos de raciocínio. Use comentários públicos, ações de ferramentas e resumos de decisões que o executor realmente disponibilize.
- Sem dados disponíveis, omita o campo e mantenha a UI honesta. Não simule uso, percentuais, limites ou atividade para preencher os cartões.
- Cotas da assinatura/limites da conta ainda não têm contrato neste frontend. Se houver fonte confiável e autorizada, entregue um contrato próprio por provedor com origem, janela, instante de observação e reset; adicione sua apresentação sem confundir cota da conta com uso de um job. Na ausência de fonte, preserve “não informado”.
- A UI continua consultando a cada 5 s. Garantir reconexão, persistência e finalização é responsabilidade do transporte/servidor. Se mudar para streaming, preserve a recuperação por snapshot e não duplique eventos.

## 3. Corrigir a aprovação no Android

A UI web responsiva foi ajustada e testada por toque. Isso não atualiza o APK do S23 FE e não resolve automaticamente permissões ou erros do servidor. A bridge local em `services/jarvis-bridge.mjs` só aceita loopback; o app Android usa o servidor Jarvis. Não abra a bridge local para qualquer origem para tentar corrigir o celular.

Arquivos encontrados no checkout real:

- `C:\J.A.R.V.I.S\jarvis\livekit_flutter_starter-main\lib\screens\projects_screen.dart`
- `C:\J.A.R.V.I.S\jarvis\livekit_flutter_starter-main\lib\master\project_ctrl.dart`
- `C:\J.A.R.V.I.S\jarvis\src\jarvis_control\web.py`
- `C:\J.A.R.V.I.S\jarvis\src\jarvis_control\orchestrator.py`

Evidências de leitura, não diagnóstico fechado:

- `_PlanCard` mostra botões quando `state == proposed`; a tela escolhe `plans.last`, dependendo da ordenação retornada pelo servidor.
- `ProjectCtrl.decide` chama `_api.decidePlan` com id/version/hash. Sucesso e `JarvisCommandException` são anunciados via `_master.say`; o método lido não guarda um erro visual de decisão. Há um `await` da fala antes de reabrir a conversa, e outros tipos de exceção não são tratados nesse bloco.
- As rotas Projects no `web.py` local usam `require("work", work=True)`. Não é correto presumir que promover o Samsung a master resolve a falha. Confirme a versão realmente publicada e o perfil `work_access` autorizado.
- `orchestrator.decide` verifica runtime antes de aprovar. Leitura de reports/conversas funciona com PC offline; isso não comprova que pode executar um plano agora.

Reproduza no S23 FE e capture status HTTP, código e mensagem retornados, estado/versão/hash vistos e runtime/heartbeat. Verifique se há plano pendente real ou apenas report de um plano. Corrija com:

1. Seleção explícita da versão pendente mais recente; revisão legível; botão alcançável por toque e sem sobreposição do teclado.
2. Estado visual de envio, trava de toques repetidos, confirmação de aprovação/rejeição e erro persistente e legível. Voz opcional não deve bloquear a atualização da tela.
3. Tratamento de 401, 403 (`work_access`), 409 (versão/hash/estado), 503 (runtime), timeout e reconexão. Consulte a decisão persistida antes de repetir uma requisição cujo resultado é incerto.
4. Mesmo contrato de decisão da web: `POST /v1/plans/{plan_id}/approve` ou `/reject`, body `{ "version": 3, "hash": "hash exibido" }`. Validação e idempotência continuam no servidor; aprovação não autoriza aplicar resultados ao projeto original.
5. Atualizar a conversa após a resposta e após retomar o app. Preservar dados e sessão quando uma atualização falhar.

Não alterar o papel do Motorola nem trocar o pareamento do Samsung sem necessidade demonstrada. Compare código local, servidor publicado e versão do APK instalado antes de concluir a correção. Os scripts de publicação antigos documentam uma release anterior e não são um atualizador genérico.

## 4. Evidências exigidas para concluir a lógica

- Um pedido real passa por planejamento, revisão no celular, aprovação e despacho de um único run.
- Aprovar duas vezes não duplica execução; plano antigo/hash incorreto falha de forma visível; dispositivo sem autorização permanece bloqueado.
- Claude, Codex e Antigravity mostram etapa e heartbeat antes da saída textual, com uso/summary somente quando suportados e fornecidos.
- Reproduzir processo sem stdout, espera por entrada, falha de inicialização, timeout, cancelamento, queda de conexão e reinício. Nenhum desses estados fica indefinidamente como “executando” sem diagnóstico.
- Logs não vazam credenciais; snapshots e eventos permanecem limitados e recuperáveis.
- Validar em aparelho Android real, incluindo toque e reconexão. Testes mockados da web não provam funcionamento do APK ou do executor.

Para validar a UI nesta pasta:

```powershell
npm.cmd run build
npm.cmd run test:ui -- tests/ui/projects.spec.ts tests/ui/projects-monitor.spec.ts
```

## Execução por Claude (22/10/2026)

Alterações feitas em `.local/jarvis-work` e aplicadas ao checkout real com `scripts/apply-jarvis-local.py` (backup em `.local/backups/20261022-091846`). Helper do PC reiniciado com o código novo. Servidor e APK **ainda não publicados** (ver pendências).

### Causa do "CMD vazio" e da aparente trava (confirmada)

- Job `17d20f03` (Claude, 22/10): o CLI terminou com sucesso em 123 s às 07:08:38 (22 turnos, 4 arquivos), mas `parar-tudo.cmd` encerrou o helper às 07:08:47, antes do cálculo das alterações. Na volta (08:11) o job virou `unknown` e o resultado se perdeu, embora estivesse em disco.
- Janela vazia: o helper roda em `pythonw` (sem console); cada CLI de console ganhava um console **visível** próprio, com stdout no pipe. Medido com `AttachConsole`/`IsWindowVisible`: sem flag `visible: true`; com `CREATE_NO_WINDOW` nenhuma janela.
- Silêncio: Claude com `--output-format json` só imprime no fim; a UI recebia `stdout_tail` vazio por minutos.
- Codex resolvia para `codex.CMD` (cmd.exe): janela de CMD e prompt multilinha **cortado na primeira quebra de linha** (`%*`), com `&`/`|` interpretados pelo cmd.

### Correções (`src/jarvis_desktop`)

- `agent_jobs.py`: `CREATE_NO_WINDOW`; Codex pelo `codex.exe` nativo do pacote npm; qualquer outro `.cmd/.bat` é recusado; prompt de Claude/Codex por stdin (Antigravity não aceita stdin: argumento de exe nativo); etapa `finishing` visível; `exit.json` gravado ao fim do CLI e **recuperação do resultado** se o helper reiniciar depois disso; `preparing` agora também vira `unknown` num restart; atividade final (Concluído/Falhou/Cancelado/Interrompido).
- `job_stream.py` (novo): telemetria dos formatos realmente suportados — Claude `stream-json --verbose`, Codex `--json`, Antigravity `stream-json` (resultado em `{"event":"result","result":…}`, com `structured_output`). Blocos `thinking` do Claude nunca são lidos; `reasoning_summary` só com os resumos publicados pelo Codex. `usage`: tokens cumulativos do job (entrada inclui cache), `source` por CLI, sem `cost_usd` (o valor do Claude é preço de tabela, não cobrança da assinatura).
- `__main__.py` + `parar-tudo.cmd`: `stop` recusa (código 3) com jobs ativos e lista quais; o `.cmd` pergunta antes de `stop --force`.

### Telemetria no servidor (`src/jarvis_control/orchestrator.py`)

`progress_body` substitui a conversão para string: textos com limite (activity 500, tails/summary 6.000), `last_output_at`, até 100 eventos com `kind` ∈ {status, tool, message, error} e 2.000 caracteres cada, `usage` só com números finitos e não negativos. Limite total: 60.000 caracteres de eventos por job e eventos só nos 5 jobs mais recentes da conversa — a ponte local recusa respostas acima de 2,1 MB e a conversa lista até 30 jobs (100 × 2.000 × 30 passaria de 6 MB). `updated_at` continua sendo a recepção do relatório do helper (a cada 3 s, inclusive sem saída do CLI); o silêncio do CLI aparece em `activity` ("sem novos eventos há N s").

### Aprovação no Android

- Evidência: o plano v1 de 22/10 foi aprovado pelo dispositivo `79652afc` = **PC** (UI web), não pelo celular. `GET /v1/orchestration/runtime` = `local_runtime_offline` quando o Orquestrador (porta 1420) está fechado; nesse estado a aprovação devolve **503 `orchestrator_offline`**.
- No app, `decide()` só falava o resultado (via chamada com o agente de voz, até ~1 min) antes de atualizar a tela; sem trava de toque; exceções de rede/timeout eram engolidas. Ler conversas e aprovar usam o mesmo `require("work", work=True)`, então quem lê não está barrado por 401/403.
- Correção (`project_ctrl.dart`, `projects_screen.dart`): decisão única por vez; resultado persistente no cartão (401, 403, 409, 503, 429); timeout/rede → consulta o estado salvo antes de pedir novo toque; tela atualiza antes da voz (que não bloqueia mais); aviso de Orquestrador fechado antes do toque; plano escolhido = último `proposed`; botões de 48 dp; atualização ao voltar do segundo plano; telemetria renderizada (antes `progress.values.join` mostraria mapas crus).

### Evidências obtidas

- Testes: Jarvis Python 190 (15 novos em `tests/test_job_telemetry.py`, com amostras reais dos três CLIs); ruff limpo; `flutter analyze` sem problemas; `flutter test` 36 (5 novos em `test/project_decision_test.dart`) e companion 6.
- Execução real dos três CLIs pelo `JobManager` sob `pythonw`: Claude, Codex e Antigravity (plano com schema) concluídos; primeiro evento em ~9 s; tokens ao vivo; prompt com `& | ^ %PATH% "aspas"` e quebra de linha íntegro; nenhuma janela visível.

### Pendências (precisam do usuário/aparelho)

1. Deploy do servidor: `scripts\publicar-telemetria-aprovacao.cmd` (pede a senha sudo; só faz deploy, não muda papéis). Até lá o servidor publicado descarta os campos novos (compatível; só `stage`/tails aparecem).
2. APK do S23 FE: `.local/releases/jarvis-s23-companion-20261022-aprovacao.apk` → `adb -s RQCX8093BJY install -r <apk>`. O S23 não estava no adb nesta sessão; a reprodução no aparelho e a validação de toque/reconexão **não foram feitas**.
3. Fluxo ponta a ponta com o Orquestrador aberto: pedido real → plano → aprovação no S23 → um único run; aprovar duas vezes; hash antigo; aparelho sem `work`.
4. Cotas da conta: o `stream-json` do Claude traz `rate_limit_event` (utilização de 5 h/7 dias). Não foi exposto: falta o contrato próprio por provedor pedido acima.

## Cópias incrementais e contexto do RAG para o planejador (Claude, 22/10/2026)

**Problema.** Cada conversa nova copiava e re-hasheava o DiceVTT inteiro (8.770 arquivos, 373 MB, ~81 s) para `work/dicevtt/conversations/<id>/reference`; cada verificação no fim de um plano lia tudo de novo. Com 4 conversas e 1 run, a pasta de cópias tinha 51 mil arquivos (~1,9 GB).

**Mudança (só no helper do PC; não exige deploy do servidor nem do app).**

- `workspaces.py`: uma **referência compartilhada** por projeto (`work/<projeto>/reference`), sincronizada antes de cada plano. Um índice (`reference.index.json`: tamanho, mtime e sha256 de cada arquivo) faz com que só os arquivos novos ou alterados sejam copiados e hasheados; os removidos do projeto são apagados. `manifest()` também usa o índice e só lê os arquivos cujo tamanho/mtime mudaram, por isso a verificação no fim de cada job deixou de reler os 373 MB. Uma escrita sempre muda o mtime, então a edição de um agente é sempre detectada.
- `agent_jobs.py`: a referência não é sincronizada enquanto outro planejador a lê (lock + leitores); nesse caso o job usa a referência como está (`copy.synced = false`). A cópia de trabalho de um run é feita a partir da referência recém-sincronizada, reaproveitando os hashes, e a checagem de conflito no `apply` continua idêntica. Se o modo plano alterar a referência, o resultado ainda traz `reference_changed` e a próxima sincronização restaura os arquivos (antes, a cópia inteira era apagada).
- Limpeza (`clean_copies`, na partida do helper e antes de cada run novo): apaga as cópias antigas por conversa e os runs com mais de 7 dias ou além dos 8 mais recentes, nunca os que estão em uso. Na primeira partida, a cópia de conversa mais recente vira a semente da referência.
- `planning_context.py`: antes do planejador (Antigravity ou Codex), o helper pergunta ao RAG local (`/v1/rag/retrieve`, só busca, sem o gerador) pela última mensagem do usuário e anexa ao prompt os scripts relevantes (caminho, classe, resumo) e um trecho por página de documentação, com no máximo 6.000 caracteres. Com o RAG fora do ar ou sem espaço no argumento do Antigravity (limite de 30.000 caracteres), o plano segue sem esse contexto (`rag_context.used = false` no job).

**Medido no DiceVTT real.** Primeira sincronização completa: 81 s. Sem mudanças: 1,2 a 1,7 s, mais 3 a 5 s da consulta `cm status` do Plastic (mantida, registra a revisão). A primeira sincronização depois da semente copiou só 5 arquivos. Verificação no fim do plano: 0,7 s. Consulta ao RAG: 0,7 s. A pasta de cópias foi de 1,9 GB para 776 MB.

**Continua igual.** A cópia de trabalho de cada run aprovado ainda leva ~60 s (é uma pasta nova de 373 MB, mas sem re-hash). Hardlinks foram descartados porque uma edição no lugar alteraria a referência.

**Evidências.** `tests/test_workspace_sync.py` (13 testes): sincronização incremental, edição na cópia detectada e desfeita, manifesto sem releitura, run a partir da referência com conflito, arquivos somente leitura, limpeza, semente, referência compartilhada entre conversas, sem sincronizar durante a leitura e extração e formatação do contexto do RAG. Suite Jarvis: 247 testes; ruff limpo. Aplicado com backup em `.local/backups/20261022-195931`; helper reiniciado (referência semeada, 4 cópias antigas removidas).

## Mensagem curta para iniciar o trabalho

“Leia `D:\Programação\ProjetoLocais\Orquestrador\docs\claude-execucao-e-aprovacao.md`. O Codex entregou somente a UI. Corrija a execução que abre CMD vazio e parece travar, conecte a telemetria real de Claude/Codex/Antigravity ao contrato documentado e corrija a aprovação de planos no Android. Preserve a UI, o pareamento, as permissões e a separação entre aprovar execução e aplicar mudanças. Reproduza as falhas, corrija a lógica e valide o fluxo no celular real; não trate os testes mockados como prova de funcionamento do backend.”
