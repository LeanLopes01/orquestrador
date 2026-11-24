# agent-rag — RAG do DiceVTT para Claude Code, Codex e Antigravity

Liga os agentes de código ao [unity_rag](../rag/README.md) (127.0.0.1:8767). Substitui o papel do antigo hook `.brain` (LightRAG do vault) para o projeto DiceVTT. Só biblioteca padrão do Python.

| Arquivo | Papel |
| --- | --- |
| `rag_hook.py` | Hook `UserPromptSubmit` / `PreInvocation`: na **primeira mensagem de cada sessão**, busca fontes para o prompt e injeta até ~8 mil caracteres (resumo dos `.cs`, trechos de docs, caminhos). Só nas pastas `C:\ProjetoTablepRPG` e deste Orquestrador. |
| `rag_mcp.py` | Servidor MCP `dicevtt-rag` (stdio): o agente consulta o RAG quando achar necessário. |
| `rag_client.py` | Cliente HTTP comum (token de `.local/rag/api-token`). |

Ferramentas MCP:

- `rag_buscar {consulta, tipo: tudo|codigo|docs, max_caracteres_por_fonte}`: scripts C# lidos do disco na hora e trechos de documentação. Leva de 1 a 2 s.
- `rag_status`: health do serviço (índice, watcher, modelo).
- `rag_reindexar {escopo: code|documents|all}`: espera até 90 s pelo job.

A geração pelo AirLLM (`/v1/rag/asks`) fica de fora: leva minutos no CPU e o agente responde melhor a partir das fontes.

## Onde está registrado

Todos os registros usam o Python do Jarvis (`C:/J.A.R.V.I.S/jarvis/.venv/Scripts/python.exe`).

- **Claude Code**: o MCP foi registrado com `claude mcp add --scope user dicevtt-rag …` e fica em `~/.claude.json`. O hook está em `~/.claude/settings.json`, em `UserPromptSubmit`.
- **Codex** (CLI e extensão do VS Code): o MCP fica em `[mcp_servers.dicevtt-rag]` do `~/.codex/config.toml`. O hook está em `~/.codex/hooks.json`. O Codex **só roda hooks revisados**: aprove o novo em `/hooks` (TUI ou painel do Codex) uma vez.
- **Antigravity** (CLI, IDE e Antigravity 2.0): o MCP foi registrado com `agy mcp add dicevtt-rag …` e fica em `~/.gemini/config/mcp_config.json`. Os hooks (`dicevtt-rag-hook` em `PreInvocation` e `jarvis-agent-hook` em `PreInvocation`/`Stop`) ficam em `~/.gemini/config/hooks.json`.

Backups do estado anterior: `*.agent-rag-backup-20261025` ao lado de cada arquivo.

## Ajustes

- Outras pastas para o hook: `DICEVTT_RAG_HOOK_DIRS="C:\pasta1;D:\pasta2"`.
- Estado de "primeira mensagem": `%LOCALAPPDATA%\DiceVTT-RAG\agent-hook\<agente>-<sessão>`. Os marcadores são apagados após 14 dias.
- Com o RAG desligado, o hook injeta só um aviso e as ferramentas devolvem erro com a instrução para ligar (`iniciar-tudo.cmd`).

## Testar sem agente

```powershell
'{"session_id":"t1","prompt":"Como o SteamLobbyManager cria o lobby?","cwd":"C:\\ProjetoTablepRPG\\DiceVTT"}' | python services\agent-rag\rag_hook.py claude
claude mcp get dicevtt-rag
codex mcp list
agy mcp list
```

Para uso não interativo (`agy -p` em `--mode plan` ou `--mode accept-edits`), `~/.gemini/antigravity-cli/settings.json` também precisa da permissão `"mcp(dicevtt-rag/*)"` em `permissions.allow` (instalada automaticamente por `jarvis_desktop.agy_setup.install()`).
