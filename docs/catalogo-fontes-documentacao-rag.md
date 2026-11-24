# Catálogo de fontes para alimentar o RAG do DiceVTT

Preparado em: 21/10/2026. Projeto: `dicevtt`. Formato do catálogo: `rag-source-catalog/v1`.

Este arquivo reúne documentação, artigos e vídeos para a futura ingestão Python. É uma lista de entrada, não o conteúdo já extraído: nenhuma destas fontes foi coletada pelo pipeline, convertida em documento ou indexada no Chroma nesta entrega.

Manter este catálogo em `docs/`, fora de `documentacao_rag/`. O programa deve ler as URLs deste arquivo, coletar as fontes habilitadas e salvar **o conteúdo de cada fonte** como `.md` em `documentacao_rag/`. O indexador estático recebe esses arquivos finais. Indexar somente este catálogo não dá ao RAG acesso ao conteúdo dos links.

## 1. Como usar este catálogo

Há 19 fontes cadastradas: 12 habilitadas para o lote inicial e 7 opcionais desabilitadas. A seleção inicial é uma proposta de curadoria, não uma afirmação de que todas essas APIs já são utilizadas pelo projeto.

1. Conferir a versão Unity, o wrapper Steam e as bibliotecas efetivamente usadas em `Packages/manifest.json`, `Packages/packages-lock.json` e nos scripts do projeto.
2. Ajustar `enabled` no bloco JSON da seção 6. Não habilitar automaticamente todos os sistemas de RPG ou frameworks de rede.
3. O futuro Python lê somente esse bloco estruturado, valida as URLs e monta um lote compatível com o pipeline.
4. Coletar artigos com Trafilatura e legendas de vídeos com youtube-transcript-api.
5. Salvar cada documento com Fonte, Tipo e Data de Extração reais.
6. Indexar os documentos concluídos no Módulo 2; registrar falhas e fontes ignoradas separadamente.

A aquisição remota exige internet. Extração de cache, indexação e consulta podem funcionar offline depois da preparação das dependências e modelos. Os links foram pesquisados nesta data; disponibilidade futura e qualidade da extração devem ser verificadas durante cada coleta.

## 2. Documentação principal: Unity e Steam

Os títulos abaixo são rótulos de catálogo. As páginas Unity foram consultadas na documentação 6000.3, versão registrada no planejamento do projeto. As páginas web listadas foram abertas ou localizadas em documentação oficial; isso não constitui um teste do extrator Trafilatura.

| ID | Fonte | Uso proposto no VTT | Lote inicial |
| --- | --- | --- | --- |
| U01 | [Unity 6000.3 — Grid](https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Grid.html) | Estrutura de células e representação do tabuleiro | Sim |
| U02 | [Unity 6000.3 — WorldToCell](https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GridLayout.WorldToCell.html) | Converter posição do mundo em célula | Sim |
| U03 | [Unity 6000.3 — GetCellCenterWorld](https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Grid.GetCellCenterWorld.html) | Posicionar tokens no centro das células | Sim |
| U04 | [Unity 6000.3 — ScriptableObject](https://docs.unity3d.com/6000.3/Documentation/Manual/class-ScriptableObject.html) | Consultar modelos de dados e assets de configuração | Sim |
| U05 | [Unity 6000.3 — Serialization rules](https://docs.unity3d.com/6000.3/Documentation/Manual/script-serialization-rules.html) | Entender limites de serialização de dados Unity | Sim |
| U06 | [Unity 6000.3 — JsonUtility](https://docs.unity3d.com/6000.3/Documentation/ScriptReference/JsonUtility.html) | Avaliar persistência JSON de mapas e campanhas | Sim |
| S01 | [Steam — Networking](https://partner.steamgames.com/doc/features/multiplayer/networking?l=english) | Comparar as interfaces de rede antes de definir o transporte | Sim |
| S02 | [Steam — Matchmaking & Lobbies](https://partner.steamgames.com/doc/features/multiplayer/matchmaking) | Sessões, descoberta e organização de lobbies | Sim |
| S03 | [Steam — ISteamMatchmaking](https://partner.steamgames.com/doc/api/ISteamMatchmaking) | Consultar operações e callbacks de lobby | Sim |
| S04 | [Steam — ISteamNetworkingSockets](https://partner.steamgames.com/doc/api/ISteamNetworkingSockets?l=english&language=english) | Consultar conexões e mensagens do transporte | Sim |
| S05 | [Steam — ISteamNetworkingMessages](https://partner.steamgames.com/doc/api/ISteamNetworkingMessages) | Comparar o modelo de mensagens entre peers | Sim |
| S06 | [Steamworks.NET — Installation](https://steamworks.github.io/installation/) | Instalação do wrapper, se adotado pelo projeto | Não: confirmar wrapper |
| S07 | [Steamworks.NET — Getting Started](https://steamworks.github.io/gettingstarted/) | Inicialização e callbacks, se adotado pelo projeto | Não: confirmar wrapper |

As referências Steam S01–S05 descrevem o SDK/API nativa; não são exemplos C# automaticamente compatíveis com qualquer wrapper. O código deve usar o wrapper e a versão realmente instalados. A documentação Steam distingue interfaces atuais e a antiga `ISteamNetworking`; tutoriais antigos devem ser confrontados com a [visão oficial de networking](https://partner.steamgames.com/doc/features/multiplayer/networking?l=english).

Nenhuma escolha de Mirror, FishNet, Netcode for GameObjects ou Facepunch foi presumida. Depois de confirmar a stack, acrescentar páginas específicas e versionadas do framework adotado. Não inserir todos como se descrevessem a arquitetura real do DiceVTT.

## 3. Algoritmos de grid e movimentação

| ID | Fonte | Uso proposto | Lote inicial |
| --- | --- | --- | --- |
| G01 | [Red Blob Games — Introduction to A*](https://www.redblobgames.com/pathfinding/a-star/introduction.html) | Referência de busca de caminhos e custos de movimento | Sim |
| G02 | [Red Blob Games — Hexagonal Grids](https://www.redblobgames.com/grids/hexagons/) | Coordenadas, vizinhança e distâncias em hexágonos | Não: habilitar se houver grid hexagonal |

Esses artigos são fontes do próprio autor dos guias. Suas demonstrações interativas não serão preservadas integralmente por extração textual. Avaliar se fórmulas, tabelas e exemplos necessários sobreviveram à conversão. Algoritmos gerais não definem a regra de jogo: custo de diagonal, obstáculos, alcance e elevação devem vir de documentação aprovada do DiceVTT ou do sistema de RPG selecionado.

## 4. Vídeos: referências opcionais

| ID | Fonte | Origem e época | Observação para ingestão |
| --- | --- | --- | --- |
| V01 | [Tilemap isométrico — Unity](https://www.youtube.com/watch?v=tywt9tOubEY) | Canal Unity; publicação encontrada de 2019 | Referência conceitual antiga; validar aplicabilidade ao Unity 6000.3 |
| V02 | [Creating a 2D Game Using Tile Maps: Tile Map Basics](https://www.youtube.com/watch?v=dtpthaIYa8g) | Canal Unity Korea; publicação encontrada de 2018 | Idioma/legendas precisam ser verificados; validar aplicabilidade à versão atual |

Os dois links foram identificados pelos resultados de busca; a abertura direta não retornou o conteúdo dos vídeos nesta verificação. **As legendas não foram consultadas nem confirmadas.** Por isso, ambos começam desabilitados. Para incluir, alterar `enabled` para `true` após decidir usar a referência histórica; a aquisição ainda precisa verificar legendas.

Prioridade de legenda: PT-BR → PT → EN; preferir manual e depois automática dentro de cada idioma. Se não houver legenda elegível, pular com aviso. Não traduzir, baixar áudio ou usar Whisper. Não cadastrar canal/playlist como se fosse vídeo individual.

Não foi incluído um tutorial de Steam de terceiro sem validar sua relação com a stack. Ao adicionar um, registrar o wrapper, a versão e se ele utiliza API legada. Um vídeo não deve se sobrepor à documentação oficial da versão instalada.

## 5. Regras de RPG e documentação própria

O sistema de regras do DiceVTT ainda não foi definido nestes pedidos. As referências abaixo são opções para escolha posterior; não são regras automaticamente adotadas pelo produto.

| ID | Fonte | Papel | Lote inicial |
| --- | --- | --- | --- |
| R01 | [Fate Core — Taking Action, Dice & The Ladder](https://fate-srd.com/fate-core/taking-action-dice-ladder) | Exemplo de página específica de regras em HTML | Não: somente se o projeto adotar Fate Core |
| R02 | [D&D — portal oficial do SRD](https://www.dndbeyond.com/srd) | Localizar a edição e o material desejados | Não: portal de descoberta, não corpus completo |

O portal de SRD não equivale à ingestão do livro. O pipeline atual não processa PDF nem segue todos os links automaticamente; selecionar páginas HTML ou preparar arquivos `.md`/`.txt` adequados separadamente. Manter sistema e edição explícitos para não misturar regras incompatíveis. Preservar os avisos de autoria e licença presentes nos materiais selecionados.

Além das fontes externas, preparar os seguintes documentos próprios. São nomes sugeridos e assuntos pendentes, não arquivos já existentes nem decisões tomadas:

| Documento futuro | Informações a registrar antes de indexar |
| --- | --- |
| `regras-grid.md` | Tipo de grid, tamanho de célula, diagonais, coordenadas negativas, elevação e obstáculos |
| `regras-tokens.md` | Tamanho/ocupação, posse, permissões e movimento de tokens |
| `regras-visibilidade.md` | Linha de visão, paredes, iluminação e informação visível por jogador |
| `regras-dados.md` | Expressões aceitas, modificadores, registro de resultados e autoridade da rolagem |
| `arquitetura-p2p.md` | Host, peers, autoridade, mensagens, reconexão e política de saída do host |
| `persistencia-campanhas.md` | Esquema, versões, migração, exportação e restauração de campanhas |
| `decisoes-tecnicas.md` | Bibliotecas/versões escolhidas e razões das decisões |

Somente decisões preenchidas e aprovadas devem ir para a pasta documental. Templates vazios e este catálogo permanecem em `docs/`. Os scripts `.cs` continuam no Pointer RAG, lidos ao vivo; não copiar seu conteúdo para este catálogo como documentação estática.

## 6. Bloco estruturado para o futuro Python

Este é o único bloco de dados autoritativo do catálogo. Os IDs U01/S01 etc. são IDs de curadoria, não o `source_id` SHA-256 do pipeline. `enabled` determina elegibilidade para aquisição; não indica extração bem-sucedida. `priority=1` vem antes de 2 e 3. `notes` são orientações de curadoria, não conteúdo a ser vetorizado.

<!-- RAG_SOURCE_CATALOG_START -->
```json
{
  "catalog_schema": "rag-source-catalog/v1",
  "project_id": "dicevtt",
  "prepared_on": "2026-10-21",
  "output_directory": "documentacao_rag",
  "languages": ["pt-BR", "pt", "en"],
  "sources": [
    {"id":"U01","title":"Unity Grid","kind":"article","url":"https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Grid.html","topic":"unity-grid","version":"6000.3","priority":1,"enabled":true,"notes":"Referência de grid; confirmar uso da classe no projeto."},
    {"id":"U02","title":"Unity WorldToCell","kind":"article","url":"https://docs.unity3d.com/6000.3/Documentation/ScriptReference/GridLayout.WorldToCell.html","topic":"unity-grid","version":"6000.3","priority":1,"enabled":true,"notes":"Conversão de posição do mundo em coordenada de célula."},
    {"id":"U03","title":"Unity GetCellCenterWorld","kind":"article","url":"https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Grid.GetCellCenterWorld.html","topic":"unity-grid","version":"6000.3","priority":1,"enabled":true,"notes":"Referência para posicionar tokens no centro da célula."},
    {"id":"U04","title":"Unity ScriptableObject","kind":"article","url":"https://docs.unity3d.com/6000.3/Documentation/Manual/class-ScriptableObject.html","topic":"unity-dados","version":"6000.3","priority":1,"enabled":true,"notes":"Consultar antes de definir assets de configuração."},
    {"id":"U05","title":"Unity Serialization rules","kind":"article","url":"https://docs.unity3d.com/6000.3/Documentation/Manual/script-serialization-rules.html","topic":"unity-persistencia","version":"6000.3","priority":1,"enabled":true,"notes":"Limites de serialização da Unity."},
    {"id":"U06","title":"Unity JsonUtility","kind":"article","url":"https://docs.unity3d.com/6000.3/Documentation/ScriptReference/JsonUtility.html","topic":"unity-persistencia","version":"6000.3","priority":1,"enabled":true,"notes":"Não presume que JsonUtility seja o serializador adotado."},
    {"id":"S01","title":"Steam Networking","kind":"article","url":"https://partner.steamgames.com/doc/features/multiplayer/networking?l=english","topic":"steam-rede","version":"consultar-sdk-instalado","priority":1,"enabled":true,"notes":"Visão geral de interfaces atuais e legadas."},
    {"id":"S02","title":"Steam Matchmaking and Lobbies","kind":"article","url":"https://partner.steamgames.com/doc/features/multiplayer/matchmaking","topic":"steam-lobby","version":"consultar-sdk-instalado","priority":1,"enabled":true,"notes":"Conceitos de matchmaking e lobbies."},
    {"id":"S03","title":"ISteamMatchmaking","kind":"article","url":"https://partner.steamgames.com/doc/api/ISteamMatchmaking","topic":"steam-lobby","version":"consultar-sdk-instalado","priority":1,"enabled":true,"notes":"API nativa; adaptar ao wrapper C# realmente usado."},
    {"id":"S04","title":"ISteamNetworkingSockets","kind":"article","url":"https://partner.steamgames.com/doc/api/ISteamNetworkingSockets?l=english&language=english","topic":"steam-p2p","version":"consultar-sdk-instalado","priority":1,"enabled":true,"notes":"API nativa; não misturar automaticamente wrappers."},
    {"id":"S05","title":"ISteamNetworkingMessages","kind":"article","url":"https://partner.steamgames.com/doc/api/ISteamNetworkingMessages","topic":"steam-p2p","version":"consultar-sdk-instalado","priority":1,"enabled":true,"notes":"Comparar com Sockets; não exige implementar ambos."},
    {"id":"S06","title":"Steamworks.NET Installation","kind":"article","url":"https://steamworks.github.io/installation/","topic":"steamworks-net","version":"confirmar-wrapper","priority":2,"enabled":false,"notes":"Habilitar somente se Steamworks.NET for o wrapper adotado."},
    {"id":"S07","title":"Steamworks.NET Getting Started","kind":"article","url":"https://steamworks.github.io/gettingstarted/","topic":"steamworks-net","version":"confirmar-wrapper","priority":2,"enabled":false,"notes":"Habilitar junto da confirmação de wrapper e versão."},
    {"id":"G01","title":"Introduction to A Star","kind":"article","url":"https://www.redblobgames.com/pathfinding/a-star/introduction.html","topic":"grid-pathfinding","version":"conceitual","priority":2,"enabled":true,"notes":"Texto não preserva toda a demonstração interativa."},
    {"id":"G02","title":"Hexagonal Grids","kind":"article","url":"https://www.redblobgames.com/grids/hexagons/","topic":"grid-hexagonal","version":"conceitual","priority":2,"enabled":false,"notes":"Habilitar se o produto suportar grid hexagonal."},
    {"id":"V01","title":"Tilemap isométrico - Unity","kind":"video","url":"https://www.youtube.com/watch?v=tywt9tOubEY","topic":"unity-tilemap","version":"referencia-2019","priority":3,"enabled":false,"notes":"Encontrado em busca; abertura direta falhou. Legendas não verificadas. Revisar compatibilidade."},
    {"id":"V02","title":"Tile Map Basics - Unity Korea","kind":"video","url":"https://www.youtube.com/watch?v=dtpthaIYa8g","topic":"unity-tilemap","version":"referencia-2018","priority":3,"enabled":false,"notes":"Encontrado em busca; abertura direta falhou. Idioma/legendas elegíveis não confirmados."},
    {"id":"R01","title":"Fate Core - Taking Action Dice and The Ladder","kind":"article","url":"https://fate-srd.com/fate-core/taking-action-dice-ladder","topic":"regras-fate","version":"fate-core","priority":3,"enabled":false,"notes":"Não é regra aprovada do DiceVTT. Habilitar somente se adotar Fate Core."},
    {"id":"R02","title":"Dungeons and Dragons - portal SRD","kind":"article","url":"https://www.dndbeyond.com/srd","topic":"regras-descoberta","version":"escolher-edicao","priority":3,"enabled":false,"notes":"Portal de descoberta; não equivale às regras completas. PDF fora do pipeline atual."}
  ]
}
```
<!-- RAG_SOURCE_CATALOG_END -->

## 7. Contrato de leitura a implementar no Python

Os planos anteriores aceitam `.txt` e manifesto JSON v1. **A leitura direta deste catálogo `.md` é uma extensão futura**, ainda não implementada. Para mantê-la compatível:

1. Em `load_input(path)`, reconhecer `.md` apenas quando houver exatamente um par de marcadores `RAG_SOURCE_CATALOG_START/END` com um único bloco JSON entre eles. Não executar conteúdo Markdown nem coletar indiscriminadamente todos os links do documento.
2. Ler UTF-8, interpretar JSON, exigir `catalog_schema="rag-source-catalog/v1"` e validar tipos, campos obrigatórios, IDs únicos e limite de fontes.
3. Selecionar `enabled=true`; ordenar por `priority` e pela ordem original em caso de empate. Os desabilitados não devem gerar requests nem entrar no lote.
4. Revalidar esquema/domínio/tipo da URL no backend. Recalcular URL canônica e ID de vídeo; não confiar em `kind` como substituto da classificação.
5. Converter cada fonte selecionada para o manifesto já planejado: `url` → `original_url`, derivar `canonical_url`, manter `kind` revalidado e acrescentar `video_id` quando aplicável. O envelope usa `schema_version=1`, `status=draft`, `collection_executed=false`, `created_at` real, `output_directory` e `languages`.
6. Passar `project_id` ao contexto do lote; validar destino pela configuração do servidor, nunca confiar no caminho do catálogo como autorização de escrita.
7. Guardar `catalog_id`, `topic`, `version` e `notes` como contexto de curadoria no manifesto de execução/estado. Isso não altera o formato mínimo de entrada da UI nem deve ser anexado ao corpo extraído como se fosse uma afirmação da fonte. Se futuramente usados para filtros do RAG, definir explicitamente a extensão do cabeçalho/metadata antes de depender deles.
8. Prosseguir pelo pipeline existente e marcar `completed` somente após publicar o arquivo real. Em vídeo sem legenda elegível, emitir `skipped`; em 403, registrar bloqueio; em offline sem cache, emitir `offline_cache_miss`.

O catálogo não deve ser marcado como processado inteiro quando apenas uma parte foi coletada. O relatório precisa listar resultado individual por `catalog_id`, caminho gerado, URL real, hash e data efetiva.

Fluxo esperado:

```text
docs/catalogo-fontes-documentacao-rag.md
    → bloco JSON validado
    → fontes enabled=true
    → manifesto de entrada v1
    → aquisição web/legendas ou cache offline
    → documentacao_rag/*.md com proveniência
    → Indexador Estático: chunks + embeddings
    → Chroma local
    → recuperação + scripts C# ao vivo
    → AirLLM
```

Antes do adaptador `.md` existir, é possível selecionar URLs das tabelas e colá-las na UI atual de ingestão. Não importar este arquivo inteiro como lista `.txt` de URLs. O catálogo não cria nenhum job por conta própria.

## 8. Manutenção e aceite do catálogo

- Acrescentar uma nova fonte no JSON e uma linha descritiva na seção correspondente. Não reutilizar IDs existentes.
- Preferir páginas específicas a homepages, pesquisas, canais ou índices gigantes. Não seguir links recursivamente sem escopo explícito.
- Quando a Unity ou um pacote mudar de versão, revisar as referências antes de reindexar. Não substituir versão fixada por `latest` silenciosamente.
- Para fóruns, cadastrar o permalink do tópico que resolve um problema concreto, não a página inicial. Marcar como fonte comunitária, comparar com a API oficial e selecionar inclusão de comentários conscientemente.
- Revisar corpo extraído: exemplos C#, tabelas e fórmulas não podem desaparecer sem aviso. Fontes incompletas não passam a ser documentação confiável por terem embedding.
- O teste de leitura deve confirmar 19 registros válidos, 12 habilitados e 7 desabilitados nesta versão; nenhuma URL duplicada e IDs de vídeo com 11 caracteres.
- Os testes de ingestão/indexação devem seguir os [critérios do pipeline](plano-ingestao-documentacao-rag.md) e o [aceite conjunto do RAG](plano-rag-dinamico-airllm-claude.md).

Este documento entrega a seleção inicial e o contrato de leitura. Não inclui textos integrais de terceiros, legendas baixadas ou regras inventadas para o DiceVTT.
