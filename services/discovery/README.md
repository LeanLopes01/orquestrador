# rag_discovery — descoberta automática de fontes para o RAG do DiceVTT

Faz o RAG crescer sem colar URLs à mão. Cada rodada propõe páginas **novas** de documentação oficial e, no modo `run`, entrega-as à ingestão (`rag_ingestion`, 8766) e pede a indexação ao RAG (`unity_rag`, 8767). Não escreve documentos nem abre o Chroma: usa os mesmos endpoints da UI.

## Estratégias

1. **Código (`code_api`)** — lê os scripts C# (`scripts_root` do `rag.toml`), conta em quantos scripts cada tipo/membro aparece e casa com os índices oficiais (ScriptReference 6000.3, xrefmaps de uGUI/TMP, Input System e Netcode, wiki do Facepunch.Steamworks). O namespace é conferido **por arquivo**: `Button` num script com `using UnityEngine.UI` não puxa `UIElements.Button`. Tipos com o mesmo nome de uma classe do projeto são ignorados. Mais usado no projeto = coletado primeiro.
2. **Tópicos (`topic`)** — o **AirLLM local** (mesmo gerador do `rag.toml`) recebe um resumo do projeto (versão da Unity, pacotes, namespaces, classes mais usadas, títulos já coletados e perguntas recentes ao RAG) e sugere tópicos curtos. Esses tópicos, as perguntas recentes e a lista fixa `[topics].extra` são comparados por embeddings (o encoder do RAG) com os títulos/breadcrumbs do Manual da Unity, dos manuais dos pacotes e dos guias do Facepunch. O modelo nunca inventa URL: no pior caso um tópico não encontra página acima de `min_score`.

Fontes já publicadas pela ingestão, já enviadas ou rejeitadas não voltam a ser propostas.

## Uso

```powershell
# Raiz do Orquestrador. Atalho: pesquisar-fontes.cmd (liga o helper, importa corpus local e coleta da web).
$py = '.\.venv-rag\Scripts\python.exe'
& $py -m rag_discovery doctor                        # configs, modelo, serviços
& $py -m rag_discovery import-local                  # importa SRD 5e XML (1.292 arquivos) + notas locais
& $py -m rag_discovery plan --no-llm                 # mostra até 400 fontes web que seriam coletadas (rápido)
& $py -m rag_discovery run --no-llm                  # coleta em lotes automáticos + indexa no Chroma
& $py -m rag_discovery run --no-llm --max-api 500    # sobrescreve limite de APIs na rodada
& $py -m rag_discovery list --status failed
& $py -m rag_discovery reject https://...            # nunca propor de novo
```

Configuração: `.local/discovery.toml` (modelo em `config.example.toml`). Os limites por rodada (`max_api_per_run`, `max_topic_per_run`) seguram o crescimento: rodadas repetidas avançam do mais usado para o menos usado.

## Custos medidos neste PC (22/10/2026)

- Primeira rodada baixa ~30 MB de índices (cache de 7 dias em `.local/discovery/cache`) e calcula embeddings de ~5 mil títulos (cache por conteúdo).
- AirLLM em CPU: ~1 s/token; `llm.max_new_tokens = 160` → ~3 min por rodada. `--no-llm` pula essa etapa.
- Coleta: 1 s de pausa por domínio entre páginas (política da ingestão).

## Testes

```powershell
cd services\discovery
..\..\.venv-rag\Scripts\python.exe -m pytest -q
```

Índices, scripts e serviços sintéticos; qualquer conexão externa falha o teste.
