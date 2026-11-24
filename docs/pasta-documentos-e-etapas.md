# Pasta de documentos e três etapas dos projetos

Entrega de 28/10/2026.

## Onde colocar os PDFs

Abra **RAG local** no menu lateral (`/#rag`). A seção **Indexar uma pasta de PDFs e documentos** mostra o caminho configurado pelo serviço:

`D:\Programação\ProjetoLocais\Orquestrador\documentacao_rag`

1. Clique em **Abrir pasta no Windows**.
2. Copie os documentos e subpastas para lá.
3. Clique em **Indexar pasta agora** e aguarde o resultado.
4. Consulte o conteúdo em **Buscar fontes**.

Formatos: PDF com texto, Markdown, TXT, CSV, TSV, JSON, YAML, XML e LOG. Limite de 32 MB por arquivo; PDF limitado a 1.000 páginas e 4 milhões de caracteres extraídos. Planilhas Excel devem ser exportadas como CSV nesta versão. PDFs protegidos ou com páginas sem texto extraível são recusados com motivo explícito; aplique OCR antes. A extração não executa conteúdo dos documentos.

A indexação é manual e recursiva. Repita o botão após adicionar, alterar ou excluir arquivos. Hashes permitem reaproveitar os inalterados e substituir trechos antigos. Formatos não suportados são ignorados; pastas ocultas, cache, logs, manifests e links de diretórios não são percorridos. PDF cita página e caminho original. Não há upload para um serviço novo: usa o índice local existente.

Validação real: indexado um PDF temporário e recuperado na busca com `Página 1`; depois removido do disco e do índice. Os 1.526 documentos existentes permaneceram inalterados, sem erros na indexação.

## Projetos: planejamento → UI → código

Em **Projects · Jarvis**, cada etapa tem agente, modelo e esforço:

- Planejamento: Antigravity por padrão, Gemini selecionável; Codex também disponível.
- UI: Codex por padrão; Claude e Antigravity como alternativas. Pode ser desativada. Quando habilitada, o planejador só cria tarefas de UI se forem necessárias.
- Implementação: Claude por padrão; Codex e Antigravity como alternativas.

Modelo vazio usa o padrão do CLI. As sugestões de Gemini foram obtidas com `agy models`; as do Codex, do catálogo local. Aliases Claude seguem seu CLI. Identificadores personalizados são aceitos, mas disponibilidade e suporte ao esforço só são confirmados pelo provedor na execução. Modelo indisponível falha explicitamente, sem fallback silencioso.

As escolhas são persistidas no navegador e enviadas no objeto `pipeline`. O servidor valida, salva as configurações no corpo/hash do plano e copia modelo/esforço para cada job. Tarefas de código dependem das tarefas de UI; todas usam a mesma cópia isolada da execução. Aprovar o plano continua obrigatório; aplicar ao projeto original é separado. Contratos antigos seguem suportados no backend, mas a nova UI exige confirmação de suporte às três etapas para evitar descartar escolhas.

Para Codex, o esforço é enviado como `-c model_reasoning_effort=...`, conforme a [referência oficial](https://learn.chatgpt.com/docs/config-file/config-reference). Claude e Antigravity recebem `--model` e `--effort`. Gemini no Antigravity usa também o sufixo de esforço no identificador do modelo.

## Ativação pendente no servidor

UI e helper local atualizados. O servidor ainda precisa da instalação com sudo:

`D:\Programação\ProjetoLocais\Orquestrador\atualizar-projetos-jarvis.cmd`

O pacote está em `/home/user/jarvis-project-pipeline-20261028`. O instalador confere hashes, recusa trabalhos ativos, guarda backup em `/var/backups/jarvis-project-pipeline`, reinicia o gateway e restaura arquivos se o health falhar. Nenhuma migration de banco é necessária. A senha é digitada no terminal, nunca no chat. Esse pacote é independente da atualização anterior de autoconhecimento da voz.

Fontes: `src/ProjectPipeline.tsx`, `src/ProjectsPanel.tsx`, `src/RagPanel.tsx`, `services/rag/src/unity_rag/document_extract.py`, `services/rag/src/unity_rag/document_indexer.py`, `deploy/project-pipeline/`. Cópia local do backend: `C:\J.A.R.V.I.S\jarvis\src\project_pipeline.py`, `jarvis_control/orchestrator.py`, `jarvis_control/web.py`; executor: `jarvis_desktop/agent_jobs.py`.
