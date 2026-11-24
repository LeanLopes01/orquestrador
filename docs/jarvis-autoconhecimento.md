# Como o Jarvis consulta suas próprias capacidades

## Estado da instalação em 28/10/2026

Código instalado na cópia local `C:\J.A.R.V.I.S\jarvis`, com backup em
`backups\self-knowledge-20261028-160942`. O helper foi reiniciado sem trabalhos
ativos e reconectou às 16:15:37 anunciando `system.inspect`.
A instalação do servidor ainda depende de sudo:
execute `D:\Programação\ProjetoLocais\Orquestrador\atualizar-autoconhecimento-jarvis.cmd`
e digite a senha diretamente no terminal. O pacote foi enviado, extraído e seu
SHA-256 conferido em `/home/user/jarvis-self-knowledge-20261028`.
O instalador verifica a base, executa testes, faz backup e recusa instalação
durante chamada de voz. Não reinicia gateway nem n8n.

Validação local: 17 testes aprovados, verificação Ruff aprovada e uma conversa
real no debugger LiveKit confirmou a chamada de `inspect_jarvis_system`.
Esse debugger local não tinha canal DesktopLink configurado; portanto ainda
falta validar uma nova conversa no servidor com o helper conectado.

## Regra de consulta

Quando a pergunta for sobre o próprio sistema (capacidades, acessos, RAG, MCPs,
integrações, implementação ou indisponibilidade), o agente deve chamar
`inspect_jarvis_system` antes de responder. Perguntas gerais continuam usando as
ferramentas apropriadas ao assunto.

A consulta devolve data/hora, ferramentas registradas na conversa, estado atual
do canal servidor–PC e sondagens somente leitura. Um serviço ausente ou inacessível
não deve ser apresentado como uma funcionalidade inexistente.

## Onde procurar

| Assunto | Caminho e função |
| --- | --- |
| Código ativo no servidor | `/opt/jarvis/current/src`; a ferramenta também informa a release resolvida de seu próprio processo |
| Instruções e ferramentas da voz | `/opt/jarvis/current/src/agent.py` |
| Autoconhecimento | `/opt/jarvis/current/src/system_knowledge.py` |
| API autenticada do servidor | `/opt/jarvis/current/src/jarvis_control/web.py` |
| Planejamento e execução de projetos | `/opt/jarvis/current/src/jarvis_control/orchestrator.py` |
| Transporte para o PC | `/opt/jarvis/current/src/desktop_link.py` |
| Consulta ao RAG por voz | `/opt/jarvis/current/src/project_knowledge.py` |
| Integrações pessoais | `/opt/jarvis/current/src/personal_data.py` e `src/jarvis_control/personal.py` |
| Cópia de desenvolvimento do Jarvis | `C:\J.A.R.V.I.S\jarvis\src` |
| Ações oferecidas pelo PC | `C:\J.A.R.V.I.S\jarvis\src\jarvis_desktop\actions.py` |
| Inventário local seguro | `C:\J.A.R.V.I.S\jarvis\src\jarvis_desktop\system_inspection.py` |
| Supervisão dos serviços | `C:\J.A.R.V.I.S\jarvis\src\jarvis_desktop\rag_service.py` |
| Orquestrador | `D:\Programação\ProjetoLocais\Orquestrador` |
| Navegação e interface | `src/App.tsx`, `src/ReportsPanel.tsx`, `src/RagPanel.tsx` relativos ao Orquestrador |
| Pontes locais | `services/*-bridge.mjs` e `vite.config.mjs` |
| RAG, índice e recuperação | `services/rag/README.md`, `services/rag/src/unity_rag/` |
| Ingestão existente | `services/ingestion/README.md` |
| MCP para agentes de código | `services/agent-rag/rag_mcp.py`, `services/agent-rag/README.md` |
| Consulta inicial dos agentes | `services/agent-rag/rag_hook.py` |
| Auditorias e investigação | `services/diagnostics/README.md` |
| Configuração MCP do Codex | `%USERPROFILE%\.codex\config.toml`, seção `mcp_servers` |
| Configuração MCP do Claude Code | `%USERPROFILE%\.claude.json`, seção `mcpServers` |
| Publicação do backend | `C:\J.A.R.V.I.S\jarvis\deploy\deploy.sh` e `deploy/jarvis-deploy` |

Os caminhos são referências técnicas. Receber este mapa não significa que o
Jarvis leu todos esses arquivos. A ferramenta não dá acesso a shell ou leitura
arbitrária de arquivos.

## Como interpretar as sondagens

- `DesktopLink.status`: consulta o gateway no servidor e as ações anunciadas pelo helper.
- `rag.health`: pergunta ao helper pelo RAG e pela ingestão.
- `orchestrator.runtime`: verifica a interface do Orquestrador e os agentes suportados.
- `system.inspect`: lê apenas registros MCP de usuário e o health das auditorias.
- `session_tools`: ferramentas efetivamente expostas ao agente de voz nesta conversa.

Registrar MCP no Claude Code ou no Codex não registra o mesmo MCP no Jarvis.
O Jarvis acessa o RAG pelo canal autenticado `rag.retrieve`. O inventário de MCP
informa configuração, não autenticação ou sucesso de handshake. Configurações
de projeto e plugins não estão cobertas pelo inventário de usuário.

Tokens, variáveis de ambiente dos MCPs, argumentos de comandos e configurações
completas não são retornados. Diagnóstico não reinicia serviços nem reindexa fontes.

## Pasta de documentos

Implementada em 28/10/2026 para PDFs com texto e formatos textuais, com caminho
visível, abertura da pasta e indexação manual pela tela RAG local. Atualizações
e exclusões são reconciliadas por hash. Planilhas precisam ser exportadas como
CSV; PDFs digitalizados precisam de OCR prévio. Consulte
[pasta-documentos-e-etapas.md](pasta-documentos-e-etapas.md) para formatos,
limites e instruções completas.
