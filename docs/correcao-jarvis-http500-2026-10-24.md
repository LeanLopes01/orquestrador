# HTTP 500 ao atualizar Projects — 24/10/2026

Diagnóstico confirmado no servidor `your-server-ip`, release
`20261024T011920Z-personal-runtime`: a lista de conversas e o runtime retornam 200,
mas uma conversa retorna 500. O traceback aponta `Orchestrator.run`, ao ler
`json.loads(t["result"])`: `JSONDecodeError: Unterminated string`.

O backend cortava o JSON **depois** de serializar: 200.000 caracteres em tarefas e
400.000 em jobs. Resultados maiores perdiam o fechamento de strings/objetos.

## Correção

- Persiste o JSON completo, respeitando o limite de transporte já existente no
  WebSocket autenticado (8 MiB).
- Para uma tarefa antiga com JSON incompleto, tenta ler o resultado do job ligado
  por `job_id`, `task_id` e `run_id`. A leitura não altera o banco nem reexecuta tarefas.
- Sem resultado íntegro, devolve `invalid_stored_result`, com `ok: false` e um
  aviso explícito, mantendo a conversa acessível.
- Um job antigo ilegível ainda pendente de processamento segue o tratamento de
  falha, em vez de quebrar o processamento com `JSONDecodeError`.

Código local aplicado em `C:\J.A.R.V.I.S\jarvis\src\jarvis_control\orchestrator.py`.
Backup original em `.local/backups/20261024-orchestrator-json-fix/orchestrator.py`.
O pacote revisável está em `deploy/orchestrator-json-fix/`.

## Validação

42 testes passaram: 8 regressões novas, 15 de orquestração/companion e 19 de
roteamento de planejadores. Incluem resultados acima de 400.000 caracteres, Unicode,
aspas e escapes, recuperação de tarefa antiga, ausência/corrupção do job, vínculo
incorreto, leitura sem mutação e falha explícita no processamento legado.
Ruff format/check passou no backend e nos testes novos.

## Ativação no servidor

Após enviar os quatro arquivos de `deploy/orchestrator-json-fix/` para
`/home/user/jarvis-json-fix-20261024/`, executar:

```powershell
.\scripts\corrigir-jarvis-http500.cmd
```

A senha sudo é digitada no terminal SSH. O instalador confere o hash da versão
original e do hotfix, roda os testes e verifica a leitura do banco real em modo
somente leitura **antes** de instalar. Guarda backup em
`/var/backups/jarvis-json-fix/`, reinicia apenas `jarvis-control`, verifica health e
a leitura das conversas; restaura o arquivo anterior se a ativação falhar.

O banco original não é editado. A ativação não retoma manualmente tarefas que já
ficaram paradas antes da correção. A disponibilidade em produção só deve ser
considerada resolvida após ativar e consultar novamente a conversa pela API.

Hash original: `5ba53730ffafd87e10a04f781eae42d79eb029c8e2d4ea5250e36ff1772c4b71`.
Hash corrigido: `b7db7375616ead60ce6e1ae7fdc3269e6580a058a6afabd102d11dd79261a5b1`.
