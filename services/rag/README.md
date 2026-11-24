# unity_rag — RAG local do DiceVTT

Serviço Python que responde perguntas sobre o DiceVTT com duas fontes:

- **Scripts C# (Pointer RAG):** o Chroma guarda só o resumo de cada `.cs` (nome do arquivo, classe principal, comentário de cabeçalho e `///` da classe) e o caminho. A cada consulta o arquivo é **lido de novo do disco**, então mudanças no corpo aparecem antes mesmo de o watcher atualizar o resumo.
- **Documentação:** os `.md`/`.txt` de `documentacao_rag/` (produzidos pela ingestão ou escritos à mão), divididos em trechos com a proveniência `Fonte`/`Tipo`/`Data de Extração` em cada trecho.

A resposta em linguagem natural vem do **AirLLM** (checkout local `airllm-main/air_llm`), com fontes `S1`, `S2`… e avisos.

Planos de origem: [plano RAG](../../docs/plano-rag-dinamico-airllm-claude.md) e [plano de ingestão](../../docs/plano-ingestao-documentacao-rag.md).

## Como roda no dia a dia

O serviço sobe **junto com o helper Jarvis Desktop** (`iniciar-tudo.cmd` na raiz do Orquestrador, ou o início automático do helper no login). Desligar o helper desliga o RAG; desligar o RAG (`unity_rag stop`, botão **Desligar** na UI) desliga o helper. O helper roda os serviços num *job object* do Windows: se ele for encerrado à força, o RAG e a ingestão morrem junto.

| Onde | Como usar |
| --- | --- |
| PC | `http://127.0.0.1:1420/#rag` (e a área RAG na Janela de contexto) |
| Celulares | Jarvis → **Knowledge** (retrato) ou **More → Knowledge** (paisagem) |
| Voz | "Jarvis, como o SteamLobbyManager cria o lobby?" → ferramenta `search_project_knowledge` |

## Instalação (já feita neste PC)

```powershell
# Na raiz do Orquestrador
py -3.12 -m venv .venv-rag
.\.venv-rag\Scripts\python.exe -m pip install --upgrade pip
.\.venv-rag\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv-rag\Scripts\python.exe -m pip install -e .\airllm-main\air_llm
.\.venv-rag\Scripts\python.exe -m pip install -e ".\services\rag[dev]" -e ".\services\ingestion[dev]"
.\.venv-rag\Scripts\python.exe -m pip check
Copy-Item .\services\rag\config.example.toml .\.local\rag.toml        # não sobrescreva um já configurado
.\.venv-rag\Scripts\python.exe -m unity_rag --config .\.local\rag.toml prepare-models   # único passo com internet
.\.venv-rag\Scripts\python.exe -m unity_rag --config .\.local\rag.toml doctor
```

Lock reproduzível: [`services/requirements-rag.lock.txt`](../requirements-rag.lock.txt) (resolução conjunta com a ingestão). Python 3.11 não estava instalado; foi usado **3.12.10**.

## Comandos

```powershell
$rag = '.\.venv-rag\Scripts\python.exe', '-m', 'unity_rag', '--config', '.\.local\rag.toml'
& $rag[0] $rag[1..4] doctor
& $rag[0] $rag[1..4] index-code
& $rag[0] $rag[1..4] index-docs
& $rag[0] $rag[1..4] retrieve "Como o lobby Steam é criado?"
& $rag[0] $rag[1..4] ask "Como o SteamLobbyManager.cs cria um lobby?"
& $rag[0] $rag[1..4] chat --watch      # terminal interativo (não use junto com o serviço)
& $rag[0] $rag[1..4] serve             # o helper já faz isso
& $rag[0] $rag[1..4] stop              # desliga o RAG e, com ele, o helper
```

Os comandos standalone recusam rodar quando o serviço está ativo (lock do sistema operacional); com o serviço ligado, use a UI ou a API.

## API local (127.0.0.1:8767, token em `.local/rag/api-token`)

| Rota | Função |
| --- | --- |
| `GET /v1/rag/health` | embeddings, índice, watcher e modelo (`not_configured/unloaded/loading/ready/error`) — não carrega o modelo |
| `POST /v1/rag/retrieve` | `{project_id, query, text_limit?}` → fontes atuais, sem geração |
| `POST /v1/rag/index-jobs` / `GET …/{id}` | `{scope: code\|documents\|all}` → 202 + `job_id`, depois relatório |
| `POST /v1/rag/asks` / `GET …/{id}` / `POST …/{id}/cancel` | geração assíncrona com progresso; `request_id` evita duplicar |
| `POST /v1/rag/shutdown` | encerramento limpo (o helper desliga junto) |

Só loopback, `Host` conferido, sem `Origin` de navegador e com `X-Local-Token`. A UI fala com `/api/rag/*` (ponte Vite em `services/rag-bridge.mjs`, que injeta o token); os celulares falam com o servidor Jarvis (`/v1/rag/*`), que repassa ao helper pela conexão que já existe.

## Configuração deste PC (`.local/rag.toml`)

- Embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (as perguntas são em PT-BR; o exemplo mantém o `all-MiniLM-L6-v2` do plano). Trocar de modelo cria outra coleção e exige reindexar.
- Gerador: `Qwen2.5-1.5B-Instruct` em CPU, bf16, janela de 4096 tokens, até 384 tokens de resposta.
- Chroma em `%LOCALAPPDATA%\DiceVTT-RAG\chroma` — ver limitações.

## Limitações medidas (não contornadas em silêncio)

- **Chroma + caminho com acento no Windows:** o Chroma 1.5.9 grava, mas não reabre o índice HNSW em `D:\Programação\…` (`Error loading hnsw index`); reproduzido com um teste isolado (ASCII funciona, acentuado falha). Por isso `chroma_path` precisa ser ASCII; a configuração recusa outro valor com mensagem clara.
- **AirLLM em CPU:** a GPU AMD RX 6600 não tem CUDA, então o AirLLM roda no Ryzen 5 5600X. Medido: 5,7 s/token originalmente; o `_post_hook` do AirLLM faz `gc.collect()` a cada camada a cada token. Desligando só isso no processo do RAG (sem editar a biblioteca) caiu para **~1,0 s/token com saída idêntica**. Respostas reais medidas: 384 tokens com prompt de 1662 tokens em 416 s; com prompt de 3706 tokens (janela 4096, 4 fontes) em 654 s, com a CPU dividida com uma build Android. A busca de fontes leva menos de 1 s. O Qwen 1.5B às vezes cita nomes de callbacks que não estão no trecho enviado: confira as fontes `S1…` antes de confiar.
- O Qwen2.5-0.5B foi medido (4,9 s/token antes do ajuste) e descartado: quase o mesmo custo por token, com qualidade pior.
- O watcher garante atualização *eventual* da seleção; a leitura direta garante frescor só dos arquivos selecionados. Não há snapshot atômico entre vários arquivos.
- Distância vetorial não é confiança. Os resumos dependem dos comentários existentes nos scripts.

## Testes

```powershell
cd services\rag
..\..\.venv-rag\Scripts\python.exe -m pytest -q                     # rápidos: embeddings determinísticos, Chroma temporário, gerador falso
$env:RAG_REAL_CONFIG = "$PWD\..\..\.local\rag.toml"
..\..\.venv-rag\Scripts\python.exe -m pytest tests/test_integration_real.py -q   # embeddings reais
$env:RAG_AIRLLM_SMOKE = '1'                                          # + AirLLM real (~20 s)
```

Os testes rápidos falham se qualquer conexão externa for aberta.
