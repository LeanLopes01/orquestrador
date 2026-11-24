# dicevtt_diagnostics — relatórios automáticos do DiceVTT

Runner local (127.0.0.1:8768) das entregas 1 e 2 do [plano](../../docs/plano-relatorios-automaticos-claude.md). Cada abertura do `iniciar-tudo.cmd` gera um relatório real do projeto, salvo neste PC e exibido em **Relatórios** (`/#reports`).

## Como roda

- O **helper Jarvis Desktop** sobe o runner junto com o RAG e a ingestão (`rag_service.py`, serviço opcional: sem `.local/diagnostics.toml` o resto sobe normalmente). Ele morre junto com o helper.
- O `iniciar-tudo.cmd`, logo depois de iniciar o helper e **antes** de verificar se a interface já está aberta, chama `request-startup` em segundo plano (`pythonw`). Esse comando cria um `startup_id`, espera o runner por até 30 s e faz até 2 POSTs de 5 s com a mesma chave. O resultado fica em `.local/audits/logs/startup.log`. A interface abre de qualquer jeito.
- Com "Gerar ao abrir" desligado nas preferências, a abertura é registrada como `disabled` e nenhum relatório é inventado.
- Ao reiniciar, um job que estava em andamento vira `interrupted` e não é reexecutado. Parar o helper durante uma coleta também grava `interrupted`. Cancelar pela UI grava `cancelled`.

## Perfil leve (`startup-light`, ~5 s; até ~60 s se o RAG ainda estiver subindo)

| Check | O que lê | Exemplos de ocorrência |
| --- | --- | --- |
| Controle de versão | `git` na raiz pai e `cm status` do Unity Version Control (`.plastic`) | itens apagados sem registrar exclusão; scripts `.cs` privados; Git pai sem o projeto |
| Unity, pacotes e scripts | `ProjectVersion.txt`, Unity Hub, `manifest.json`/`packages-lock.json`, `.asmdef`, inventário de `Assets` | editor ausente; Test Framework sem assembly de teste; scripts fora do `scripts_root` do RAG |
| Logs do Editor e do build | últimos 2 MB do `Editor.log` e do `Player.log` (hash do trecho lido) | erro/aviso **da última compilação**; exceções agrupadas por tipo + primeiro frame do projeto |
| RAG e acesso MCP | health do RAG (sem indexar nem gerar) e o registro `dicevtt-rag` no Claude Code e no Codex | RAG desligado ou degradado |

Regras de honestidade:

- O status do check descreve a **coleta**: `collected`, `partial`, `error` ou `skipped`. A gravidade fica nos achados. Git indisponível é erro de coleta, nunca "projeto sem versionamento".
- Um `Editor.log` de outro projeto é ignorado. Um log mais antigo que o script mais recente gera achados `suspected`, nunca `confirmed`.
- Na comparação com o run anterior, um achado só vira `resolved` se o check correspondente foi coletado por inteiro. Caso contrário, vira `not_rechecked` e continua contando como presente.
## Perfil completo (`full-audit`, entrega 4)

Roda sob demanda (botão **Auditoria completa**) ou na abertura, se escolhido nas preferências. Faz o perfil leve e depois os checks abaixo, todos numa cópia em `C:/DiceVTT-Audit` (`[full]` em `.local/diagnostics.toml`):

| Check | O que faz |
| --- | --- |
| Cópia isolada (snapshot) | Copia `Assets`, `Packages` e `ProjectSettings` da cópia de trabalho com SHA-256 por arquivo, sem seguir links nem junctions. A identidade é o hash da árvore mais o changeset e as pendências do Plastic. Na cópia, `productName` ganha o sufixo `-Audit`, então o `persistentDataPath` do editor da auditoria vira outra pasta; os `sistemas` são provisionados lá como cópia. Sem esse isolamento, os validadores não rodam. |
| Importação e compilação na cópia | `Unity -batchmode -nographics -quit` no snapshot. Erros e avisos da última compilação viram `isolated.compile-*` (confirmados). Licença indisponível e timeout são erro de coleta, não achado. |
| Referências de assets | Sem Unity. Cada `guid` de cena, prefab ou asset YAML precisa existir num `.meta` (Assets, Packages, `PackageCache` ou pacotes embutidos da Unity). Referências a classes dentro de DLLs usam guids internos da Unity e contam como **não verificáveis**, nunca como faltando. |
| Testes EditMode | Só roda se houver assembly de teste; sem nenhuma, fica "não executado" (zero testes não é aprovação). XML ausente é erro, zero testes é achado e cada teste que falha também. |
| Validadores do projeto | Os `-executeMethod` em lote listados em `[[full.validators]]`, um processo da Unity por validador. As linhas `FALHA`/`FALHOU`/`FAIL` do relatório viram achados (números normalizados na identidade). Saídas possíveis: sem falhas, com falhas, não rodou, tempo esgotado. Os que salvam cena ou prefab ficaram fora da lista. |
| Integridade da origem | Recalcula a árvore da origem no fim. Igual = a auditoria não mexeu em nada. Diferente = edição em paralelo (o editor aberto), registrada como informativa. |

Garantias:

- A Unity da auditoria roda com **prioridade abaixo do normal**, sem janela, num **job object próprio**. Cancelar ou estourar o tempo encerra só aquele processo e os filhos dele, nunca a Unity que você tem aberta.
- **Library:** usa um cache próprio, `C:/DiceVTT-Audit/cache/Library`, que entra e sai da cópia a cada run.
  - Sem cache, a `Library` só é semeada da origem se nenhum editor estiver com o projeto aberto (`Temp/UnityLockfile` travado). Caso contrário, a primeira importação é completa e lenta (`import_timeout_seconds`).
  - Restos de um run interrompido são recuperados como cache.
- **Limpeza:** ao terminar, cancelar ou interromper, os logs e relatórios de cada etapa vão para `runs/<run>/full/` e a cópia e os dados isolados são apagados.
- **Prazos:** 30 minutos por execução da Unity e 60 minutos no total (configuráveis).

Medido em 25/10/2026, com o editor aberto na origem. As durações valem para este PC.

| Execução | Snapshot | Importação | Referências | 9 validadores | Total |
| --- | --- | --- | --- | --- | --- |
| Primeira, sem cache de `Library` (`AUD-20261025-232404-4ed197`) | 78 s | 4 min (fria) | 117 s | — (ver nota) | 8,5 min |
| Segunda, com cache (`AUD-20261025-233315-073210`) | 28 s | 92 s | 59 s | 3,8 min (21–43 s cada) | 7,5 min |

A primeira execução tropeçou numa linha inofensiva do log de licença e marcou a importação como erro; o detector foi corrigido e coberto por teste. A segunda execução teve 7 validadores sem falhas e 2 com falhas (Guildas e a regressão de Salas). Ela também achou scripts ausentes em cenas e prefabs de produção. A origem ficou idêntica nas duas (`8d976e311fed`).

## Investigação por IA (entrega 5)

É opcional. Pode ser pedida em cada relatório ou ligada para rodar ao fim de todos ("Investigar com IA"). Roda numa **fila própria** e nunca atrasa as auditorias.

- **Escopo:** investiga as ocorrências alta, média e baixa presentes, as mais graves primeiro (`[ai] max_findings`).
- **Provedores:**
  - `local-rag` (padrão): AirLLM pelo RAG local, `/v1/rag/asks`. Nada sai do PC. Leva minutos por ocorrência no CPU.
  - `claude-code`: `claude -p` em lote, com MCP restrito ao `dicevtt-rag`, só `rag_buscar`/`Read`/`Grep`/`Glob`, hooks desligados e sessão não persistida. Envia trechos do código à Anthropic, então exige a autorização `allow_code_to_provider`. Essa autorização nunca vem de um arquivo importado.
- **Toda saída é hipótese.**
  - `supported` só quando cita uma fonte que existe: um `[S#]` retornado pelo RAG, ou um arquivo real dentro do projeto.
  - Sem fonte, é `unsupported`. Falha, tempo esgotado e não executada aparecem como tais.
  - Nada altera o estado de uma ocorrência.
- **Gravação:** o resultado vai para `runs/<run>/investigation.json`, com provedor, modelo, `prompt_version`, tentativa e o SHA-256 do relatório investigado. Um relatório adulterado não é investigado. Hipóteses nunca vão para `documentacao_rag`.
- **Falhas:** modelo indisponível ou sem autorização resulta em `skipped`, com o motivo. O relatório básico não muda.

## Dados

`.local/audits/`: `audits.sqlite3` (runs, pedidos, checks, achados, comparação, artefatos), `config.json` (preferências versionadas por `revision`), `runs/<run_id>/report.{json,html}` (conferidos por SHA-256 a cada leitura), `logs/`, `api-token`. O HTML é estático, escapado, sem scripts e com CSP.

## API (token em `.local/audits/api-token`)

| Rota do runner | Ponte da UI (`services/audits-bridge.mjs`) |
| --- | --- |
| `GET /v1/diagnostics/health` | `GET /api/audits/health` |
| `GET` / `PUT /v1/settings` (`{settings, expected_revision}`) | `GET` / `PUT /api/audits/settings` |
| `POST /v1/audits` (`Idempotency-Key` obrigatório; 202 novo, 200 repetido/agregado/desativado) | `POST /api/audits/runs` |
| `GET /v1/audits?cursor&limit&state&severity` | `GET /api/audits/runs` |
| `GET /v1/audits/{id}` · `GET /v1/audits/{id}/report?format=json\|html` | `GET /api/audits/runs/{id}[/report]` |
| `POST /v1/audits/{id}/cancel` · `POST /v1/diagnostics/shutdown` | só cancel |
| `POST /v1/audits/{id}/investigation` (202 nova, 200 já na fila/concluída) | `POST /api/audits/runs/{id}/investigation` |

`POST /v1/audits` aceita `profile` (`startup-light`/`full-audit`) só em pedidos manuais; a abertura usa o perfil das preferências. O detalhe (`GET /v1/audits/{id}`) traz `investigation`, conferida por hash.

O acesso é restrito ao loopback, com `Host` conferido, sem `Origin` de navegador e com `X-Local-Token`. A ponte não expõe o shutdown.

## Comandos

```powershell
$d = '.\.venv-rag\Scripts\python.exe', '-m', 'dicevtt_diagnostics', '--config', '.\.local\diagnostics.toml'
& $d[0] $d[1..4] doctor
& $d[0] $d[1..4] run              # auditoria avulsa (recusa se o serviço estiver ativo)
& $d[0] $d[1..4] request-startup  # o que o CMD chama
& $d[0] $d[1..4] stop
cd services\diagnostics; ..\..\.venv-rag\Scripts\python.exe -m pytest -q
```

Instalação: `.\.venv-rag\Scripts\python.exe -m pip install -e ".\services\diagnostics[dev]"` e copie `config.example.toml` para `.local/diagnostics.toml`.

## Ainda não implementado (entrega 3)

Outbox/sincronização com o gateway Jarvis e os workflows n8n A/B. A UI e o JSON marcam isso (`sync.state = local_only`, `capabilities.sync = false`). Também ficaram de fora PlayMode pelo Test Runner e o build, que o plano deixa para depois de medir o custo. As duas regressões do projeto que entram em Play Mode rodam como validadores.
