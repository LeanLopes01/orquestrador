# rag_ingestion — coleta de fontes para o RAG do DiceVTT

Transforma URLs de documentação e vídeos em Markdown rastreável em `documentacao_rag/`. Sites passam pelo **Trafilatura**; vídeos usam **legendas já existentes** (youtube-transcript-api, PT-BR → PT → EN, manual antes de automática). Sem LLM, sem áudio, sem tradução, sem navegador headless.

Cada arquivo começa com:

```text
Fonte: https://URL-ORIGINAL
Tipo: Artigo | Vídeo
Data de Extração: 2026-10-21T21:32:22-03:00
Source ID: <sha256 da URL canônica>
URL Canônica: …
Aquisição Original: …
(URL Final / Idioma / Legenda quando houver)

---

# Título
```

Salvar não é indexar: depois da coleta, use **Indexar documentos no RAG** (UI) ou `unity_rag index-docs`.

## Uso

O serviço (127.0.0.1:8766) sobe junto com o helper. Na UI: **Ingestão de fontes** → *Coletar online*, *Coletar catálogo (online)*, *Reprocessar cache offline* e *Indexar documentos no RAG*.

CLI (com o serviço desligado):

```powershell
$py = '.\.venv-rag\Scripts\python.exe'
& $py -m rag_ingestion --config .\.local\ingestion.toml doctor
& $py -m rag_ingestion --config .\.local\ingestion.toml run --input .\docs\catalogo-fontes-documentacao-rag.md --mode online
& $py -m rag_ingestion --config .\.local\ingestion.toml run --input .\minha-lista.txt --mode offline
& $py -m rag_ingestion --config .\.local\ingestion.toml resume BATCH_ID
& $py -m rag_ingestion --config .\.local\ingestion.toml prune-cache
```

Entradas: lista `.txt`, manifesto JSON v1 exportado pela UI ou o catálogo `.md` (somente o bloco JSON entre `RAG_SOURCE_CATALOG_START/END`, fontes `enabled=true` por prioridade). Exit code 0 = sem falhas (skips documentados contam como sucesso), 1 = falha em algum item, 2 = erro de entrada/configuração.

## Comportamento

- Modo **offline** nunca acessa a rede; sem cache válido → `skipped / offline_cache_miss`.
- Transporte stdlib com IP fixado após checar DNS (bloqueia loopback, rede privada, link-local), redirects revalidados um a um, limite de 10 MiB, 3 tentativas com orçamento de espera de 60 s; `Retry-After` acima do orçamento vira `retry_budget_exceeded` (sem insistir antes).
- 403/CAPTCHA/login → `access_blocked`; 404 → `not_found`; página só com JavaScript → `content_unavailable`; vídeo sem legenda elegível → `skipped` com motivo.
- Escrita atômica (temporário + `os.replace`), journal `writing → completed` no SQLite, recuperação após queda; uma nova coleta que falha preserva o documento anterior. Reprocessar o mesmo cache com as mesmas opções é no-op (preserva data e hash).
- Manifesto de execução por lote em `.local/ingestion/manifests/<batch>.json` (exportação do estado, não fonte de verdade).

## Primeira coleta real (21/10/2026)

Catálogo: 12 fontes habilitadas → **12 documentos** (6 Unity 6000.3, 5 Steamworks, 1 Red Blob A*). A primeira tentativa pulou as 6 páginas da Unity porque o servidor delas envia `Content-Type: text/html,text/html`; o parser foi corrigido e os documentos foram regenerados a partir do cache em modo offline. As páginas Unity incluem o texto do widget "Suggest a change" (ruído do site, preservado como extraído).

## Testes

```powershell
cd services\ingestion
..\..\.venv-rag\Scripts\python.exe -m pytest -q
```

Fixtures locais (HTML/legendas sintéticos); qualquer conexão externa falha o teste. Os casos de URL em `tests/fixtures/url_cases.json` também são verificados contra o `URL` WHATWG da UI (`tests/url-contract.test.mjs`).
