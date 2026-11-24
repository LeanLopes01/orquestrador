# Reports do Orquestrador para Jarvis

> Registro do contrato inicial. Para a integração real já publicada, papéis companion e validações de ponta a ponta, consulte [Integração Jarvis e S23 FE](integracao-companion.md).

## Contrato observado

Fonte local: `C:\J.A.R.V.I.S\jarvis\src\jarvis_control\events.py` e `jarvis_desktop/outbox.py`, inspecionados em 19/10/2026. Não foi feita alteração nesses arquivos.

- `event_id`: `[A-Za-z0-9_-]{8,80}`; idempotente por tarefa/estado nesta UI. No executor, incluir ID de execução e sequência para distinguir reexecuções.
- `kind`: `agent_waiting` ou `agent_finished`.
- `status`: `approval`, `question`, `turn_completed`, `completed`, `failed` ou `interrupted`.
- `title`: até 160 caracteres; `summary`: até 600; `report`: até 20.000.
- `agent`: até 30; `host`: 40; `project`, `session_id`, `turn_id`: 120.
- `started_at` e `finished_at`: Unix timestamp ou null; não usar datas inventadas.
- `data`: objeto limitado a 8.000 caracteres no validador atual.

`turn_completed` não prova conclusão da tarefa. Nesta UI, rascunhos e exemplos nunca são enviados como `completed`; `data.executed=false` identifica a ausência de execução real. Tarefas aguardando revisão usam `agent_waiting/approval`. Arquivos exportados não são uma fila de entrega.

## Transporte futuro

1. O serviço persiste o evento e seu `event_id` numa outbox própria em transação com o estado da tarefa.
2. Um adaptador entrega ao helper desktop autenticado ou ao protocolo acordado com Jarvis. Não escrever diretamente no SQLite do Jarvis, nem presumir `POST /v1/reports`.
3. O servidor Jarvis confirma persistência com ACK. Somente então marcar como entregue.
4. Repetições mantêm o mesmo ID; backoff limitado, diagnóstico de erro e reenvio manual visível na UI.
5. Aplicar remoção de segredos antes da outbox; logs brutos, conteúdo pessoal do vault e credenciais não entram automaticamente no report.
6. Uma aprovação vinda do Jarvis precisa identificar usuário, run ID e commit/hash do diff; um texto livre de voz não deve virar merge sem esse vínculo.

## Responsabilidade de execução

Jarvis já tem seu próprio orquestrador e runners. Escolher a fronteira explicitamente. Proposta: este serviço possui as execuções Unity; Jarvis recebe reports e consulta estado. Caso Jarvis seja escolhido como executor, trocar os adaptadores por um cliente de seu serviço em vez de disparar o mesmo job em ambos.

## Teste de integração para a fase seguinte

Publicar um evento de sandbox, derrubar a conexão antes do ACK, reconectar e confirmar exatamente um registro visível no Jarvis. Verificar redaction, limite de tamanho, autenticação inválida, report antigo e retomada após reinício. O teste não deve executar Git ou Unity.
