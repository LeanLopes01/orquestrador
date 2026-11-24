# Catálogo completo de integrações do n8n-claw

Inventário levantado em 27/10/2026 e atualizado para a entrega em 28/10/2026. Foram lidos os manifestos das **75 entradas** da revisão que o próprio `mcp-library-manager.json` local referencia. O README local fala em 43 e está desatualizado em relação a essa revisão. A instalação dos adaptadores e a associação das credenciais estão em [ENTREGA.md](ENTREGA.md); os argumentos de cada operação estão em [OPERACOES.md](OPERACOES.md).

Revisão fixada: `fb71ed429520aa48b071b01a911f31293b56fae7`. [Índice de origem](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/index.json). [Snapshot local com manifestos e hashes](catalogo-n8n-claw.json). Os 75 adaptadores estão empacotados e seus contratos foram verificados. O relógio passou por execução no n8n real; **não foram testadas contas reais nos 75 provedores**. A API separa as operações pelo identificador de cada integração para evitar colisões.

Há **49 entradas com campos de configuração obrigatórios** e **26 sem campos obrigatórios** no manifesto. Algumas configurações são apenas URLs/tópicos; isso não equivale a 49 contas pessoais distintas. Outlook e canais Telegram/Slack/Teams/Discord/WhatsApp são adicionais, detalhados em [CONTAS.md](CONTAS.md).

## Procedimento comum

Para cada entrada: (1) instalar o adaptador revisado; (2) obter autorização no provedor seguindo a instrução abaixo; (3) cadastrar os campos em uma credencial criptografada do n8n e associar conta/serviço; (4) testar identidade e recurso conhecido; (5) habilitar somente os dispositivos e operações escolhidos. Credenciais existentes são preservadas. Não colar tokens em chat, JSON de workflow, catálogo ou formulário público do template.

Os endereços e campos são orientações dos manifestos consultados. Menus, planos e APIs precisam ser confirmados na implementação. Não há promessa de gratuidade, quota, disponibilidade ou compatibilidade baseada apenas no manifesto. Testar leitura primeiro; ferramentas de envio/escrita/execução requerem autorização e teste próprio. Skills sem credenciais também podem transmitir dados a serviços externos.

## Índice

| # | Integração | ID | Configuração obrigatória |
| --- | --- | --- | --- |
| 1 | [Weather (Open-Meteo)](#weather-openmeteo) | `weather-openmeteo` | Nenhuma no manifesto |
| 2 | [Wikipedia](#wikipedia) | `wikipedia` | Nenhuma no manifesto |
| 3 | [Exchange Rates](#exchange-rates) | `exchange-rates` | Nenhuma no manifesto |
| 4 | [Hacker News](#hackernews) | `hackernews` | Nenhuma no manifesto |
| 5 | [Dictionary](#dictionary) | `dictionary` | Nenhuma no manifesto |
| 6 | [IP Geolocation](#ip-geolocation) | `ip-geolocation` | Nenhuma no manifesto |
| 7 | [Website Check](#website-check) | `website-check` | Nenhuma no manifesto |
| 8 | [News (NewsAPI)](#news-newsapi) | `news-newsapi` | `newsapi_key` |
| 9 | [OpenClaw](#openclaw) | `openclaw` | `openclaw_url`, `openclaw_token`, `openclaw_caller_id` |
| 10 | [Email (IMAP/SMTP)](#email-imap-smtp) | `email-imap-smtp` | `email_user`, `email_password`, `imap_host`, `smtp_host` |
| 11 | [Route Planner (OpenRouteService)](#route-planner) | `route-planner` | `ors_api_key` |
| 12 | [Wiener Linien](#wiener-linien) | `wiener-linien` | Nenhuma no manifesto |
| 13 | [QR Code Generator](#qr-code) | `qr-code` | Nenhuma no manifesto |
| 14 | [Country Info](#country-info) | `country-info` | Nenhuma no manifesto |
| 15 | [Public Holidays](#public-holidays) | `public-holidays` | Nenhuma no manifesto |
| 16 | [Crypto Prices](#crypto-prices) | `crypto-prices` | Nenhuma no manifesto |
| 17 | [Trivia](#trivia) | `trivia` | Nenhuma no manifesto |
| 18 | [Timezone & World Clock](#timezone-world-clock) | `timezone-world-clock` | Nenhuma no manifesto |
| 19 | [Recipes](#recipes) | `recipes` | Nenhuma no manifesto |
| 20 | [NocoDB](#nocodb-crm) | `nocodb-crm` | `nocodb_url`, `nocodb_token` |
| 21 | [Todoist](#todoist) | `todoist` | `todoist_token` |
| 22 | [GitHub](#github-api) | `github-api` | `github_pat` |
| 23 | [TMDB Movies & TV](#tmdb-movies) | `tmdb-movies` | `tmdb_api_key` |
| 24 | [DeepL Translate](#deepl-translate) | `deepl-translate` | `deepl_api_key` |
| 25 | [PDF Tools (pdf-mcp.io)](#pdf-mcp) | `pdf-mcp` | `pdfmcp_api_key` |
| 26 | [Vexa Meetings](#vexa-meetings) | `vexa-meetings` | `vexa_api_key`, `vexa_tx_key` |
| 27 | [Notion](#notion) | `notion` | `notion_token` |
| 28 | [KontoFlux](#kontoflux) | `kontoflux` | `kontoflux_api_key`, `kontoflux_workspace_id` |
| 29 | [OpenWebUI Knowledge Manager](#openwebui-knowledge) | `openwebui-knowledge` | `openwebui_url`, `openwebui_api_key` |
| 30 | [OpenFoodFacts](#openfoodfacts) | `openfoodfacts` | Nenhuma no manifesto |
| 31 | [Deutsche Bahn](#deutsche-bahn) | `deutsche-bahn` | Nenhuma no manifesto |
| 32 | [DZT Germany Tourism](#dzt-germany-tourism) | `dzt-germany-tourism` | Nenhuma no manifesto |
| 33 | [CalDAV Calendar](#caldav-calendar) | `caldav-calendar` | `caldav_url`, `caldav_username`, `caldav_password` |
| 34 | [Vikunja](#vikunja) | `vikunja` | `vikunja_url`, `vikunja_token` |
| 35 | [Nextcloud Files](#nextcloud-files) | `nextcloud-files` | `nextcloud_url`, `nextcloud_username`, `nextcloud_password` |
| 36 | [Seafile](#seafile) | `seafile` | `seafile_url`, `seafile_token` |
| 37 | [Gmail](#gmail) | `gmail` | `client_id`, `client_secret` |
| 38 | [Google Calendar](#google-calendar) | `google-calendar` | `client_id`, `client_secret` |
| 39 | [Google Drive](#google-drive) | `google-drive` | `client_id`, `client_secret` |
| 40 | [Google Analytics](#google-analytics) | `google-analytics` | `client_id`, `client_secret` |
| 41 | [Google Ads](#google-ads) | `google-ads` | `client_id`, `client_secret`, `developer_token`, `customer_id` |
| 42 | [Lexware Office](#lexware) | `lexware` | `lexware_api_token` |
| 43 | [Config Backup & Restore](#config-backup) | `config-backup` | Nenhuma no manifesto |
| 44 | [Google Media Generation](#google-media-gen) | `google-media-gen` | `gemini_api_key` |
| 45 | [ÖBB](#oebb) | `oebb` | Nenhuma no manifesto |
| 46 | [SBB](#sbb) | `sbb` | Nenhuma no manifesto |
| 47 | [ÖPNV Deutschland](#oepnv) | `oepnv` | Nenhuma no manifesto |
| 48 | [DeepWiki](#deepwiki) | `deepwiki` | Nenhuma no manifesto |
| 49 | [Overpass (OpenStreetMap)](#overpass-osm) | `overpass-osm` | Nenhuma no manifesto |
| 50 | [ntfy.sh](#ntfy) | `ntfy` | `ntfy_topic` |
| 51 | [Home Assistant](#home-assistant) | `home-assistant` | `ha_url`, `ha_token` |
| 52 | [Airtable](#airtable) | `airtable` | `airtable_pat` |
| 53 | [Open Library](#openlibrary) | `openlibrary` | Nenhuma no manifesto |
| 54 | [Unsplash](#unsplash) | `unsplash` | `unsplash_access_key` |
| 55 | [OpenAQ Air Quality](#openaq) | `openaq` | `openaq_api_key` |
| 56 | [Finnhub Stocks](#finnhub) | `finnhub` | `finnhub_api_key` |
| 57 | [YouTube Data](#youtube) | `youtube` | `youtube_api_key` |
| 58 | [Asana](#asana) | `asana` | `asana_pat` |
| 59 | [Jira Cloud](#jira) | `jira` | `atlassian_email`, `atlassian_api_token`, `atlassian_site` |
| 60 | [Confluence Cloud](#confluence) | `confluence` | `atlassian_email`, `atlassian_api_token`, `atlassian_site` |
| 61 | [Stripe](#stripe) | `stripe` | `stripe_api_key` |
| 62 | [HubSpot CRM](#hubspot) | `hubspot` | `hubspot_pat` |
| 63 | [Salesforce CRM](#salesforce) | `salesforce` | `salesforce_instance_url`, `salesforce_consumer_key`, `salesforce_consumer_secret` |
| 64 | [Zoho CRM](#zoho-crm) | `zoho-crm` | `zoho_region`, `zoho_client_id`, `zoho_client_secret`, `zoho_grant_code` |
| 65 | [WordPress](#wordpress) | `wordpress` | `wp_url`, `wp_username`, `wp_app_password` |
| 66 | [Shopify](#shopify) | `shopify` | `shopify_store`, `shopify_access_token` |
| 67 | [GENESIS-Online (Destatis)](#genesis-destatis) | `genesis-destatis` | `genesis_token` |
| 68 | [DataForSEO](#dataforseo) | `dataforseo` | `dataforseo_login`, `dataforseo_password` |
| 69 | [wger Exercises](#wger-exercises) | `wger-exercises` | Nenhuma no manifesto |
| 70 | [Fitness Buddy](#fitness-buddy) | `fitness-buddy` | `openai_api_key` |
| 71 | [Apify Actors](#apify) | `apify` | `auth_token` |
| 72 | [BFL FLUX Image Generation](#bfl-flux) | `bfl-flux` | `bfl_api_key` |
| 73 | [Meta Ads](#meta-ads) | `meta-ads` | `auth_token` |
| 74 | [TikTok Ads](#tiktok-ads) | `tiktok-ads` | `auth_token` |
| 75 | [Open Terminal](#open-terminal) | `open-terminal` | `terminal_url`, `terminal_api_key` |

## Instruções por integração

<a id="weather-openmeteo"></a>

### 1. Weather (Open-Meteo)

ID `weather-openmeteo` · versão `1.1.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/weather-openmeteo/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Campos opcionais do manifesto (avaliar necessidade antes de habilitar): `open_meteo_commercial`.

Ferramentas de referência: `get_weather`, `get_hourly_forecast`, `get_air_quality`, `get_weather_history`, `get_marine_weather`, `get_weather_alerts`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="wikipedia"></a>

### 2. Wikipedia

ID `wikipedia` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/wikipedia/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_wikipedia`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="exchange-rates"></a>

### 3. Exchange Rates

ID `exchange-rates` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/exchange-rates/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `convert_currency`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="hackernews"></a>

### 4. Hacker News

ID `hackernews` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/hackernews/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_hackernews`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="dictionary"></a>

### 5. Dictionary

ID `dictionary` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/dictionary/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `define_word`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="ip-geolocation"></a>

### 6. IP Geolocation

ID `ip-geolocation` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/ip-geolocation/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `geolocate_ip`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="website-check"></a>

### 7. Website Check

ID `website-check` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/website-check/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `check_website`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="news-newsapi"></a>

### 8. News (NewsAPI)

ID `news-newsapi` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/news-newsapi/manifest.json).

Criar conta em https://newsapi.org/register, abrir o painel da conta e gerar/copiar a API key. Cadastrar em newsapi_key; validar uma pesquisa pequena antes de programar monitoramento.

Campos obrigatórios:

- `newsapi_key` — NewsAPI Key.

Ferramentas de referência: `search_news`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="openclaw"></a>

### 9. OpenClaw

ID `openclaw` · versão `2.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/openclaw/manifest.json).

Preparar uma instância isolada de OpenClaw; obter URL do gateway e token de seu administrador, definir caller_id exclusivo para Jarvis. A URL precisa ser alcançável pelo servidor. Testar uma mensagem sem instruções de execução; não entregar shell do servidor principal.

Campos obrigatórios:

- `openclaw_url` — OpenClaw Gateway URL.
- `openclaw_token` — OpenClaw Gateway Token.
- `openclaw_caller_id` — Caller ID.

Ferramentas de referência: `openclaw_send_message`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="email-imap-smtp"></a>

### 10. Email (IMAP/SMTP)

ID `email-imap-smtp` · versão `1.1.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/email-imap-smtp/manifest.json).

Na conta de e-mail, habilitar IMAP e consultar hosts, portas e TLS documentados pelo provedor. Criar senha de aplicativo quando esse método for permitido e informar usuário completo. Gmail/Outlook devem preferir seus conectores OAuth. Instalar Email Bridge interno; validar leitura da caixa antes de habilitar envio SMTP.

Campos obrigatórios:

- `email_user` — Email Address.
- `email_password` — Email Password.
- `imap_host` — IMAP Server.
- `smtp_host` — SMTP Server.

Campos opcionais do manifesto (avaliar necessidade antes de habilitar): `imap_port`, `smtp_port`.

Ferramentas de referência: `read_emails`, `send_email`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="route-planner"></a>

### 11. Route Planner (OpenRouteService)

ID `route-planner` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/route-planner/manifest.json).

Cadastrar aplicação no painel de desenvolvedor https://openrouteservice.org/dev/#/signup e emitir chave. Guardar em ors_api_key, escolher perfil de transporte suportado e consultar rota de teste sem dados pessoais.

Campos obrigatórios:

- `ors_api_key` — OpenRouteService API Key.

Ferramentas de referência: `plan_route`, `plan_route_outdoor`, `search_place`, `find_pois`, `get_elevation_profile`, `get_isochrone`; mais 1 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="wiener-linien"></a>

### 12. Wiener Linien

ID `wiener-linien` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/wiener-linien/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `create_route_public_transport_vienna`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="qr-code"></a>

### 13. QR Code Generator

ID `qr-code` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/qr-code/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `generate_qr_code`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="country-info"></a>

### 14. Country Info

ID `country-info` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/country-info/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `get_country_info`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="public-holidays"></a>

### 15. Public Holidays

ID `public-holidays` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/public-holidays/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `get_public_holidays`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="crypto-prices"></a>

### 16. Crypto Prices

ID `crypto-prices` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/crypto-prices/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `get_crypto_price`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="trivia"></a>

### 17. Trivia

ID `trivia` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/trivia/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `get_trivia`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="timezone-world-clock"></a>

### 18. Timezone & World Clock

ID `timezone-world-clock` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/timezone-world-clock/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `get_time`, `convert_timezone`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="recipes"></a>

### 19. Recipes

ID `recipes` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/recipes/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_recipe`, `random_recipe`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="nocodb-crm"></a>

### 20. NocoDB

ID `nocodb-crm` · versão `1.1.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/nocodb-crm/manifest.json).

Na instância NocoDB, abrir configurações da conta e API Tokens. Criar token para bases necessárias, cadastrar URL base e token, descobrir IDs reais de base/tabela e testar listagem. Não confundir URL pública do painel com endereço inacessível ao servidor.

Campos obrigatórios:

- `nocodb_url` — NocoDB Instance URL.
- `nocodb_token` — NocoDB API Token.

Ferramentas de referência: `nocodb_list_bases`, `nocodb_list_tables`, `nocodb_list_records`, `nocodb_get_record`, `nocodb_create_record`, `nocodb_update_record`; mais 11 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="todoist"></a>

### 21. Todoist

ID `todoist` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/todoist/manifest.json).

Abrir configurações do Todoist, integrações e área de desenvolvedor; obter token da conta e cadastrar em todoist_token. Conferir usuário/projetos e listar tarefas de um projeto conhecido antes de habilitar conclusão/criação.

Campos obrigatórios:

- `todoist_token` — Todoist API Token.

Ferramentas de referência: `list_tasks`, `create_task`, `complete_task`, `list_projects`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="github-api"></a>

### 22. GitHub

ID `github-api` · versão `1.1.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/github-api/manifest.json).

Em https://github.com/settings/tokens, criar token para repositórios escolhidos. Preferir fine-grained quando as operações do adaptador o suportarem; conferir permissões e aprovação SSO da organização. Cadastrar github_pat e testar leitura de um arquivo privado autorizado. O template sugere escopos clássicos amplos; adaptar ao conjunto efetivamente usado.

Campos obrigatórios:

- `github_pat` — GitHub Personal Access Token.

Ferramentas de referência: `search_repos`, `get_repo_info`, `list_issues`, `create_issue`, `list_pull_requests`, `get_pull_request`; mais 5 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="tmdb-movies"></a>

### 23. TMDB Movies & TV

ID `tmdb-movies` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/tmdb-movies/manifest.json).

Abrir https://www.themoviedb.org/settings/api e cadastrar o uso da API. O manifesto pede API Read Access Token apesar do campo se chamar tmdb_api_key; verificar o esquema Bearer do workflow e usar esse token, sem misturar com chave v3 de query. Testar busca de filme.

Campos obrigatórios:

- `tmdb_api_key` — TMDB API Key (Bearer Token).

Ferramentas de referência: `search_movie`, `search_tv`, `get_trending`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="deepl-translate"></a>

### 24. DeepL Translate

ID `deepl-translate` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/deepl-translate/manifest.json).

Na conta DeepL API, criar chave e identificar se o plano usa endpoint Free ou Pro. Cadastrar deepl_api_key e configurar o endpoint correspondente no adaptador. Testar uma frase curta e conferir quota no provedor.

Campos obrigatórios:

- `deepl_api_key` — DeepL API Key.

Ferramentas de referência: `translate_text`, `detect_language`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="pdf-mcp"></a>

### 25. PDF Tools (pdf-mcp.io)

ID `pdf-mcp` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/pdf-mcp/manifest.json).

Criar conta em https://pdf-mcp.io, gerar chave e cadastrar pdfmcp_api_key. Escolher arquivo público de teste para extração. Esse serviço recebe arquivos fora do servidor; para PDFs pessoais, preferir o processador local/servidor previsto no plano quando aplicável.

Campos obrigatórios:

- `pdfmcp_api_key` — pdf-mcp.io API Key.

Ferramentas de referência: `html_to_pdf`, `extract_text`, `merge_pdfs`, `list_files`, `get_file`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="vexa-meetings"></a>

### 26. Vexa Meetings

ID `vexa-meetings` · versão `2.2.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/vexa-meetings/manifest.json).

No painel https://vexa.ai/dashboard, gerar as duas chaves: bot e transcrição. Preencher vexa_api_key e vexa_tx_key separadamente; a chave de bot não substitui a de transcrição. Validar listagem e leitura de transcrição de reunião de teste autorizada antes de permitir entrada de bot em reuniões.

Campos obrigatórios:

- `vexa_api_key` — Vexa Bot API Key.
- `vexa_tx_key` — Vexa Transcription API Key.

Campos opcionais do manifesto (avaliar necessidade antes de habilitar): `vexa_url`, `vexa_bot_name`.

Ferramentas de referência: `deploy_meeting_bot`, `get_transcript`, `share_transcript`, `list_bots`, `stop_bot`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="notion"></a>

### 27. Notion

ID `notion` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/notion/manifest.json).

Seguir CONTAS.md, seção Notion: integração do workspace, permissão de leitura, compartilhar a base/página original e cadastrar token. Testar página conhecida. O conector do catálogo não substitui sozinho a migração de data sources e tarefas do gateway atual.

Campos obrigatórios:

- `notion_token` — Notion Integration Token.

Ferramentas de referência: `search_pages`, `read_page`, `create_page`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="kontoflux"></a>

### 28. KontoFlux

ID `kontoflux` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/kontoflux/manifest.json).

No workspace KontoFlux, obter API key e workspace ID; concluir o vínculo bancário no próprio serviço, se desejado. Cadastrar ambos e validar escopo/listagem em ambiente permitido. Confirmar cobertura do país/banco: o template é orientado a Open Banking alemão, não garante bancos brasileiros.

Campos obrigatórios:

- `kontoflux_api_key` — KontoFlux API Key.
- `kontoflux_workspace_id` — KontoFlux Workspace ID.

Ferramentas de referência: `list_accounts`, `get_transactions`, `search_transactions`, `list_categories`, `check_scope`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="openwebui-knowledge"></a>

### 29. OpenWebUI Knowledge Manager

ID `openwebui-knowledge` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/openwebui-knowledge/manifest.json).

Na sua instância OpenWebUI, habilitar acesso de API conforme política do administrador e gerar chave em Settings/Account/API Keys. Cadastrar URL e chave, listar uma coleção autorizada. Essa integração é opcional e não substitui o RAG local do DiceVTT.

Campos obrigatórios:

- `openwebui_url` — OpenWebUI URL.
- `openwebui_api_key` — OpenWebUI API Key.

Ferramentas de referência: `list_knowledge`, `create_knowledge`, `get_knowledge`, `update_knowledge`, `delete_knowledge`, `list_files`; mais 4 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="openfoodfacts"></a>

### 30. OpenFoodFacts

ID `openfoodfacts` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/openfoodfacts/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `lookup_barcode`, `search_food`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="deutsche-bahn"></a>

### 31. Deutsche Bahn

ID `deutsche-bahn` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/deutsche-bahn/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_station`, `get_departures`, `get_arrivals`, `search_journey`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="dzt-germany-tourism"></a>

### 32. DZT Germany Tourism

ID `dzt-germany-tourism` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/dzt-germany-tourism/manifest.json).

Fonte de turismo alemão. Confirmar cobertura/disponibilidade do endpoint e testar lugar público; não substitui uma fonte de turismo brasileira.

Ferramentas de referência: `get_pois_by_criteria`, `get_events_by_criteria`, `get_trails_by_criteria`, `get_entity_details`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="caldav-calendar"></a>

### 33. CalDAV Calendar

ID `caldav-calendar` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/caldav-calendar/manifest.json).

Obter URL CalDAV do provedor, usuário e senha de aplicativo. Configurar no n8n e descobrir calendários via DAV antes de selecionar o calendário real. Testar leitura de evento; habilitar criação/alteração separadamente.

Campos obrigatórios:

- `caldav_url` — CalDAV Server URL (e.g. https://nextcloud.example.com/remote.php/dav).
- `caldav_username` — Username.
- `caldav_password` — Password or App Password.

Ferramentas de referência: `list_calendars`, `list_events`, `create_event`, `update_event`, `delete_event`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="vikunja"></a>

### 34. Vikunja

ID `vikunja` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/vikunja/manifest.json).

Na instância Vikunja, criar API token em Settings/API Tokens com acesso aos projetos desejados. Cadastrar URL e token; listar projeto e tarefa conhecidos. Registrar prazo de validade e permissões de escrita quando usadas.

Campos obrigatórios:

- `vikunja_url` — Vikunja Instance URL.
- `vikunja_token` — Vikunja API Token.

Ferramentas de referência: `vikunja_list_projects`, `vikunja_list_tasks`, `vikunja_get_task`, `vikunja_create_task`, `vikunja_update_task`, `vikunja_delete_task`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="nextcloud-files"></a>

### 35. Nextcloud Files

ID `nextcloud-files` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/nextcloud-files/manifest.json).

Em Nextcloud, Settings/Security/App passwords, criar senha de aplicativo. Preencher URL raiz, usuário e essa senha. Testar WebDAV listando uma pasta autorizada e lendo arquivo conhecido; liberar upload/remoção separadamente.

Campos obrigatórios:

- `nextcloud_url` — Nextcloud URL (e.g. https://cloud.example.com).
- `nextcloud_username` — Username.
- `nextcloud_password` — App Password (Settings > Security > App passwords).

Ferramentas de referência: `list_files`, `read_file`, `write_file`, `upload_file`, `download_file`, `upload_from_url`; mais 3 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="seafile"></a>

### 36. Seafile

ID `seafile` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/seafile/manifest.json).

Abrir biblioteca Seafile escolhida e criar API token para ela; preferir leitura quando o adaptador permitir. Cadastrar URL raiz e token, identificar a biblioteca e testar repo_info/listagem. Operações de escrita precisam de permissão correspondente, não de substituir todos os tokens por acesso amplo.

Campos obrigatórios:

- `seafile_url` — Seafile Instance URL.
- `seafile_token` — Seafile Library API Token.

Ferramentas de referência: `repo_info`, `list_directory`, `get_file_detail`, `download_file`, `upload_file`, `create_file`; mais 2 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="gmail"></a>

### 37. Gmail

ID `gmail` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/gmail/manifest.json).

Seguir CONTAS.md, seção Google: habilitar Gmail API, configurar cliente OAuth Web e credencial por conta. Começar com gmail.readonly e selecionar explicitamente o Gmail correto; ampliar escopos para envio somente quando implementar esse recurso.

Campos obrigatórios:

- `client_id` — Google OAuth Client ID.
- `client_secret` — Google OAuth Client Secret.

Ferramentas de referência: `search_emails`, `read_email`, `send_email`, `create_draft`, `list_labels`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="google-calendar"></a>

### 38. Google Calendar

ID `google-calendar` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/google-calendar/manifest.json).

Seguir CONTAS.md, seção Google: habilitar Calendar API e cadastrar OAuth por conta. Descobrir calendários acessíveis, selecionar quais consultar e testar evento conhecido. Escopo inicial calendar.readonly; escrita exige consentimento adicional.

Campos obrigatórios:

- `client_id` — Google OAuth Client ID.
- `client_secret` — Google OAuth Client Secret.

Ferramentas de referência: `list_events`, `create_event`, `update_event`, `delete_event`, `list_calendars`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="google-drive"></a>

### 39. Google Drive

ID `google-drive` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/google-drive/manifest.json).

Seguir CONTAS.md, seção Google: habilitar Drive API, OAuth por conta e drive.readonly. Testar arquivo existente, exportação de Docs e pastas compartilhadas necessárias. O template pede drive amplo; adaptar leitura e escrita em políticas separadas.

Campos obrigatórios:

- `client_id` — Google OAuth Client ID.
- `client_secret` — Google OAuth Client Secret.

Ferramentas de referência: `list_files`, `search_files`, `read_file`, `create_file`, `create_folder`, `delete_file`; mais 3 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="google-analytics"></a>

### 40. Google Analytics

ID `google-analytics` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/google-analytics/manifest.json).

Seguir CONTAS.md, seção Google: habilitar APIs de dados/administração usadas, autorizar analytics.readonly e dar acesso do usuário à propriedade GA4. Descobrir property ID e comparar relatório de teste com o painel.

Campos obrigatórios:

- `client_id` — Google OAuth Client ID.
- `client_secret` — Google OAuth Client Secret.

Ferramentas de referência: `get_report`, `list_properties`, `get_realtime_data`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="google-ads"></a>

### 41. Google Ads

ID `google-ads` · versão `1.0.0-beta` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/google-ads/manifest.json).

Seguir CONTAS.md, seção Google: configurar OAuth adwords, acesso de API, developer token e customer ID da conta. Caso use conta gerente, conferir login-customer-id. Validar listagem de campanhas sem alterar anúncios; elegibilidade do token é verificada no provedor.

Campos obrigatórios:

- `client_id` — Google OAuth Client ID.
- `client_secret` — Google OAuth Client Secret.
- `developer_token` — Google Ads Developer Token.
- `customer_id` — Google Ads Customer ID.

Campos opcionais do manifesto (avaliar necessidade antes de habilitar): `login_customer_id`.

Ferramentas de referência: `list_campaigns`, `get_campaign_stats`, `list_ad_groups`, `get_account_stats`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="lexware"></a>

### 42. Lexware Office

ID `lexware` · versão `2.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/lexware/manifest.json).

Na conta Lexware, abrir https://app.lexware.de/addons/public-api, habilitar acesso permitido pelo plano e emitir token. Cadastrar lexware_api_token e listar contatos/documentos de teste. Criar ou enviar documento fiscal/comercial será uma ação separada com prévia.

Campos obrigatórios:

- `lexware_api_token` — Lexware API Token.

Ferramentas de referência: `list_contacts`, `get_contact`, `create_company`, `create_person`, `update_contact_address`, `update_contact_email`; mais 17 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="config-backup"></a>

### 43. Config Backup & Restore

ID `config-backup` · versão `1.2.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/config-backup/manifest.json).

Não exige conta, mas acessa configuração do sistema. Adaptar ao backup criptografado e restauração isolada de IMPLANTACAO.md; restore_backup nunca participa de teste automático em produção.

Ferramentas de referência: `create_backup`, `show_backup`, `restore_backup`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="google-media-gen"></a>

### 44. Google Media Generation

ID `google-media-gen` · versão `1.2.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/google-media-gen/manifest.json).

No Google AI Studio, criar chave para o projeto desejado e cadastrar gemini_api_key. Conferir APIs, região, modelos disponíveis e faturamento. Executar pequena geração autorizada; a chave não é um token OAuth do Gmail e o processamento ocorre no provedor.

Campos obrigatórios:

- `gemini_api_key` — Google Gemini API Key.

Ferramentas de referência: `generate_image`, `edit_image`, `generate_video`, `animate_image`, `wait_for_video`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="oebb"></a>

### 45. ÖBB

ID `oebb` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/oebb/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_station`, `get_departures`, `get_arrivals`, `search_journey`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="sbb"></a>

### 46. SBB

ID `sbb` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/sbb/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_station`, `get_departures`, `get_arrivals`, `search_journey`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="oepnv"></a>

### 47. ÖPNV Deutschland

ID `oepnv` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/oepnv/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_station`, `get_departures`, `get_arrivals`, `search_journey`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="deepwiki"></a>

### 48. DeepWiki

ID `deepwiki` · versão `1.0.0` · tipo `bridge`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/deepwiki/manifest.json).

Bridge MCP externo para documentação de repositórios públicos. Validar URL/transporte e consultar repositório público; não enviar código privado por supor que é uma ferramenta local.

Ferramentas de referência: `read_wiki_structure`, `read_wiki_contents`, `ask_question`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="overpass-osm"></a>

### 49. Overpass (OpenStreetMap)

ID `overpass-osm` · versão `1.3.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/overpass-osm/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Campos opcionais do manifesto (avaliar necessidade antes de habilitar): `overpass_endpoint`.

Ferramentas de referência: `geocode_place`, `find_nearby`, `reverse_geocode`, `search_custom`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="ntfy"></a>

### 50. ntfy.sh

ID `ntfy` · versão `1.0.1` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/ntfy/manifest.json).

Preferir instância ntfy própria com autenticação e ACL de tópico. Criar tópico por usuário/dispositivo, cadastrar endereço e token quando suportados e assinar o mesmo tópico no cliente. Adaptar o template para não tratar nome secreto do tópico como única autorização. Enviar somente aviso de teste consentido; histórico permanece no Jarvis.

Campos obrigatórios:

- `ntfy_topic` — ntfy Topic Name.

Campos opcionais do manifesto (avaliar necessidade antes de habilitar): `ntfy_server_url`, `ntfy_token`.

Ferramentas de referência: `send_notification`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="home-assistant"></a>

### 51. Home Assistant

ID `home-assistant` · versão `1.1.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/home-assistant/manifest.json).

Na instância Home Assistant, criar token de longa duração em Profile/Security e cadastrar URL raiz sem /api. Usar usuário dedicado e acesso de rede restrito. Listar entidades e ler estado; chamadas de serviço e voz exigem habilitação própria.

Campos obrigatórios:

- `ha_url` — Home Assistant URL.
- `ha_token` — Long-Lived Access Token.

Ferramentas de referência: `list_entities`, `get_state`, `list_services`, `call_service`, `speak`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="airtable"></a>

### 52. Airtable

ID `airtable` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/airtable/manifest.json).

Em https://airtable.com/create/tokens, criar PAT restrito às bases desejadas. Para leitura, selecionar data.records:read e schema.bases:read; acrescentar escrita somente se usada. Cadastrar airtable_pat e testar base/tabela/registro conhecido.

Campos obrigatórios:

- `airtable_pat` — Airtable Personal Access Token.

Ferramentas de referência: `list_bases`, `list_tables`, `list_records`, `get_record`, `create_record`, `update_record`; mais 1 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="openlibrary"></a>

### 53. Open Library

ID `openlibrary` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/openlibrary/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_books`, `get_book`, `get_author`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="unsplash"></a>

### 54. Unsplash

ID `unsplash` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/unsplash/manifest.json).

Em https://unsplash.com/oauth/applications, registrar aplicação e copiar Access Key, não Secret Key. Cadastrar unsplash_access_key e validar pesquisa; ao exibir/baixar imagens, implementar atribuição e requisitos de uso da API.

Campos obrigatórios:

- `unsplash_access_key` — Unsplash Access Key.

Ferramentas de referência: `search_photos`, `get_random_photo`, `get_photo`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="openaq"></a>

### 55. OpenAQ Air Quality

ID `openaq` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/openaq/manifest.json).

Criar conta em https://explore.openaq.org/register, gerar chave na área API Keys e cadastrar openaq_api_key. Pesquisar estação/localização de teste e validar unidades e horário da medição.

Campos obrigatórios:

- `openaq_api_key` — OpenAQ API Key.

Ferramentas de referência: `get_air_quality`, `find_stations`, `get_station_history`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="finnhub"></a>

### 56. Finnhub Stocks

ID `finnhub` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/finnhub/manifest.json).

Criar conta em https://finnhub.io/register e obter chave no painel. Cadastrar finnhub_api_key e consultar símbolo conhecido; exibir mercado, horário e eventual atraso do dado. Não habilitar operações financeiras a partir de uma ferramenta de cotações.

Campos obrigatórios:

- `finnhub_api_key` — Finnhub API Key.

Ferramentas de referência: `get_quote`, `get_company_profile`, `get_company_news`, `search_symbol`, `get_market_status`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="youtube"></a>

### 57. YouTube Data

ID `youtube` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/youtube/manifest.json).

No Google Cloud, habilitar YouTube Data API v3 e criar API key restrita a essa API; configurar restrição de rede compatível com o servidor quando possível. Cadastrar youtube_api_key e testar metadados de vídeo público. Esta skill não autentica sua conta YouTube nem fornece transcrições por si só.

Campos obrigatórios:

- `youtube_api_key` — YouTube Data API v3 Key.

Ferramentas de referência: `search_videos`, `get_video`, `get_channel`, `list_channel_videos`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="asana"></a>

### 58. Asana

ID `asana` · versão `1.1.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/asana/manifest.json).

Na conta Asana, abrir https://app.asana.com/0/my-apps e criar Personal Access Token. Cadastrar asana_pat, descobrir workspace/projeto e listar uma tarefa conhecida antes de habilitar atualizações.

Campos obrigatórios:

- `asana_pat` — Asana Personal Access Token.

Ferramentas de referência: `list_workspaces`, `list_projects`, `get_project`, `list_sections`, `list_tasks`, `get_task`; mais 10 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="jira"></a>

### 59. Jira Cloud

ID `jira` · versão `1.1.4` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/jira/manifest.json).

No perfil Atlassian, criar API token em https://id.atlassian.com/manage-profile/security/api-tokens. Cadastrar e-mail, token e site no formato esperado pelo adaptador. Se o token for scoped, conferir a URL de API apropriada; testar issue conhecida e registrar validade do token.

Campos obrigatórios:

- `atlassian_email` — Atlassian Email.
- `atlassian_api_token` — Atlassian API Token.
- `atlassian_site` — Atlassian Site URL.

Ferramentas de referência: `list_projects`, `search_issues`, `get_issue`, `create_issue`, `update_issue`, `add_comment`; mais 6 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="confluence"></a>

### 60. Confluence Cloud

ID `confluence` · versão `1.6.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/confluence/manifest.json).

Usar credencial Atlassian da conta correta ou criar token próprio, com e-mail e site. Conferir formato de endpoint para token scoped/classic e permissão no espaço/página. Ler página conhecida; compartilhamento de credencial com Jira só dentro da mesma identidade.

Campos obrigatórios:

- `atlassian_email` — Atlassian Email.
- `atlassian_api_token` — Atlassian API Token.
- `atlassian_site` — Atlassian Site URL.

Ferramentas de referência: `list_spaces`, `list_pages_in_space`, `search_pages`, `get_page`, `get_page_by_title`, `list_children`; mais 9 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="stripe"></a>

### 61. Stripe

ID `stripe` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/stripe/manifest.json).

No dashboard Stripe, criar chave restrita em modo de teste para os objetos necessários e cadastrar stripe_api_key. Validar listagem de clientes/faturas fictícias. Acesso real a cobrança, reembolso e pagamento exige projeto e autorização específicos, fora da ativação automática do catálogo.

Campos obrigatórios:

- `stripe_api_key` — Stripe API Key.

Ferramentas de referência: `list_customers`, `search_customers`, `get_customer`, `create_customer`, `update_customer`, `list_payments`; mais 17 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="hubspot"></a>

### 62. HubSpot CRM

ID `hubspot` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/hubspot/manifest.json).

Criar Private App na área de integrações da conta HubSpot, escolhendo escopos de leitura dos objetos usados. Copiar access token para hubspot_pat. Testar contato/empresa de exemplo; habilitar escopos de escrita só para ações implementadas.

Campos obrigatórios:

- `hubspot_pat` — HubSpot Private App Access Token.

Ferramentas de referência: `list_contacts`, `search_contacts`, `get_contact`, `create_contact`, `update_contact`, `delete_contact`; mais 22 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="salesforce"></a>

### 63. Salesforce CRM

ID `salesforce` · versão `1.0.1` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/salesforce/manifest.json).

No Setup Salesforce, criar External Client App/OAuth com fluxo Client Credentials suportado pela organização. Definir usuário Run-As dedicado, escopo API e políticas; copiar consumer key/secret. Cadastrar URL My Domain, não Lightning, e validar consulta de objeto. Confirmar que a edição permite API.

Campos obrigatórios:

- `salesforce_instance_url` — Salesforce Instance URL.
- `salesforce_consumer_key` — Consumer Key (Client ID).
- `salesforce_consumer_secret` — Consumer Secret.

Ferramentas de referência: `list_contacts`, `search_contacts`, `get_contact`, `create_contact`, `update_contact`, `delete_contact`; mais 29 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="zoho-crm"></a>

### 64. Zoho CRM

ID `zoho-crm` · versão `1.2.2` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/zoho-crm/manifest.json).

Identificar o data center da conta. No Zoho API Console dessa região, criar cliente apropriado (o template usa Self Client), copiar client ID/secret e gerar grant code com escopos necessários. Cadastrar região e dados; trocar o código de uso único imediatamente por refresh token em credencial criptografada. Não persistir refresh token em tabela aberta do template.

Campos obrigatórios:

- `zoho_region` — Zoho Region Code (just 'com' or 'eu' — not a URL).
- `zoho_client_id` — Client ID.
- `zoho_client_secret` — Client Secret.
- `zoho_grant_code` — Grant Code (one-time).

Ferramentas de referência: `list_leads`, `search_leads`, `get_lead`, `create_lead`, `update_lead`, `delete_lead`; mais 31 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="wordpress"></a>

### 65. WordPress

ID `wordpress` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/wordpress/manifest.json).

Na administração WordPress, criar usuário com papel compatível e Application Password em Users/Profile. Cadastrar URL do site, login e senha de aplicativo; não usar senha principal. Ler post conhecido via REST antes de habilitar rascunho/publicação.

Campos obrigatórios:

- `wp_url` — WordPress Site URL.
- `wp_username` — WordPress Username.
- `wp_app_password` — WordPress Application Password.

Ferramentas de referência: `list_posts`, `get_post`, `create_post`, `update_post`, `delete_post`, `list_pages`; mais 13 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="shopify"></a>

### 66. Shopify

ID `shopify` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/shopify/manifest.json).

No portal de desenvolvimento/administração Shopify da loja, criar app compatível com o modelo atual de distribuição e acesso Admin API. Selecionar escopos dos objetos usados, instalar/autorizar na loja e obter token pelo fluxo aplicável. Cadastrar domínio myshopify.com e token; validar produto em loja de teste. A emissão atual de tokens deve ser confirmada, sem depender do menu legado indicado no template.

Campos obrigatórios:

- `shopify_store` — Shopify Store Domain.
- `shopify_access_token` — Shopify Admin API Access Token.

Ferramentas de referência: `list_products`, `get_product`, `create_product`, `update_product`, `delete_product`, `list_orders`; mais 8 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="genesis-destatis"></a>

### 67. GENESIS-Online (Destatis)

ID `genesis-destatis` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/genesis-destatis/manifest.json).

Cadastrar acesso na API GENESIS-Online/Destatis e obter token segundo o portal do provedor. Preencher genesis_token e testar metadados/tabela pública. Confirmar o mecanismo vigente de token antes da implementação; o manifesto não traz instrução detalhada.

Campos obrigatórios:

- `genesis_token` — GENESIS-Online API Token.

Ferramentas de referência: `genesis_search`, `genesis_list_tables`, `genesis_list_statistics`, `genesis_list_variables`, `genesis_list_values`, `genesis_table_metadata`; mais 3 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="dataforseo"></a>

### 68. DataForSEO

ID `dataforseo` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/dataforseo/manifest.json).

Na conta DataForSEO, abrir área de acesso à API e obter login/senha específicos da API; não presumir que a senha do portal seja a mesma. Cadastrar ambos e testar saldo/consulta de menor custo antes de habilitar pesquisas cobradas.

Campos obrigatórios:

- `dataforseo_login` — DataForSEO Login (Email).
- `dataforseo_password` — DataForSEO API Password.

Ferramentas de referência: `dfs_account_balance`, `dfs_serp_google_organic`, `dfs_serp_google_organic_advanced`, `dfs_search_volume`, `dfs_keywords_for_keywords`, `dfs_google_trends`; mais 12 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="wger-exercises"></a>

### 69. wger Exercises

ID `wger-exercises` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/wger-exercises/manifest.json).

Não é necessário conectar uma conta segundo este manifesto. Instalar o adaptador revisado, configurar parâmetros de consulta e testar com informação pública conhecida. Registrar origem, data e falha de provedor; habilitar no Jarvis após o teste.

Ferramentas de referência: `search_exercises`, `get_exercise`, `list_categories`, `list_muscles`, `list_equipment`, `list_public_templates`; mais 1 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="fitness-buddy"></a>

### 70. Fitness Buddy

ID `fitness-buddy` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/fitness-buddy/manifest.json).

Configurar o provedor de visão em credencial própria, se usar análise de fotos, e adaptar schema de perfil/registros/rotinas no servidor. Não executar setup --force do template sobre a produção. Validar resumo com dados fictícios; tratar registros de saúde como privados e permitir apagar/exportar.

Campos obrigatórios:

- `openai_api_key` — OpenAI API Key.

Ferramentas de referência: `fitness_profile`, `log_meal`, `meal_memory`, `suggest_meal`, `log_workout`, `log_body`; mais 8 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="apify"></a>

### 71. Apify Actors

ID `apify` · versão `1.0.1` · tipo `bridge`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/apify/manifest.json).

Na Apify Console, gerar token em Settings/Integrations e cadastrar auth_token no bridge MCP. Testar descoberta de actor sem executá-lo. Execução de actor deve indicar entradas, destino e custo/limite; documentos pessoais não são enviados por simples instalação.

Campos obrigatórios:

- `auth_token` — Apify API Token.

Ferramentas de referência: `search-actors`, `fetch-actor-details`, `call-actor`, `get-actor-run`, `get-actor-output`, `search-apify-docs`; mais 2 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="bfl-flux"></a>

### 72. BFL FLUX Image Generation

ID `bfl-flux` · versão `1.0.0` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/bfl-flux/manifest.json).

No portal https://api.bfl.ai/, criar API key e cadastrar bfl_api_key. Conferir créditos/modelo disponível; testar consulta de créditos e depois geração pequena autorizada. É geração remota, diferente dos modelos locais do PC.

Campos obrigatórios:

- `bfl_api_key` — BFL API Key.

Ferramentas de referência: `generate_image`, `wait_for_image`, `get_credits`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="meta-ads"></a>

### 73. Meta Ads

ID `meta-ads` · versão `1.0.0` · tipo `bridge`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/meta-ads/manifest.json).

O template usa Pipeboard: criar conta nesse serviço, autorizar conta Meta Ads via OAuth e obter token em https://pipeboard.co/api-tokens. Cadastrar auth_token e validar listagem de contas. Se evitar intermediário for requisito, implementar adaptador Meta direto; não anunciar este bridge como acesso direto auto-hospedado.

Campos obrigatórios:

- `auth_token` — Pipeboard API Token.

Ferramentas de referência: `get_ad_accounts`, `get_account_info`, `get_account_pages`, `search_pages_by_name`, `get_pixels`, `get_account_activities`; mais 87 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="tiktok-ads"></a>

### 74. TikTok Ads

ID `tiktok-ads` · versão `1.0.0` · tipo `bridge`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/tiktok-ads/manifest.json).

O template usa Pipeboard: autorizar TikTok Ads na conta Pipeboard e gerar token em https://pipeboard.co/api-tokens. Cadastrar auth_token e listar advertisers permitidos. A alternativa é adaptador direto da API TikTok; criação/edição de campanha fica separada da conexão.

Campos obrigatórios:

- `auth_token` — Pipeboard API Token.

Ferramentas de referência: `list_tiktok_advertisers`, `get_tiktok_advertiser_info`, `get_tiktok_campaigns`, `create_tiktok_campaign`, `update_tiktok_campaign`, `update_tiktok_campaign_status`; mais 54 no snapshot.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

<a id="open-terminal"></a>

### 75. Open Terminal

ID `open-terminal` · versão `1.0.1` · tipo `native`. [Manifesto consultado](https://raw.githubusercontent.com/freddy-schuetz/n8n-claw-templates/fb71ed429520aa48b071b01a911f31293b56fae7/templates/open-terminal/manifest.json).

Preparar worker isolado e configurar OPEN_TERMINAL_API_KEY no serviço. Cadastrar URL alcançável e token correspondente; testar check_terminal. Não apontar para shell root do servidor. Ferramentas Windows seguem a disponibilidade do helper e só funcionam com programa aberto.

Campos obrigatórios:

- `terminal_url` — Open Terminal Base URL.
- `terminal_api_key` — Open Terminal API Key.

Ferramentas de referência: `run_command`, `send_input`, `read_file`, `write_file`, `list_files`, `check_terminal`.

Estado nesta entrega: **inventariado; implementação e teste real pendentes**.

## Regras de cobertura da implementação

A etapa de catálogo só termina quando cada uma dessas 75 linhas tiver adaptador/bridge compatível, credencial protegida quando necessária, contrato de entrada/saída, autorização, diagnóstico, limite e teste correspondente. Conta ausente pode impedir teste real e ativação, mas não deve ser confundida com conector implementado. Manter estados separados: pendente de implementação, pronto sem credencial, autorizado, verificado e habilitado.

Google A/B e qualquer outra identidade repetida geram conexões distintas. Compartilhar client ID não autoriza compartilhar refresh token. Bridge MCP externo permanece serviço externo. Não enviar secret do n8n ou seu endpoint administrativo ao modelo. Preservar licenças dos templates reutilizados e registrar revisão/hash de cada workflow importado.
