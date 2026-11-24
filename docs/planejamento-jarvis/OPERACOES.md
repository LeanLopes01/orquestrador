# Operações dos conectores instaláveis

Gerado dos workflows fixados em `fb71ed429520aa48b071b01a911f31293b56fae7`. Estes são contratos de referência, não resultados de testes nas suas contas.

Na interface: Contas → conector → ferramenta → argumentos JSON → Preparar chamada → revisar → Confirmar. Não forneça tokens nos argumentos. Os tokens ficam na credencial do n8n.

Toda chamada exige confirmação, inclusive consultas. Após timeout use Consultar resultado; uma operação de escrita pode ter sido concluída no provedor. Não repita sem conferir.

## Airtable (`airtable`)

JSON para preencher na credencial **Jarvis · Airtable** (substitua cada valor):

```json
{
  "airtable_pat": "PREENCHER"
}
```

### `list_bases`

List all Airtable bases accessible with the configured PAT. Returns base IDs, names, and permission levels.

```json
{}
```

### `list_tables`

List tables in an Airtable base with their fields, types, and views. Parameter: base_id (required, app... ID from list_bases).

```json
{
  "base_id": "PREENCHER"
}
```

### `list_records`

List records from a table. Parameters: base_id (required), table (required, table name or ID), max_records (optional, default 10), view (optional view name), filter_by_formula (optional Airtable formula, e.g. {Status}='Done'), sort_field (optional field name to sort by), sort_desc ('true' for descending).

```json
{
  "base_id": "PREENCHER",
  "table": "PREENCHER",
  "max_records": "PREENCHER",
  "view": "PREENCHER",
  "filter_by_formula": "PREENCHER",
  "sort_field": "PREENCHER",
  "sort_desc": "PREENCHER"
}
```

### `get_record`

Get a single record by ID. Parameters: base_id (required), table (required), record_id (required, rec... ID).

```json
{
  "base_id": "PREENCHER",
  "table": "PREENCHER",
  "record_id": "PREENCHER"
}
```

### `create_record`

Create a new record. Parameters: base_id (required), table (required), fields (required, JSON string with field values, e.g. '{"Name":"New task","Status":"To Do"}'). Linked records use arrays of record IDs.

```json
{
  "base_id": "PREENCHER",
  "table": "PREENCHER",
  "fields": "PREENCHER"
}
```

### `update_record`

Update fields on an existing record (partial update — only specified fields change). Parameters: base_id (required), table (required), record_id (required), fields (required, JSON string with fields to update).

```json
{
  "base_id": "PREENCHER",
  "table": "PREENCHER",
  "record_id": "PREENCHER",
  "fields": "PREENCHER"
}
```

### `delete_record`

Delete a record by ID. Parameters: base_id (required), table (required), record_id (required).

```json
{
  "base_id": "PREENCHER",
  "table": "PREENCHER",
  "record_id": "PREENCHER"
}
```

## Apify Actors (`apify`)

JSON para preencher na credencial **Jarvis · Apify Actors** (substitua cada valor):

```json
{
  "auth_token": "PREENCHER"
}
```

Ponte MCP: https://mcp.apify.com. Os argumentos seguem o schema publicado pelo provedor.

- `search-actors`
- `fetch-actor-details`
- `call-actor`
- `get-actor-run`
- `get-actor-output`
- `search-apify-docs`
- `fetch-apify-docs`
- `apify--rag-web-browser`

## Asana (`asana`)

JSON para preencher na credencial **Jarvis · Asana** (substitua cada valor):

```json
{
  "asana_pat": "PREENCHER"
}
```

### `list_workspaces`

List all Asana workspaces the token has access to. No parameters. Use this first when you need a workspace gid for other calls.

```json
{}
```

### `list_projects`

List projects in a workspace. Parameters: workspace (required, workspace gid), archived (optional 'true'/'false', default 'false'), limit (optional, default 20, max 100).

```json
{
  "workspace": "PREENCHER",
  "archived": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_project`

Get full details of a project including notes, owner, due date, members. Parameters: project (required, project gid).

```json
{
  "project": "PREENCHER"
}
```

### `list_sections`

List sections (columns) of a project. Parameters: project (required, project gid).

```json
{
  "project": "PREENCHER"
}
```

### `list_tasks`

List tasks with ONE of these filters: project (by project gid), section (by section gid), OR assignee+workspace (use 'me' for the current user). Parameters: project, section, assignee, workspace, limit (default 20), completed_since (ISO 8601, e.g. 'now' for only open tasks).

```json
{
  "project": "PREENCHER",
  "section": "PREENCHER",
  "assignee": "PREENCHER",
  "workspace": "PREENCHER",
  "limit": "PREENCHER",
  "completed_since": "PREENCHER"
}
```

### `get_task`

Get full task details: name, notes, assignee, due date, projects, tags, subtasks. Parameters: task (required, task gid).

```json
{
  "task": "PREENCHER"
}
```

### `create_task`

Create a new task. Parameters: name (required), workspace OR project (at least one required), notes (optional), assignee (optional, gid or 'me'), due_on (optional, YYYY-MM-DD).

```json
{
  "name": "PREENCHER",
  "workspace": "PREENCHER",
  "project": "PREENCHER",
  "notes": "PREENCHER",
  "assignee": "PREENCHER",
  "due_on": "PREENCHER"
}
```

### `update_task`

Update an existing task. Parameters: task (required, task gid), plus at least one of: name, notes, assignee, due_on (YYYY-MM-DD).

```json
{
  "task": "PREENCHER",
  "name": "PREENCHER",
  "notes": "PREENCHER",
  "assignee": "PREENCHER",
  "due_on": "PREENCHER"
}
```

### `complete_task`

Mark a task as completed. Parameters: task (required, task gid).

```json
{
  "task": "PREENCHER"
}
```

### `add_comment_to_task`

Add a comment (story) to a task. Parameters: task (required, task gid), text (required, comment body).

```json
{
  "task": "PREENCHER",
  "text": "PREENCHER"
}
```

### `list_comments`

List comments on a task (stories of type 'comment'). Parameters: task (required, task gid), include_system (optional 'true'/'false', default false — set true to include automated events like assignments).

```json
{
  "task": "PREENCHER",
  "include_system": "PREENCHER"
}
```

### `list_subtasks`

List subtasks of a parent task. Parameters: task (required, parent task gid), limit (optional, default 50, max 100).

```json
{
  "task": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `create_subtask`

Create a subtask under a parent task. Parameters: task (required, parent task gid), name (required), notes (optional), assignee (optional, gid or 'me'), due_on (optional, YYYY-MM-DD).

```json
{
  "task": "PREENCHER",
  "name": "PREENCHER",
  "notes": "PREENCHER",
  "assignee": "PREENCHER",
  "due_on": "PREENCHER"
}
```

### `move_task_to_section`

Move a task into a specific section of a project (Kanban-style column change). Parameters: task (required, task gid), section (required, target section gid). Use list_sections to find section gids.

```json
{
  "task": "PREENCHER",
  "section": "PREENCHER"
}
```

### `search_users`

Typeahead search for users in a workspace by name or email fragment. Use this to find a user's gid before assigning a task. Parameters: workspace (required, workspace gid), query (required, name/email fragment), count (optional, default 10, max 100).

```json
{
  "workspace": "PREENCHER",
  "query": "PREENCHER",
  "count": "PREENCHER"
}
```

### `search_tasks`

Typeahead search for tasks in a workspace by name fragment. Use this when the user refers to a task by partial name and you need the gid. Parameters: workspace (required, workspace gid), query (required, name fragment), count (optional, default 10, max 100).

```json
{
  "workspace": "PREENCHER",
  "query": "PREENCHER",
  "count": "PREENCHER"
}
```

## BFL FLUX Image Generation (`bfl-flux`)

JSON para preencher na credencial **Jarvis · BFL FLUX Image Generation** (substitua cada valor):

```json
{
  "bfl_api_key": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `generate_image`

Generate a single image with BFL FLUX 2. Covers text-to-image AND image editing: pass file_ref to edit a user-uploaded photo, OR image_url to edit a previously generated image. Returns the image inline if ready within ~25s, otherwise returns a polling_url and you must call wait_for_image to keep waiting. Parameters: prompt (required, what to generate or how to edit), model (optional: flux-2-pro [default], flux-2-max [highest quality], flux-2-flex [best typography], flux-2-klein-9b, flux-2-klein-4b [cheapest+fastest], flux-2-pro-preview, flux-2-klein-9b-preview), width/height (optional, default 1024, min 64), file_ref (optional, file-bridge id of a user-uploaded photo to edit), image_url (optional, URL of a previous BFL generation to edit/vary), seed (optional integer for reproducibility).

```json
{
  "prompt": "PREENCHER",
  "model": "PREENCHER",
  "width": "PREENCHER",
  "height": "PREENCHER",
  "file_ref": "PREENCHER",
  "image_url": "PREENCHER",
  "seed": "PREENCHER"
}
```

### `wait_for_image`

Wait up to ~25 seconds for a BFL FLUX generation that did not finish in the initial generate_image call. Returns the finished image when ready, or a 'still generating, call again' message if not yet ready. Keep calling with the same polling_url until you get the file. Most generations finish on the first attempt; FLUX 2 Max may need 1-2 wait_for_image calls. Parameters: polling_url (required, the URL returned by generate_image when status was pending).

```json
{
  "polling_url": "PREENCHER"
}
```

### `get_credits`

Return the remaining BFL credit balance for the configured API key. 1 credit = $0.01 USD. Typical costs: klein-4b ~1.4 credits/image, pro ~6-8 credits/image, max ~12-15 credits/image. Takes no parameters.

```json
{}
```

## CalDAV Calendar (`caldav-calendar`)

JSON para preencher na credencial **Jarvis · CalDAV Calendar** (substitua cada valor):

```json
{
  "caldav_url": "PREENCHER",
  "caldav_username": "PREENCHER",
  "caldav_password": "PREENCHER"
}
```

### `list_calendars`

List all available calendars on the CalDAV server. Returns calendar names and IDs.

```json
{}
```

### `list_events`

List events from a calendar. Optionally filter by date range. Parameters: calendar (calendar ID from list_calendars), start (optional, ISO 8601 date like 2026-03-14T00:00:00Z), end (optional, ISO 8601 date)

```json
{
  "calendar": "PREENCHER",
  "start": "PREENCHER",
  "end": "PREENCHER"
}
```

### `create_event`

Create a new calendar event. Parameters: calendar (calendar ID), title (event title), start (ISO 8601 datetime), end (ISO 8601 datetime), description (optional), location (optional)

```json
{
  "calendar": "PREENCHER",
  "title": "PREENCHER",
  "start": "PREENCHER",
  "end": "PREENCHER",
  "description": "PREENCHER",
  "location": "PREENCHER"
}
```

### `update_event`

Update an existing calendar event. Fetches the event first, merges changes, and saves. Parameters: calendar (calendar ID), event_uid (UID from list_events), title (optional), start (optional, ISO 8601), end (optional, ISO 8601), description (optional), location (optional)

```json
{
  "calendar": "PREENCHER",
  "event_uid": "PREENCHER",
  "title": "PREENCHER",
  "start": "PREENCHER",
  "end": "PREENCHER",
  "description": "PREENCHER",
  "location": "PREENCHER"
}
```

### `delete_event`

Delete a calendar event. Parameters: calendar (calendar ID), event_uid (UID from list_events)

```json
{
  "calendar": "PREENCHER",
  "event_uid": "PREENCHER"
}
```

## Config Backup & Restore (`config-backup`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

**Escopo adaptado:** o armazenamento deste conector é isolado. Ele não acessa o banco central nem as credenciais de outros conectores. O backup completo do Jarvis é feito pelo script de implantação.

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `create_backup`

Create a JSON backup of n8n-claw configuration and return a download link. Parameters: name (backup file name or empty string for auto-generated), scope (core=config only, full=everything including memory/conversations/knowledge graph, custom=specify tables — default is full), tables (comma-separated table names, only used when scope is custom. Available tables: soul, claw_agents, user_profiles, tools_config, projects, mcp_registry, template_credentials, memory_long, memory_daily, conversations, reminders, scheduled_actions, heartbeat_config, tasks, kg_entities, kg_relations)

```json
{
  "name": "PREENCHER",
  "scope": "PREENCHER",
  "tables": "PREENCHER"
}
```

### `show_backup`

View contents of a backup file without restoring. Parameters: url (URL to the backup JSON file, required), table (show only this specific table or empty string for overview)

```json
{
  "url": "PREENCHER",
  "table": "PREENCHER"
}
```

### `restore_backup`

Restore configuration from a backup file URL. IMPORTANT: By default, template_credentials and tools_config are SKIPPED because they contain API keys. Use include_credentials=true to restore them too. Parameters: url (URL to the backup JSON file, required), tables (comma-separated list of tables to restore or empty string for all), mode (upsert=merge with existing data, replace=delete existing then insert — default upsert), include_credentials (true to also restore template_credentials and tools_config which contain API keys, or empty string to skip them for security)

```json
{
  "url": "PREENCHER",
  "tables": "PREENCHER",
  "mode": "PREENCHER",
  "include_credentials": "PREENCHER"
}
```

## Confluence Cloud (`confluence`)

JSON para preencher na credencial **Jarvis · Confluence Cloud** (substitua cada valor):

```json
{
  "atlassian_email": "PREENCHER",
  "atlassian_api_token": "PREENCHER",
  "atlassian_site": "PREENCHER"
}
```

### `list_spaces`

List all Confluence spaces (id, key, name, type). No parameters. Use this first to find a space_id for other operations.

```json
{}
```

### `list_pages_in_space`

List pages and blogposts in a space. Parameters: space_id (required, numeric id from list_spaces), limit (optional), content_type (optional: page or blogpost to narrow).

```json
{
  "space_id": "PREENCHER",
  "limit": "PREENCHER",
  "space_key": "PREENCHER",
  "content_type": "PREENCHER"
}
```

### `search_pages`

Search Confluence with CQL or plain text. Pages and blogposts are both searched by default; narrow with content_type. Plain text is auto-wrapped, real CQL (containing = or ~) is passed through unchanged. Parameters: query (required), limit (optional), content_type (optional). IMPORTANT for questions about recent content: pass order=newest, otherwise relevance ranking can hide the newest pages behind older ones.

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER",
  "content_type": "PREENCHER",
  "order": "PREENCHER"
}
```

### `get_page`

Fetch a page or blogpost by id, with body, version and space. Blogposts are detected automatically. Live Docs are returned as readable text. The Version number shown can be passed to update_page as expected_version for a safe edit. Parameters: page_id (required), content_type (optional: page or blogpost). Set format=storage to get the raw markup instead of readable text, which is what you need before editing a page.

```json
{
  "page_id": "PREENCHER",
  "content_type": "PREENCHER",
  "format": "PREENCHER"
}
```

### `get_page_by_title`

Find a page or blogpost by exact title. Searches pages first, then blogposts. Parameters: title (required), space_id (optional), content_type (optional).

```json
{
  "title": "PREENCHER",
  "space_id": "PREENCHER",
  "content_type": "PREENCHER"
}
```

### `list_children`

List child pages of a page. Blogposts have no children and are reported as such. Parameters: page_id (required), limit (optional).

```json
{
  "page_id": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `create_page`

Create a new page or blogpost. Body MUST be storage-format HTML, e.g. '<p>Hello</p><h2>Section</h2>'. Set content_type to blogpost to create a blog entry. Parameters: space_id (required), title (required), body (required), parent_id (optional, pages only), content_type (optional).

```json
{
  "space_id": "PREENCHER",
  "title": "PREENCHER",
  "body": "PREENCHER",
  "parent_id": "PREENCHER",
  "content": "PREENCHER",
  "space_key": "PREENCHER",
  "content_type": "PREENCHER"
}
```

### `update_page`

Update title and/or body of a page or blogpost by REPLACING the content. To add an entry to a list or a row to a table, use append_to_page instead: it does not rewrite the page and cannot lose existing content. Body must be storage-format HTML. The version is bumped automatically. Best practice: call get_page first and pass its Version as expected_version - the update is then refused instead of silently overwriting someone else's edit. Content that exists only in ADF format (no storage representation) is refused rather than wiped. Sending only a title keeps the existing body. Parameters: page_id (required), title (optional), body (optional), expected_version (optional), change_note (optional), content_type (optional). A new body that is much shorter than the current one is refused, because that usually means formatting or other entries were lost; pass allow_shrink=true if it is intended. An update that would drop existing structure such as column widths or macros is refused; pass allow_format_loss=true if that is intended.

```json
{
  "page_id": "PREENCHER",
  "title": "PREENCHER",
  "body": "PREENCHER",
  "content": "PREENCHER",
  "expected_version": "PREENCHER",
  "change_note": "PREENCHER",
  "content_type": "PREENCHER",
  "allow_shrink": "PREENCHER",
  "allow_format_loss": "PREENCHER"
}
```

### `delete_page`

Delete a page or blogpost by id (moves it to the trash). Blogposts are detected automatically. Parameters: page_id (required), content_type (optional).

```json
{
  "page_id": "PREENCHER",
  "content_type": "PREENCHER"
}
```

### `add_comment_to_page`

Add a comment to a page or blogpost. Works on Live Docs too. Parameters: page_id (required), text (required).

```json
{
  "page_id": "PREENCHER",
  "text": "PREENCHER"
}
```

### `list_comments_on_page`

List comments on a page or blogpost. Parameters: page_id (required).

```json
{
  "page_id": "PREENCHER"
}
```

### `add_label_to_page`

Add a label to a page for categorization. Label names should be lowercase with hyphens (e.g. 'meeting-notes'). Parameters: page_id (required), label (required).

```json
{
  "page_id": "PREENCHER",
  "label": "PREENCHER"
}
```

### `list_labels_on_page`

List labels on a page or blogpost. Parameters: page_id (required).

```json
{
  "page_id": "PREENCHER"
}
```

### `search_by_label`

Find content carrying a label. Returns pages and blogposts. Parameters: label (required), limit (optional), content_type (optional). Pass order=newest to see the most recent content first.

```json
{
  "label": "PREENCHER",
  "limit": "PREENCHER",
  "content_type": "PREENCHER",
  "order": "PREENCHER"
}
```

### `append_to_page`

Append content to an existing page or blogpost WITHOUT rewriting it. This is the right tool for adding an entry to a list or a row to a table, for example a feedback log. Only the new part is sent, the existing content is untouched, so nothing can get lost and the page keeps its formatting. Use update_page only when existing content really has to change. Parameters: page_id (required), cells (JSON array of strings for a new table row, escaping is handled for you), html (alternative: a storage-format snippet such as a paragraph), location (optional: table appends into the last table, end appends at the bottom of the page), change_note (optional), expected_version (optional), content_type (optional).

```json
{
  "page_id": "PREENCHER",
  "cells": "PREENCHER",
  "html": "PREENCHER",
  "location": "PREENCHER",
  "change_note": "PREENCHER",
  "expected_version": "PREENCHER",
  "content_type": "PREENCHER"
}
```

## Country Info (`country-info`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_country_info`

Get detailed information about a country. Parameter: query (country name like 'Germany' or ISO code like 'DE')

```json
{
  "query": "PREENCHER"
}
```

## Crypto Prices (`crypto-prices`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_crypto_price`

Get current cryptocurrency price, 24h change, and market cap. Parameters: coin (name or ID like 'bitcoin', 'ethereum', 'solana'), currency (optional, target currency like 'eur', 'usd', default 'eur')

```json
{
  "coin": "PREENCHER",
  "currency": "PREENCHER"
}
```

## DataForSEO (`dataforseo`)

JSON para preencher na credencial **Jarvis · DataForSEO** (substitua cada valor):

```json
{
  "dataforseo_login": "PREENCHER",
  "dataforseo_password": "PREENCHER"
}
```

### `dfs_account_balance`

Show DataForSEO account balance, lifetime spend, and timezone. Free, use first to check budget.

```json
{}
```

### `dfs_serp_google_organic`

Google organic SERP for a keyword. Common location_codes: 2276=Germany, 2840=USA, 2826=UK, 2040=Austria, 2756=Switzerland. Common language_codes: de, en, fr, it, es. ~$0.002 per call.

```json
{
  "keyword": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "depth": "PREENCHER"
}
```

### `dfs_serp_google_organic_advanced`

Google SERP advanced (with featured snippets, Knowledge Graph, People Also Ask, sitelinks). ~$0.002 per call.

```json
{
  "keyword": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "depth": "PREENCHER"
}
```

### `dfs_search_volume`

Monthly search volume + CPC + competition for a list of keywords. Pass keywords as comma-separated list. ~$0.075 per call regardless of keyword count.

```json
{
  "keywords": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER"
}
```

### `dfs_keywords_for_keywords`

Find related keywords for a seed (Google Ads). Returns related keywords with volume, CPC, competition. ~$0.075 per call.

```json
{
  "keywords": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `dfs_google_trends`

Google Trends interest-over-time for up to 5 keywords (comma-separated). Optional date range YYYY-MM-DD.

```json
{
  "keywords": "PREENCHER",
  "location_code": "PREENCHER",
  "date_from": "PREENCHER",
  "date_to": "PREENCHER"
}
```

### `dfs_keyword_overview`

Full SEO profile of a single keyword: search volume, KD, CPC, intent, SERP features. ~$0.01 per call.

```json
{
  "keyword": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER"
}
```

### `dfs_keyword_ideas`

Semantic keyword ideas from a seed keyword (DataForSEO Labs). ~$0.011 per call.

```json
{
  "keyword": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `dfs_keyword_difficulty`

Bulk keyword difficulty (0-100) for a list of keywords. ~$0.01 per call.

```json
{
  "keywords": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER"
}
```

### `dfs_ranked_keywords`

Keywords a domain ranks for organically: position, search volume, traffic estimate. Pass domain (no http://, no path) as 'target'. ~$0.0105 per call.

```json
{
  "target": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `dfs_competitors_domain`

Top competing domains for a target domain in the SERPs. ~$0.0105 per call.

```json
{
  "target": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `dfs_backlinks_summary`

Backlink profile overview for a domain. NOTE: Requires Backlinks API subscription on DataForSEO; without it returns 40204 access-denied error.

```json
{
  "target": "PREENCHER"
}
```

### `dfs_backlinks_referring_domains`

List of referring domains for a target. NOTE: Requires Backlinks API subscription.

```json
{
  "target": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `dfs_backlinks_anchors`

Anchor text distribution for a domain's backlinks. NOTE: Requires Backlinks API subscription.

```json
{
  "target": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `dfs_onpage_instant`

Live single-page audit: HTTP status, meta tags, on-page checks. Pass full URL with protocol. ~$0.000125 per call.

```json
{
  "url": "PREENCHER"
}
```

### `dfs_lighthouse_audit`

Lighthouse audit (Performance, Accessibility, SEO, Best Practices, PWA). Set for_mobile=false for desktop. ~$0.00425 per call.

```json
{
  "url": "PREENCHER",
  "for_mobile": "PREENCHER"
}
```

### `dfs_domain_technologies`

Detected tech stack of a domain (CMS, frameworks, analytics, hosting, etc.). ~$0.01 per call.

```json
{
  "target": "PREENCHER"
}
```

### `dfs_my_business_info`

Google My Business listings for a search query in a location. Returns name, address, rating, categories, hours. ~$0.0054 per call.

```json
{
  "keyword": "PREENCHER",
  "location_code": "PREENCHER",
  "language_code": "PREENCHER",
  "depth": "PREENCHER"
}
```

## DeepL Translate (`deepl-translate`)

JSON para preencher na credencial **Jarvis · DeepL Translate** (substitua cada valor):

```json
{
  "deepl_api_key": "PREENCHER"
}
```

### `translate_text`

Translate text to a target language using DeepL. Parameters: text (the text to translate, required), target_lang (target language code like 'DE', 'EN', 'FR', 'ES', 'IT', 'JA', 'ZH', required), source_lang (source language code, optional — auto-detected if omitted)

```json
{
  "text": "PREENCHER",
  "target_lang": "PREENCHER",
  "source_lang": "PREENCHER"
}
```

### `detect_language`

Detect the language of a given text using DeepL. Parameter: text (the text to analyze, required)

```json
{
  "text": "PREENCHER"
}
```

## DeepWiki (`deepwiki`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

Ponte MCP: https://mcp.deepwiki.com/mcp. Os argumentos seguem o schema publicado pelo provedor.

- `read_wiki_structure`
- `read_wiki_contents`
- `ask_question`

## Deutsche Bahn (`deutsche-bahn`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_station`

Search for a train station by name. Returns station names and IDs. Parameter: query (station name to search for, e.g. 'Berlin Hbf')

```json
{
  "query": "PREENCHER"
}
```

### `get_departures`

Get upcoming departures from a train station. Accepts station name (auto-resolved) or ID. Parameters: station (station name or ID, e.g. 'Essen Hbf'), duration (optional, minutes to look ahead, default 60)

```json
{
  "station": "PREENCHER",
  "duration": "PREENCHER"
}
```

### `get_arrivals`

Get upcoming arrivals at a train station. Accepts station name (auto-resolved) or ID. Parameters: station (station name or ID, e.g. 'München Hbf'), duration (optional, minutes to look ahead, default 60)

```json
{
  "station": "PREENCHER",
  "duration": "PREENCHER"
}
```

### `search_journey`

Search for train connections between two stations. Accepts station names (auto-resolved) or IDs. Parameters: from (origin station name or ID), to (destination station name or ID), departure (optional, ISO 8601 datetime), results (optional, number of connections, default 3)

```json
{
  "from": "PREENCHER",
  "to": "PREENCHER",
  "departure": "PREENCHER",
  "results": "PREENCHER"
}
```

## Dictionary (`dictionary`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `define_word`

Look up English word definitions, phonetics, and examples. Parameter: word (the English word to look up)

```json
{
  "word": "PREENCHER"
}
```

## DZT Germany Tourism (`dzt-germany-tourism`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_pois_by_criteria`

Search permanent Points of Interest in Germany: restaurants, museums, castles, wineries, landmarks, parks etc. Use for places that exist year-round. Do NOT use for time-bound events. Note: Restaurant data sparse for major cities — use postal_code or near_point instead of locality. Parameters: name (POI name), keywords (comma-separated, e.g. 'art,history'), type (schema.org type e.g. Museum, Restaurant, TouristAttraction, LandmarksOrHistoricalBuildings, FoodEstablishment), locality (city — unreliable for major cities), region (e.g. Schwarzwald, Bayern), postal_code, near_point (format: 'km,lat,lon' e.g. '10km,48.137,11.576')

```json
{
  "name": "PREENCHER",
  "keywords": "PREENCHER",
  "type": "PREENCHER",
  "locality": "PREENCHER",
  "region": "PREENCHER",
  "postal_code": "PREENCHER",
  "near_point": "PREENCHER"
}
```

### `get_events_by_criteria`

Search upcoming tourist events and cultural activities in Germany (festivals, food markets, guided tours, wine tastings). Use for time-bound events. Do NOT use for permanent POIs. Note: locality filter unreliable for major cities — omit and use region instead. Parameters: keywords (REQUIRED, comma-separated German or English, e.g. 'Kulinarik,Food', 'Wein,Weinprobe', 'Musik,Konzert'), dateRangeStart (REQUIRED, YYYY-MM-DD, today or future), name (event name), locality (city), dateRangeEnd (YYYY-MM-DD), region (e.g. Bayern, Pfalz)

```json
{
  "keywords": "PREENCHER",
  "dateRangeStart": "PREENCHER",
  "name": "PREENCHER",
  "locality": "PREENCHER",
  "dateRangeEnd": "PREENCHER",
  "region": "PREENCHER"
}
```

### `get_trails_by_criteria`

Search hiking trails, cycling routes and walking tours in Germany. Returns routes with distance, difficulty and waypoints. By default only circular routes are returned. Set is_circular to false for all trail types. Parameters: name (trail name), keywords (e.g. 'downhill,lake view'), difficulty (exactly: Leicht, Mittel, or Schwer), max_length_km (number), region (e.g. Schwarzwald, Eifel), is_circular (true/false, default true), near_point (format: 'km,lat,lon')

```json
{
  "name": "PREENCHER",
  "keywords": "PREENCHER",
  "difficulty": "PREENCHER",
  "max_length_km": "PREENCHER",
  "region": "PREENCHER",
  "is_circular": "PREENCHER",
  "near_point": "PREENCHER"
}
```

### `get_entity_details`

Get full details for a tourism entity by URI. Use a URI from a previous get_pois_by_criteria, get_events_by_criteria, or get_trails_by_criteria result. Parameters: uri (REQUIRED, the entity URI), language (two-letter code, default 'de')

```json
{
  "uri": "PREENCHER",
  "language": "PREENCHER"
}
```

## Email (IMAP/SMTP) (`email-imap-smtp`)

JSON para preencher na credencial **Jarvis · Email (IMAP/SMTP)** (substitua cada valor):

```json
{
  "email_user": "PREENCHER",
  "email_password": "PREENCHER",
  "imap_host": "PREENCHER",
  "smtp_host": "PREENCHER"
}
```

Ponte IMAP/SMTP interna incluída. Cadastre origens como `imaps://imap.exemplo.com:993` e `smtp://smtp.exemplo.com:587` (ou `smtps://smtp.exemplo.com:465`) na credencial. TLS é obrigatório. O provedor pode exigir senha de aplicativo.

### `read_emails`

Read emails from inbox. Parameters: folder (default INBOX), limit (default 10), since (date like 2026-03-01, emails ON or AFTER this date), before (date like 2026-03-02, emails BEFORE this date, use since+before together for a specific day), unseen (true=only unread), from (filter by sender email)

```json
{
  "folder": "PREENCHER",
  "limit": "PREENCHER",
  "since": "PREENCHER",
  "before": "PREENCHER",
  "unseen": "PREENCHER",
  "from": "PREENCHER"
}
```

### `send_email`

Send an email. Parameters: to (recipient email, required), subject (email subject, required), body (plain text body, required), html (HTML body, optional)

```json
{
  "to": "PREENCHER",
  "subject": "PREENCHER",
  "body": "PREENCHER",
  "html": "PREENCHER"
}
```

## Exchange Rates (`exchange-rates`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `convert_currency`

Convert currencies using live exchange rates. Parameters: from (source currency code, default EUR), to (target currency code, default USD), amount (amount to convert, default 1)

```json
{
  "from": "PREENCHER",
  "to": "PREENCHER",
  "amount": "PREENCHER"
}
```

## Finnhub Stocks (`finnhub`)

JSON para preencher na credencial **Jarvis · Finnhub Stocks** (substitua cada valor):

```json
{
  "finnhub_api_key": "PREENCHER"
}
```

### `get_quote`

Current stock price and daily change for a ticker symbol. Parameters: symbol (required, e.g. AAPL, MSFT, TSLA). Use search_symbol first if you only know the company name.

```json
{
  "symbol": "PREENCHER"
}
```

### `get_company_profile`

Company profile: industry, market cap, exchange, IPO date, website, logo. Parameters: symbol (required).

```json
{
  "symbol": "PREENCHER"
}
```

### `get_company_news`

Recent news articles about a specific company. Parameters: symbol (required), days (optional, default 7, max 30), limit (optional, default 5, max 15).

```json
{
  "symbol": "PREENCHER",
  "days": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `search_symbol`

Find ticker symbols by company name. Use when the user refers to a company by name (e.g. "Apple", "Tesla") and you need the symbol ("AAPL", "TSLA") for other tools. Parameters: query (required).

```json
{
  "query": "PREENCHER"
}
```

### `get_market_status`

Check if a stock exchange is currently open. Parameters: exchange (optional, default US; also supports L, T, HK, etc.).

```json
{
  "exchange": "PREENCHER"
}
```

## Fitness Buddy (`fitness-buddy`)

JSON para preencher na credencial **Jarvis · Fitness Buddy** (substitua cada valor):

```json
{
  "openai_api_key": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `fitness_profile`

Manage the user's fitness profile via STEP-BY-STEP onboarding. CRITICAL CALL CONVENTION: this tool's external schema marks all parameters as 'required' (n8n quirk) — you MUST include EVERY parameter in every call, using empty string "" for fields the user has not yet provided. The skill internally skips empty strings, saves whatever is non-empty, and replies with the next single question. Workflow: (1) initial call with sub_action='setup' and ALL other 13 fields = "" → skill replies with the first question (e.g. 'What's your sex? m/f/x') → forward verbatim to user. (2) user answers 'männlich' → call again with sub_action='setup', sex='m', and the remaining 12 fields still as "" → skill saves sex, replies with the next question. (3) repeat until skill replies 'All set!'. NEVER ask the questionnaire yourself. Allowed values — sex: m/f/x; activity_level: sedentary|light|moderate|active|very_active; goal: lose_weight|maintain|gain_muscle|recomp|endurance. Other sub_actions: 'update' modifies existing fields (same empty-string-for-unknowns rule), 'get' returns current profile (still pass empty strings for unused fields).

```json
{
  "sub_action": "PREENCHER",
  "sex": "PREENCHER",
  "birthdate": "PREENCHER",
  "height_cm": "PREENCHER",
  "weight_kg_baseline": "PREENCHER",
  "activity_level": "PREENCHER",
  "goal": "PREENCHER",
  "target_weight_kg": "PREENCHER",
  "target_date": "PREENCHER",
  "allergies": "PREENCHER",
  "dietary_restrictions": "PREENCHER",
  "training_days_per_week": "PREENCHER",
  "daily_kcal_override": "PREENCHER",
  "notes": "PREENCHER"
}
```

### `log_meal`

Log a meal. sub_action='from_text' parses a description (e.g. '100g oatmeal, 200ml milk, 1 banana'); 'from_voice' is identical (text from voice transcript); 'from_photo' uses the photo file_ref to call OpenAI vision and estimate items+grams; 'from_barcode' looks up by EAN; 'from_memory' logs a saved meal_memory_id; 'edit' modifies notes/meal_type of meal_id; 'delete' removes meal_id; 'clear_day' wipes all meals for a date (requires confirm=true). Always include meal_type (breakfast/lunch/dinner/snack).

```json
{
  "sub_action": "PREENCHER",
  "meal_type": "PREENCHER",
  "text": "PREENCHER",
  "file_ref": "PREENCHER",
  "barcode": "PREENCHER",
  "grams": "PREENCHER",
  "meal_memory_id": "PREENCHER",
  "meal_id": "PREENCHER",
  "date": "PREENCHER",
  "confirm": "PREENCHER",
  "logged_at": "PREENCHER",
  "notes": "PREENCHER"
}
```

### `meal_memory`

Manage frequently eaten meals. sub_action='list' shows top-20 saved meals with usage count; 'save' stores a previously logged meal_id under a name (e.g. 'My standard breakfast'); 'delete' removes meal_memory_id.

```json
{
  "sub_action": "PREENCHER",
  "name": "PREENCHER",
  "meal_id": "PREENCHER",
  "meal_memory_id": "PREENCHER"
}
```

### `suggest_meal`

Suggest 3 next-meal options that fit the remaining macro budget for today. Respects allergies, dietary restrictions, and prefers user favorites from meal_memory.

```json
{}
```

### `log_workout`

Log a workout. sub_action='log' (default) saves a new workout, auto-extracting exercise_type/duration_min/intensity from text/voice if provided. 'edit' updates workout_id; 'delete' removes workout_id. Pass text (e.g. '30 min jog medium intensity') OR explicit fields (exercise_type, duration_min, intensity).

```json
{
  "sub_action": "PREENCHER",
  "text": "PREENCHER",
  "exercise_type": "PREENCHER",
  "duration_min": "PREENCHER",
  "intensity": "PREENCHER",
  "distance_km": "PREENCHER",
  "perceived_exertion": "PREENCHER",
  "performed_at": "PREENCHER",
  "workout_id": "PREENCHER",
  "notes": "PREENCHER"
}
```

### `log_body`

Log body measurements (weight, body fat %, circumferences) and view trends. sub_action='log' saves a measurement; 'list' shows entries from last N days; 'trend' computes change between first and last entry over the window.

```json
{
  "sub_action": "PREENCHER",
  "weight_kg": "PREENCHER",
  "body_fat_pct": "PREENCHER",
  "muscle_mass_kg": "PREENCHER",
  "waist_cm": "PREENCHER",
  "chest_cm": "PREENCHER",
  "hip_cm": "PREENCHER",
  "thigh_cm": "PREENCHER",
  "arm_cm": "PREENCHER",
  "measured_at": "PREENCHER",
  "days": "PREENCHER",
  "notes": "PREENCHER"
}
```

### `log_hydration`

Log water intake and check progress. sub_action='log' adds volume_ml; 'today' shows progress vs target; 'set_target' updates daily target_ml in the profile.

```json
{
  "sub_action": "PREENCHER",
  "volume_ml": "PREENCHER",
  "beverage_type": "PREENCHER",
  "target_ml": "PREENCHER",
  "logged_at": "PREENCHER"
}
```

### `goals`

Manage fitness goals. sub_action='set' creates a goal (goal_type: weight, body_fat, workout_frequency, distance, strength, habit, streak); 'list' shows active goals with progress; 'archive' marks goal_id done.

```json
{
  "sub_action": "PREENCHER",
  "goal_type": "PREENCHER",
  "target_value": "PREENCHER",
  "target_unit": "PREENCHER",
  "current_value": "PREENCHER",
  "deadline": "PREENCHER",
  "goal_id": "PREENCHER",
  "status": "PREENCHER"
}
```

### `summary`

Aggregated fitness report. sub_action='today' shows today's calories vs target, macros, workouts, water, and active streak; 'week' or 'month' aggregate the period.

```json
{
  "sub_action": "PREENCHER"
}
```

### `training_plan`

Manage multi-week training plans. sub_action='generate_custom' uses LLM + wger.de exercise database (anonymous /exerciseinfo/ endpoint, ~80 real exercises with IDs) to create a periodized plan tailored to profile and goal (params: goal, weeks, days_per_week, equipment); 'today' returns today's planned session; 'get_active' returns active plan summary; 'complete_session' marks session_id complete; 'adjust' notes adjustment (V2 will restructure). NOTE: 'import_template' / 'list_templates' for wger public templates require auth and are not available — use generate_custom instead.

```json
{
  "sub_action": "PREENCHER",
  "goal": "PREENCHER",
  "weeks": "PREENCHER",
  "days_per_week": "PREENCHER",
  "equipment": "PREENCHER",
  "template_id": "PREENCHER",
  "session_id": "PREENCHER",
  "plan_id": "PREENCHER",
  "adjustment_note": "PREENCHER",
  "notes": "PREENCHER"
}
```

### `reminders`

Set up recurring fitness reminders fired by the heartbeat. sub_action='setup' adds presets (preset='morning_meal' / 'evening_summary' / 'weekly_report' / 'all'); 'list' shows configured reminders; 'disable' turns off reminder_id.

```json
{
  "sub_action": "PREENCHER",
  "preset": "PREENCHER",
  "timezone": "PREENCHER",
  "reminder_id": "PREENCHER",
  "chat_id": "PREENCHER"
}
```

### `insights`

Pattern detection over the last 30 days of logs. sub_action='analyze' runs LLM analysis on aggregated stats and writes 3-5 insights to memory_long (category=insight, entity_name=fitness) for the agent to recall in future turns; 'list' shows the latest insights.

```json
{
  "sub_action": "PREENCHER"
}
```

### `export`

Export logs as CSV. type='meals' / 'workouts' / 'body' / 'hydration'. since/until are YYYY-MM-DD (default last 30 days). The CSV is uploaded to the file bridge and a file_ref is returned for the agent to send as a Telegram document.

```json
{
  "type": "PREENCHER",
  "since": "PREENCHER",
  "until": "PREENCHER"
}
```

### `nutrition_lookup`

Stand-alone OpenFoodFacts nutrition lookup without logging. sub_action='by_name' searches by product name (top N results); 'by_barcode' fetches a product by EAN.

```json
{
  "sub_action": "PREENCHER",
  "query": "PREENCHER",
  "barcode": "PREENCHER",
  "limit": "PREENCHER"
}
```

## GENESIS-Online (Destatis) (`genesis-destatis`)

JSON para preencher na credencial **Jarvis · GENESIS-Online (Destatis)** (substitua cada valor):

```json
{
  "genesis_token": "PREENCHER"
}
```

### `genesis_search`

Free-text search across GENESIS-Online (German official statistics) for tables, statistics, variables, time series and cubes. Returns codes (e.g. '12711-0001') that you can pass to genesis_table_metadata or genesis_get_table. NOTE: German search terms often return empty results — use language='en' with English terms (e.g. 'migration' instead of 'Wanderung') for best results.

```json
{
  "term": "PREENCHER",
  "category": "PREENCHER",
  "pagelength": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_list_tables`

List GENESIS tables filtered by code prefix. Examples: '12711*' for migration tables, '61*' for prices, '21*' for education, '23*' for health. Use '*' for everything.

```json
{
  "selection": "PREENCHER",
  "pagelength": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_list_statistics`

Browse top-level GENESIS statistics (themes). Each statistic has a numeric code (e.g. '12711' for Wanderungsstatistik). Use the codes here as a prefix for genesis_list_tables.

```json
{
  "selection": "PREENCHER",
  "pagelength": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_list_variables`

List GENESIS variables (Merkmale) such as JAHR (year), NAT (nationality), GES (sex), DLAND (federal state). Optionally filter by code prefix or by type (klassifizierend, raeumlich, zeitlich, sachlich, insgesamt).

```json
{
  "selection": "PREENCHER",
  "type": "PREENCHER",
  "pagelength": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_list_values`

List concrete value keys of a GENESIS variable. E.g. name='NAT' returns ['NATD'=Deutsche, 'NATA'=Auslaender]; name='DLAND' returns federal-state codes. Use these keys as classifyingkey/regionalkey in genesis_get_table.

```json
{
  "name": "PREENCHER",
  "pagelength": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_table_metadata`

Get the full structure of a GENESIS table: variables in head/columns/rows, time range, last update timestamp. Always call this BEFORE genesis_get_table to know which classifying variables exist and how to filter.

```json
{
  "name": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_get_table`

Fetch the actual data of a GENESIS table as a CSV-like preview. Always narrow the result with startyear/endyear and filter variables — full tables are huge and the response is truncated at 4500 chars. To filter: pass regionalvariable + regionalkey (e.g. DLAND + 'DG' for Germany) or classifyingvariable1..3 + classifyingkey1..3 (e.g. NAT + 'DEUTSCH'). Use genesis_list_values to find valid keys.

```json
{
  "name": "PREENCHER",
  "startyear": "PREENCHER",
  "endyear": "PREENCHER",
  "regionalvariable": "PREENCHER",
  "regionalkey": "PREENCHER",
  "classifyingvariable1": "PREENCHER",
  "classifyingkey1": "PREENCHER",
  "classifyingvariable2": "PREENCHER",
  "classifyingkey2": "PREENCHER",
  "classifyingvariable3": "PREENCHER",
  "classifyingkey3": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_get_timeseries`

Fetch a single GENESIS time series by code (returned by genesis_search with category='time-series'). Optional year filter via startyear/endyear.

```json
{
  "name": "PREENCHER",
  "startyear": "PREENCHER",
  "endyear": "PREENCHER",
  "contents": "PREENCHER",
  "language": "PREENCHER"
}
```

### `genesis_quality_signs`

Reference: meaning of GENESIS quality codes used in data cells (e.g. '-' = no data, '/' = unreliable, '()' = limited validity, 'p' = preliminary). Use this when interpreting unusual values in genesis_get_table output.

```json
{
  "language": "PREENCHER"
}
```

## GitHub (`github-api`)

JSON para preencher na credencial **Jarvis · GitHub** (substitua cada valor):

```json
{
  "github_pat": "PREENCHER"
}
```

### `search_repos`

Search GitHub repositories by keyword. Parameters: query (search keywords, required), sort ('stars', 'forks', 'updated', optional, default 'stars')

```json
{
  "query": "PREENCHER",
  "sort": "PREENCHER"
}
```

### `get_repo_info`

Get detailed info about a GitHub repository. Parameters: owner (repo owner/org, required), repo (repository name, required)

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER"
}
```

### `list_issues`

List issues for a GitHub repository. Parameters: owner (repo owner, required), repo (repository name, required), state ('open', 'closed', or 'all', optional, default 'open')

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER",
  "state": "PREENCHER"
}
```

### `create_issue`

Create a new issue in a GitHub repository. Parameters: owner (repo owner, required), repo (repository name, required), title (issue title, required), body (issue description, optional), labels (comma-separated label names, optional)

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER",
  "title": "PREENCHER",
  "body": "PREENCHER",
  "labels": "PREENCHER"
}
```

### `list_pull_requests`

List pull requests for a GitHub repository. Parameters: owner (repo owner, required), repo (repository name, required), state ('open', 'closed', or 'all', optional, default 'open')

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER",
  "state": "PREENCHER"
}
```

### `get_pull_request`

Get details of a specific pull request including diff stats and reviews. Parameters: owner (repo owner, required), repo (repository name, required), pr_number (PR number, required)

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER",
  "pr_number": "PREENCHER"
}
```

### `get_file_content`

Read a file or list a directory from a GitHub repository. Parameters: owner (repo owner, required), repo (repository name, required), path (file or directory path, required), ref (branch/tag/commit, optional, default: default branch)

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER",
  "path": "PREENCHER",
  "ref": "PREENCHER"
}
```

### `search_code`

Search code across GitHub repositories. Parameters: query (search keywords, required), owner (limit to user/org, optional), repo (limit to specific repo, optional — requires owner too)

```json
{
  "query": "PREENCHER",
  "owner": "PREENCHER",
  "repo": "PREENCHER"
}
```

### `list_releases`

List releases for a GitHub repository. Parameters: owner (repo owner, required), repo (repository name, required)

```json
{
  "owner": "PREENCHER",
  "repo": "PREENCHER"
}
```

### `list_notifications`

List your GitHub notifications. Parameters: all ('true' to include read notifications, optional, default only unread)

```json
{
  "all": "PREENCHER"
}
```

### `list_starred`

List your starred GitHub repositories. Parameters: sort ('created' or 'updated', optional, default 'created')

```json
{
  "sort": "PREENCHER"
}
```

## Gmail (`gmail`)

JSON para preencher na credencial **Jarvis · Gmail** (substitua cada valor):

```json
{
  "client_id": "PREENCHER",
  "client_secret": "PREENCHER"
}
```

### `search_emails`

Search emails using Gmail search syntax (e.g. 'from:user@example.com', 'is:unread', 'subject:hello'). Parameters: query (search query, required), max_results (number, default 10)

```json
{
  "query": "PREENCHER",
  "max_results": "PREENCHER"
}
```

### `read_email`

Read a specific email by its message ID. Returns full email content including headers, body text, and labels. Parameters: message_id (required)

```json
{
  "message_id": "PREENCHER"
}
```

### `send_email`

Send an email via Gmail. Parameters: to (recipient email, required), subject (required), body (plain text content, required), cc (optional), bcc (optional)

```json
{
  "to": "PREENCHER",
  "subject": "PREENCHER",
  "body": "PREENCHER",
  "cc": "PREENCHER",
  "bcc": "PREENCHER"
}
```

### `create_draft`

Create an email draft in Gmail. Parameters: to (recipient email, required), subject (required), body (plain text content, required)

```json
{
  "to": "PREENCHER",
  "subject": "PREENCHER",
  "body": "PREENCHER"
}
```

### `list_labels`

List all Gmail labels (both system and user-created labels).

```json
{}
```

## Google Ads (`google-ads`)

JSON para preencher na credencial **Jarvis · Google Ads** (substitua cada valor):

```json
{
  "client_id": "PREENCHER",
  "client_secret": "PREENCHER",
  "developer_token": "PREENCHER",
  "customer_id": "PREENCHER"
}
```

### `list_campaigns`

List Google Ads campaigns with performance summary. Parameters: status_filter (optional: ENABLED, PAUSED, REMOVED)

```json
{
  "status_filter": "PREENCHER"
}
```

### `get_campaign_stats`

Get detailed campaign performance statistics by date. Parameters: campaign_id (required), date_from (YYYY-MM-DD, required), date_to (YYYY-MM-DD, required)

```json
{
  "campaign_id": "PREENCHER",
  "date_from": "PREENCHER",
  "date_to": "PREENCHER"
}
```

### `list_ad_groups`

List ad groups for a specific campaign. Parameters: campaign_id (required)

```json
{
  "campaign_id": "PREENCHER"
}
```

### `get_account_stats`

Get ACCOUNT-LEVEL totals (impressions, clicks, cost, conversions) across ALL campaigns for a date range. USE THIS for questions like 'how many clicks yesterday' or 'total spend this month'. No campaign_id needed. Parameters: date_from (YYYY-MM-DD, required), date_to (YYYY-MM-DD, required)

```json
{
  "date_from": "PREENCHER",
  "date_to": "PREENCHER"
}
```

## Google Analytics (`google-analytics`)

JSON para preencher na credencial **Jarvis · Google Analytics** (substitua cada valor):

```json
{
  "client_id": "PREENCHER",
  "client_secret": "PREENCHER"
}
```

### `get_report`

Run a GA4 analytics report. Parameters: property_id (required), date_from (YYYY-MM-DD, required), date_to (YYYY-MM-DD, required), metrics (comma-separated, default: sessions,activeUsers,screenPageViews), dimensions (comma-separated, optional, e.g. date,country)

```json
{
  "property_id": "PREENCHER",
  "date_from": "PREENCHER",
  "date_to": "PREENCHER",
  "metrics": "PREENCHER",
  "dimensions": "PREENCHER"
}
```

### `list_properties`

List all GA4 properties accessible to the user.

```json
{}
```

### `get_realtime_data`

Get realtime analytics data. Parameters: property_id (required), metrics (comma-separated, default: activeUsers,screenPageViews)

```json
{
  "property_id": "PREENCHER",
  "metrics": "PREENCHER"
}
```

## Google Calendar (`google-calendar`)

JSON para preencher na credencial **Jarvis · Google Calendar** (substitua cada valor):

```json
{
  "client_id": "PREENCHER",
  "client_secret": "PREENCHER"
}
```

### `list_events`

List upcoming calendar events. Parameters: calendar_id (default 'primary'), time_min (ISO date), time_max (ISO date), max_results (default 10)

```json
{
  "calendar_id": "PREENCHER",
  "time_min": "PREENCHER",
  "time_max": "PREENCHER",
  "max_results": "PREENCHER"
}
```

### `create_event`

Create a new calendar event. Parameters: summary (title, required), start (ISO datetime, required), end (ISO datetime, required), description (optional), location (optional), calendar_id (default 'primary')

```json
{
  "summary": "PREENCHER",
  "start": "PREENCHER",
  "end": "PREENCHER",
  "description": "PREENCHER",
  "location": "PREENCHER",
  "calendar_id": "PREENCHER"
}
```

### `update_event`

Update an existing calendar event. Parameters: event_id (required), summary (optional), start (optional), end (optional), description (optional), location (optional), calendar_id (default 'primary')

```json
{
  "event_id": "PREENCHER",
  "summary": "PREENCHER",
  "start": "PREENCHER",
  "end": "PREENCHER",
  "description": "PREENCHER",
  "location": "PREENCHER",
  "calendar_id": "PREENCHER"
}
```

### `delete_event`

Delete a calendar event. Parameters: event_id (required), calendar_id (default 'primary')

```json
{
  "event_id": "PREENCHER",
  "calendar_id": "PREENCHER"
}
```

### `list_calendars`

List all calendars accessible to the user.

```json
{}
```

## Google Drive (`google-drive`)

JSON para preencher na credencial **Jarvis · Google Drive** (substitua cada valor):

```json
{
  "client_id": "PREENCHER",
  "client_secret": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `list_files`

List files and folders in a Google Drive directory. Parameters: folder_id (ID of folder to list, default 'root'), max_results (number, default 20), query (optional name filter)

```json
{
  "folder_id": "PREENCHER",
  "max_results": "PREENCHER",
  "query": "PREENCHER"
}
```

### `search_files`

Search for files by name across all of Google Drive. Parameters: query (search term, required), max_results (number, default 20)

```json
{
  "query": "PREENCHER",
  "max_results": "PREENCHER"
}
```

### `read_file`

Read the content of a file by ID. Google Docs/Sheets/Slides are exported as plain text. Text files return content inline. Binary files return a view link. Parameters: file_id (required)

```json
{
  "file_id": "PREENCHER"
}
```

### `create_file`

Create a new text file or Google Doc with content. Parameters: name (filename, required), content (file content, required), folder_id (optional parent folder ID), mime_type ('doc' for Google Doc, otherwise plain text)

```json
{
  "name": "PREENCHER",
  "content": "PREENCHER",
  "folder_id": "PREENCHER",
  "mime_type": "PREENCHER"
}
```

### `create_folder`

Create a new folder in Google Drive. Parameters: name (folder name, required), parent_folder_id (optional parent folder ID)

```json
{
  "name": "PREENCHER",
  "parent_folder_id": "PREENCHER"
}
```

### `delete_file`

Delete a file or folder from Google Drive. Parameters: file_id (required)

```json
{
  "file_id": "PREENCHER"
}
```

### `share_file`

Share a file or folder in Google Drive. Parameters: file_id (required), email (required for user sharing), role ('reader'/'writer'/'commenter', default 'reader'), type ('user' or 'anyone', default 'user')

```json
{
  "file_id": "PREENCHER",
  "email": "PREENCHER",
  "role": "PREENCHER",
  "type": "PREENCHER"
}
```

### `upload_file`

Upload a binary file (PDF, image, etc.) to Google Drive from a file_ref or external URL. For files sent by the user in chat, use file_ref (preferred). For external URLs, use file_url. Parameters: name (filename, required), file_ref (File Bridge ID, preferred for user-sent files), file_url (external URL, alternative to file_ref), folder_id (optional parent folder ID)

```json
{
  "name": "PREENCHER",
  "file_ref": "PREENCHER",
  "file_url": "PREENCHER",
  "folder_id": "PREENCHER"
}
```

### `download_file`

Download a file from Google Drive and prepare it for sending to the user. Use this when the user asks to receive/download a file. Returns a send_file link. Google Docs/Sheets/Slides are exported as PDF. Parameters: file_id (required)

```json
{
  "file_id": "PREENCHER"
}
```

## Google Media Generation (`google-media-gen`)

JSON para preencher na credencial **Jarvis · Google Media Generation** (substitua cada valor):

```json
{
  "gemini_api_key": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `generate_image`

Generate an image from a text prompt using Google Nano Banana Pro (Gemini 3 Pro Image). Returns the image as a file. Parameters: prompt (text description, required), aspect_ratio (optional: 1:1, 16:9, 9:16, 4:3, 3:4 — default 1:1)

```json
{
  "prompt": "PREENCHER",
  "aspect_ratio": "PREENCHER"
}
```

### `edit_image`

Edit a user-supplied image with a text prompt using Google Nano Banana Pro. Use this when the user sends a photo and asks for changes. Parameters: prompt (what to change, required), file_ref (file-bridge id of the source image — usually provided automatically when the user sends a photo, required), aspect_ratio (optional)

```json
{
  "prompt": "PREENCHER",
  "file_ref": "PREENCHER",
  "aspect_ratio": "PREENCHER"
}
```

### `generate_video`

Start video generation with Google Veo 3.1. Returns an operation_id IMMEDIATELY (does NOT wait for the video). After calling this, you MUST call wait_for_video repeatedly with the returned operation_id in this same conversation turn until it returns the finished MP4 file. Parameters: prompt (required), aspect_ratio (optional: 16:9 or 9:16, default 16:9), negative_prompt (optional), duration_seconds (optional, default 8)

```json
{
  "prompt": "PREENCHER",
  "aspect_ratio": "PREENCHER",
  "negative_prompt": "PREENCHER",
  "duration_seconds": "PREENCHER"
}
```

### `animate_image`

Animate a user-supplied image into a video using Google Veo 3.1 (image-to-video). Use this when the user sends a photo and asks for it to be turned into a video / animated / brought to life. Returns an operation_id IMMEDIATELY (does NOT wait for the video). After calling this, you MUST call wait_for_video repeatedly with the returned operation_id in this same conversation turn until it returns the finished MP4 file. Parameters: prompt (describes the desired motion/animation, required), file_ref (file-bridge id of the source image — usually provided automatically when the user sends a photo, required), aspect_ratio (optional: 16:9 or 9:16, default 16:9), negative_prompt (optional), duration_seconds (optional, default 8)

```json
{
  "prompt": "PREENCHER",
  "file_ref": "PREENCHER",
  "aspect_ratio": "PREENCHER",
  "negative_prompt": "PREENCHER",
  "duration_seconds": "PREENCHER"
}
```

### `wait_for_video`

Wait up to ~25 seconds for a Veo video to finish. Returns the finished MP4 file when ready, or a 'still generating, call again' message if not yet ready — in which case you MUST call this tool AGAIN with the SAME operation_id. Keep calling until you get the file. Typical Veo 3.1 jobs need 2-8 wait_for_video calls. Parameters: operation_id (the operation name returned by generate_video, required)

```json
{
  "operation_id": "PREENCHER"
}
```

## Hacker News (`hackernews`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_hackernews`

Search Hacker News stories or get top stories. Parameter: query (search term, or 'top' for top stories)

```json
{
  "query": "PREENCHER"
}
```

## Home Assistant (`home-assistant`)

JSON para preencher na credencial **Jarvis · Home Assistant** (substitua cada valor):

```json
{
  "ha_url": "PREENCHER",
  "ha_token": "PREENCHER"
}
```

### `list_entities`

List Home Assistant entities. Without parameters returns a summary by domain. Parameters: domain (optional, filter by domain like light, switch, sensor, climate, media_player), search (optional, substring match on entity_id or friendly_name), limit (optional, default 50).

```json
{
  "domain": "PREENCHER",
  "search": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_state`

Get the current state and attributes of a specific Home Assistant entity. Parameter: entity_id (required, e.g. light.kitchen, sensor.outdoor_temperature, climate.living_room).

```json
{
  "entity_id": "PREENCHER"
}
```

### `list_services`

List available Home Assistant services. Without parameters shows all domains with their services. Parameters: domain (optional, e.g. light, climate, switch — returns detailed info incl. fields).

```json
{
  "domain": "PREENCHER"
}
```

### `speak`

Speak a text message on a Home Assistant voice device or speaker. Auto-selects the best path: prefers assist_satellite.announce (works reliably for HA Voice Preview Edition / HAPPE2 satellites, bypasses media_player routing), falls back to tts.speak on a media_player with a TTS engine. Parameters: message (required, text to speak), device_hint (optional, substring to match a specific device by entity_id or friendly_name — e.g. 'kitchen', 'voice'; if omitted, picks the first available device).

```json
{
  "message": "PREENCHER",
  "device_hint": "PREENCHER"
}
```

### `call_service`

Call a Home Assistant service to control devices. Parameters: domain (required, e.g. light, switch, climate, media_player), service (required, e.g. turn_on, turn_off, toggle, set_temperature), entity_id (optional target entity, e.g. light.kitchen), service_data (optional JSON string with additional data like '{"brightness": 128, "rgb_color": [255,0,0]}').

```json
{
  "domain": "PREENCHER",
  "service": "PREENCHER",
  "entity_id": "PREENCHER",
  "service_data": "PREENCHER"
}
```

## HubSpot CRM (`hubspot`)

JSON para preencher na credencial **Jarvis · HubSpot CRM** (substitua cada valor):

```json
{
  "hubspot_pat": "PREENCHER"
}
```

### `list_contacts`

List recent HubSpot contacts (paginated).

```json
{
  "limit": "PREENCHER"
}
```

### `search_contacts`

Search contacts. Default matches 'email'; override via 'property' (firstname, lastname, phone, company, any property name) and 'operator' (EQ, NEQ, CONTAINS_TOKEN, GT, LT, HAS_PROPERTY).

```json
{
  "query": "PREENCHER",
  "property": "PREENCHER",
  "operator": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_contact`

Get a contact by id or email.

```json
{
  "contact_id": "PREENCHER",
  "email": "PREENCHER"
}
```

### `create_contact`

Create a new contact. At least email, firstname or lastname required.

```json
{
  "email": "PREENCHER",
  "firstname": "PREENCHER",
  "lastname": "PREENCHER",
  "phone": "PREENCHER",
  "company": "PREENCHER",
  "jobtitle": "PREENCHER",
  "lifecyclestage": "PREENCHER"
}
```

### `update_contact`

Update an existing contact by id.

```json
{
  "contact_id": "PREENCHER",
  "email": "PREENCHER",
  "firstname": "PREENCHER",
  "lastname": "PREENCHER",
  "phone": "PREENCHER",
  "company": "PREENCHER",
  "jobtitle": "PREENCHER",
  "lifecyclestage": "PREENCHER",
  "hs_lead_status": "PREENCHER"
}
```

### `delete_contact`

Archive (soft-delete) a contact by id. Restorable within 90 days in HubSpot UI.

```json
{
  "contact_id": "PREENCHER"
}
```

### `search_companies`

Search companies. Default property 'name'; override via 'property' (domain, industry, country) and 'operator'.

```json
{
  "query": "PREENCHER",
  "property": "PREENCHER",
  "operator": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_company`

Get a company by id.

```json
{
  "company_id": "PREENCHER"
}
```

### `create_company`

Create a new company. Requires name or domain.

```json
{
  "name": "PREENCHER",
  "domain": "PREENCHER",
  "phone": "PREENCHER",
  "city": "PREENCHER",
  "state": "PREENCHER",
  "country": "PREENCHER",
  "industry": "PREENCHER",
  "description": "PREENCHER",
  "numberofemployees": "PREENCHER",
  "website": "PREENCHER"
}
```

### `update_company`

Update a company by id.

```json
{
  "company_id": "PREENCHER",
  "name": "PREENCHER",
  "domain": "PREENCHER",
  "phone": "PREENCHER",
  "city": "PREENCHER",
  "state": "PREENCHER",
  "country": "PREENCHER",
  "industry": "PREENCHER",
  "description": "PREENCHER",
  "numberofemployees": "PREENCHER",
  "website": "PREENCHER"
}
```

### `delete_company`

Archive (soft-delete) a company.

```json
{
  "company_id": "PREENCHER"
}
```

### `list_deals`

List recent deals.

```json
{
  "limit": "PREENCHER"
}
```

### `search_deals`

Search deals. Default property 'dealname'; override via 'property' (dealstage, amount, hubspot_owner_id, closedate) and 'operator' (EQ, GT, LT, CONTAINS_TOKEN, BETWEEN).

```json
{
  "query": "PREENCHER",
  "property": "PREENCHER",
  "operator": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_deal`

Get a deal by id. Includes associated contacts and companies.

```json
{
  "deal_id": "PREENCHER"
}
```

### `create_deal`

Create a new deal. Requires dealname.

```json
{
  "dealname": "PREENCHER",
  "amount": "PREENCHER",
  "dealstage": "PREENCHER",
  "pipeline": "PREENCHER",
  "closedate": "PREENCHER",
  "hubspot_owner_id": "PREENCHER",
  "dealtype": "PREENCHER",
  "description": "PREENCHER",
  "associated_contact_id": "PREENCHER",
  "associated_company_id": "PREENCHER"
}
```

### `update_deal`

Update a deal by id (move stage, update amount, change owner, etc.).

```json
{
  "deal_id": "PREENCHER",
  "dealname": "PREENCHER",
  "amount": "PREENCHER",
  "dealstage": "PREENCHER",
  "pipeline": "PREENCHER",
  "closedate": "PREENCHER",
  "hubspot_owner_id": "PREENCHER",
  "dealtype": "PREENCHER",
  "description": "PREENCHER"
}
```

### `delete_deal`

Archive (soft-delete) a deal.

```json
{
  "deal_id": "PREENCHER"
}
```

### `search_tickets`

Search tickets. Default property 'subject'; override via 'property' (hs_pipeline_stage, hs_ticket_priority, hubspot_owner_id) and 'operator'.

```json
{
  "query": "PREENCHER",
  "property": "PREENCHER",
  "operator": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_ticket`

Get a ticket by id.

```json
{
  "ticket_id": "PREENCHER"
}
```

### `create_ticket`

Create a new ticket. Requires subject.

```json
{
  "subject": "PREENCHER",
  "content": "PREENCHER",
  "hs_pipeline": "PREENCHER",
  "hs_pipeline_stage": "PREENCHER",
  "hs_ticket_priority": "PREENCHER",
  "hubspot_owner_id": "PREENCHER",
  "source_type": "PREENCHER",
  "associated_contact_id": "PREENCHER",
  "associated_company_id": "PREENCHER"
}
```

### `update_ticket`

Update a ticket (change stage, priority, assign owner).

```json
{
  "ticket_id": "PREENCHER",
  "subject": "PREENCHER",
  "content": "PREENCHER",
  "hs_pipeline": "PREENCHER",
  "hs_pipeline_stage": "PREENCHER",
  "hs_ticket_priority": "PREENCHER",
  "hubspot_owner_id": "PREENCHER"
}
```

### `delete_ticket`

Archive (soft-delete) a ticket.

```json
{
  "ticket_id": "PREENCHER"
}
```

### `create_note`

Create a note and optionally associate it with an object (contact, company, deal or ticket).

```json
{
  "body": "PREENCHER",
  "associated_contact_id": "PREENCHER",
  "associated_company_id": "PREENCHER",
  "associated_deal_id": "PREENCHER",
  "associated_ticket_id": "PREENCHER"
}
```

### `create_task`

Create a task with due-date, priority and optional object attachment.

```json
{
  "subject": "PREENCHER",
  "body": "PREENCHER",
  "priority": "PREENCHER",
  "status": "PREENCHER",
  "type": "PREENCHER",
  "due_date": "PREENCHER",
  "hubspot_owner_id": "PREENCHER",
  "associated_contact_id": "PREENCHER",
  "associated_company_id": "PREENCHER",
  "associated_deal_id": "PREENCHER",
  "associated_ticket_id": "PREENCHER"
}
```

### `associate_objects`

Associate two CRM objects via v4 default association. Types: contacts, companies, deals, tickets, notes, tasks.

```json
{
  "from_type": "PREENCHER",
  "from_id": "PREENCHER",
  "to_type": "PREENCHER",
  "to_id": "PREENCHER"
}
```

### `list_associations`

List objects of a given type associated with a source object.

```json
{
  "from_type": "PREENCHER",
  "from_id": "PREENCHER",
  "to_type": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `list_pipelines`

List pipelines and their stages for deals or tickets.

```json
{
  "object_type": "PREENCHER"
}
```

### `list_owners`

List HubSpot users / owners (for hubspot_owner_id assignments).

```json
{
  "limit": "PREENCHER"
}
```

## IP Geolocation (`ip-geolocation`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `geolocate_ip`

Get location, ISP, and organization info for an IP address. Parameter: ip (IP address to look up)

```json
{
  "ip": "PREENCHER"
}
```

## Jira Cloud (`jira`)

JSON para preencher na credencial **Jarvis · Jira Cloud** (substitua cada valor):

```json
{
  "atlassian_email": "PREENCHER",
  "atlassian_api_token": "PREENCHER",
  "atlassian_site": "PREENCHER"
}
```

### `list_projects`

List all Jira projects accessible with the token. No parameters. Use this first to find a project key before other operations.

```json
{}
```

### `search_issues`

Search issues with JQL. Examples: 'assignee = currentUser() AND status != Done', 'project = KAN ORDER BY created DESC', 'text ~ \"login bug\"'. Parameters: jql (required), limit (optional default 20), fields (optional comma list). IMPORTANT: never use currentUser() in JQL (service account, always 0 results) - filter by display name or accountId.

```json
{
  "jql": "PREENCHER",
  "limit": "PREENCHER",
  "fields": "PREENCHER",
  "max_results": "PREENCHER"
}
```

### `get_issue`

Get full issue detail by key (e.g. KAN-1). Returns summary, status, type, assignee, description, labels, links, recent comments. Parameters: key (required).

```json
{
  "key": "PREENCHER"
}
```

### `create_issue`

Create a new issue. Parameters: project (required, key like KAN), summary (required), issuetype (optional, default Task - use list_issue_types to see valid types), description, assignee (accountId from list_users), priority (e.g. Highest, High, Medium, Low), labels (comma-separated), parent (for subtasks, parent issue key). If creation fails with a required custom field, retry with custom_fields (JSON) using the field id and one of the allowed values from the error message. Project specific required fields go into custom_fields as a JSON object; a plain value is enough, the tool derives the required shape (list, option object or plain text) from the Jira field schema.

```json
{
  "project": "PREENCHER",
  "summary": "PREENCHER",
  "issuetype": "PREENCHER",
  "description": "PREENCHER",
  "assignee": "PREENCHER",
  "priority": "PREENCHER",
  "labels": "PREENCHER",
  "parent": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_issue`

Update issue fields. Parameters: key (required), plus at least one of: summary, description, assignee (accountId; pass empty string to unassign), priority, labels (comma-separated). To change status use transition_issue instead.

```json
{
  "key": "PREENCHER",
  "summary": "PREENCHER",
  "description": "PREENCHER",
  "assignee": "PREENCHER",
  "priority": "PREENCHER",
  "labels": "PREENCHER"
}
```

### `add_comment`

Add a comment to an issue. Parameters: key (required), text (required, plain text).

```json
{
  "key": "PREENCHER",
  "text": "PREENCHER"
}
```

### `list_comments`

List all comments on an issue. Parameters: key (required).

```json
{
  "key": "PREENCHER"
}
```

### `transition_issue`

Change issue status. Parameters: key (required), transition (required, status name like 'Done', 'In Progress' or transition id). Status names are localized per workspace - use list_transitions first if unsure.

```json
{
  "key": "PREENCHER",
  "transition": "PREENCHER"
}
```

### `list_transitions`

List available status transitions for an issue from its current state. Parameters: key (required).

```json
{
  "key": "PREENCHER"
}
```

### `list_issue_types`

List valid issue types for a project. Parameters: project (required, project key).

```json
{
  "project": "PREENCHER"
}
```

### `link_issues`

Create a relationship between two issues. Parameters: from (required, issue key), to (required, issue key), type (optional, default 'Relates'; also 'Blocks', 'Duplicate', 'Cloners'). Example: from=KAN-1 to=KAN-2 type=Blocks means KAN-1 blocks KAN-2.

```json
{
  "from": "PREENCHER",
  "to": "PREENCHER",
  "type": "PREENCHER"
}
```

### `list_users`

Search Atlassian users by name or email. Use before assignee fields to find accountId. Parameters: query (required, name/email fragment), limit (optional, default 10).

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER"
}
```

## KontoFlux (`kontoflux`)

JSON para preencher na credencial **Jarvis · KontoFlux** (substitua cada valor):

```json
{
  "kontoflux_api_key": "PREENCHER",
  "kontoflux_workspace_id": "PREENCHER"
}
```

### `list_accounts`

List all bank accounts in your KontoFlux workspace with balances and IBANs. No parameters needed.

```json
{}
```

### `get_transactions`

Get the 10 most recent bank transactions. Parameter: account_id (numeric ID from list_accounts). Returns date, amount, counterpart, category.

```json
{
  "account_id": "PREENCHER"
}
```

### `search_transactions`

Full-text search across all transactions. Parameter: query (search text). Returns matching transactions with amount, counterpart, purpose, category, date.

```json
{
  "query": "PREENCHER"
}
```

### `list_categories`

List all AI-generated transaction categories with subcategories. No parameters needed.

```json
{}
```

### `check_scope`

Check API key permissions and access scope. No parameters needed.

```json
{}
```

## Lexware Office (`lexware`)

JSON para preencher na credencial **Jarvis · Lexware Office** (substitua cada valor):

```json
{
  "lexware_api_token": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `list_contacts`

List Lexware contacts. Optional: name (search, min 3 chars), customer (true/false), vendor (true/false), page (number).

```json
{
  "page": "PREENCHER",
  "name": "PREENCHER",
  "email": "PREENCHER",
  "customer": "PREENCHER",
  "vendor": "PREENCHER"
}
```

### `get_contact`

Get full details of a contact. Returns name, address, email, phone, version. Parameter: id (UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

### `create_company`

Create a company contact. Example: companyName=ACME GmbH, street=Hauptstr. 1, zip=80331, city=München, email=info@acme.de, phone=+4989123456

```json
{
  "companyName": "PREENCHER",
  "email": "PREENCHER",
  "phone": "PREENCHER",
  "note": "PREENCHER",
  "contactPersonName": "PREENCHER",
  "street": "PREENCHER",
  "zip": "PREENCHER",
  "city": "PREENCHER"
}
```

### `create_person`

Create a person contact. Example: lastName=Müller, firstName=Hans, street=Hauptstr. 1, zip=80331, city=München, email=hans@example.de, phone=+4989123456

```json
{
  "lastName": "PREENCHER",
  "firstName": "PREENCHER",
  "email": "PREENCHER",
  "phone": "PREENCHER",
  "note": "PREENCHER",
  "street": "PREENCHER",
  "zip": "PREENCHER",
  "city": "PREENCHER"
}
```

### `update_contact_address`

Update the address of a contact. Call get_contact first for id+version. Example: id=abc, version=3, street=Strandallee 61, zip=26969, city=Butjadingen

```json
{
  "id": "PREENCHER",
  "version": "PREENCHER",
  "street": "PREENCHER",
  "zip": "PREENCHER",
  "city": "PREENCHER"
}
```

### `update_contact_email`

Update ONLY the email of a contact. Call get_contact first for id and version. Example: id=abc-123, version=3, email=neu@firma.de

```json
{
  "id": "PREENCHER",
  "version": "PREENCHER",
  "email": "PREENCHER"
}
```

### `update_contact_phone`

Update ONLY the phone of a contact. Call get_contact first for id and version. Example: id=abc-123, version=3, phone=+4930999888

```json
{
  "id": "PREENCHER",
  "version": "PREENCHER",
  "phone": "PREENCHER"
}
```

### `update_contact_name`

Update ONLY the name of a contact. Call get_contact first for id and version. Example: id=abc-123, version=3, name=Neuer Firmenname GmbH

```json
{
  "id": "PREENCHER",
  "version": "PREENCHER",
  "name": "PREENCHER"
}
```

### `list_articles`

List Lexware articles (products and services). Optional: type (PRODUCT or SERVICE), page (number).

```json
{
  "page": "PREENCHER",
  "type": "PREENCHER"
}
```

### `get_article`

Get details of an article. Returns title, type, price, version. Parameter: id (UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

### `create_article`

Create an article. Example: title=Beratung, type=SERVICE, unitName=Stunde, netPrice=120, taxRate=19

```json
{
  "title": "PREENCHER",
  "type": "PREENCHER",
  "unitName": "PREENCHER",
  "netPrice": "PREENCHER",
  "taxRate": "PREENCHER",
  "description": "PREENCHER",
  "articleNumber": "PREENCHER"
}
```

### `update_article`

Update an article. Call get_article first for id+version. Example: id=abc, version=1, title=Neuer Name, netPrice=150, taxRate=19

```json
{
  "id": "PREENCHER",
  "version": "PREENCHER",
  "title": "PREENCHER",
  "type": "PREENCHER",
  "unitName": "PREENCHER",
  "netPrice": "PREENCHER",
  "taxRate": "PREENCHER",
  "description": "PREENCHER",
  "articleNumber": "PREENCHER"
}
```

### `delete_article`

Delete an article by ID. Parameter: id (UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

### `upload_voucher`

Upload a voucher/receipt to Lexware. When the user sends a file (photo/PDF), use the file_ref from the attachment. Parameter: file_ref (REQUIRED, the File Bridge reference ID)

```json
{
  "file_ref": "PREENCHER"
}
```

### `list_quotations`

List Lexware quotations (Angebote). Optional: status (draft/open/accepted/rejected), page.

```json
{
  "page": "PREENCHER",
  "status": "PREENCHER"
}
```

### `get_quotation`

Get details of a quotation including line items and totals. Parameter: id (UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

### `create_quotation`

Create a quotation. Example: contactId=abc-123, lineItems=[{"name":"Beratung","quantity":5,"unitPrice":120,"taxRate":19}], finalize=false

```json
{
  "contactId": "PREENCHER",
  "lineItems": "PREENCHER",
  "finalize": "PREENCHER",
  "voucherDate": "PREENCHER",
  "introduction": "PREENCHER",
  "remark": "PREENCHER"
}
```

### `list_invoices`

List Lexware invoices (Rechnungen). Optional: status (draft/open/paidoff/voided), page.

```json
{
  "page": "PREENCHER",
  "status": "PREENCHER"
}
```

### `get_invoice`

Get details of an invoice including line items and totals. Parameter: id (UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

### `create_invoice`

Create an invoice. Example: contactId=abc-123, lineItems=[{"name":"Beratung","quantity":5,"unitPrice":120,"taxRate":19}], finalize=true

```json
{
  "contactId": "PREENCHER",
  "lineItems": "PREENCHER",
  "finalize": "PREENCHER",
  "voucherDate": "PREENCHER",
  "introduction": "PREENCHER",
  "remark": "PREENCHER"
}
```

### `create_invoice_from_quotation`

Create an invoice from an existing quotation. Copies all line items. Example: quotationId=abc-123, finalize=true

```json
{
  "quotationId": "PREENCHER",
  "finalize": "PREENCHER"
}
```

### `download_invoice`

Download an invoice as PDF and send it to the user. Use get_invoice or list_invoices first to find the ID. The PDF will be sent as a file in Telegram. Parameter: id (Invoice UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

### `download_quotation`

Download a quotation as PDF and send it to the user. Use get_quotation or list_quotations first to find the ID. The PDF will be sent as a file in Telegram. Parameter: id (Quotation UUID, REQUIRED).

```json
{
  "id": "PREENCHER"
}
```

## Meta Ads (`meta-ads`)

JSON para preencher na credencial **Jarvis · Meta Ads** (substitua cada valor):

```json
{
  "auth_token": "PREENCHER"
}
```

Ponte MCP: https://meta-ads.mcp.pipeboard.co/. Os argumentos seguem o schema publicado pelo provedor.

- `get_ad_accounts`
- `get_account_info`
- `get_account_pages`
- `search_pages_by_name`
- `get_pixels`
- `get_account_activities`
- `search`
- `fetch`
- `submit_feedback`
- `get_campaigns`
- `get_campaign_details`
- `create_campaign`
- `update_campaign`
- `duplicate_campaign`
- `create_budget_schedule`
- `get_adsets`
- `get_adset_details`
- `create_adset`
- `update_adset`
- `duplicate_adset`
- `get_ads`
- `get_ad_details`
- `create_ad`
- `update_ad`
- `duplicate_ad`
- `get_ad_previews`
- `get_ad_image`
- `get_ad_video`
- `get_ad_creatives`
- `get_creative_details`
- `create_ad_creative`
- `update_ad_creative`
- `duplicate_creative`
- `delete_ad_creative`
- `create_existing_post_ad_creative`
- `create_carousel_ad_creative`
- `upload_ad_image`
- `upload_ad_video`
- `bulk_upload_ad_images`
- `bulk_upload_ad_videos`
- `delete_ad_image`
- `compute_image_crops`
- `get_insights`
- `bulk_get_insights`
- `create_meta_ads_email_report`
- `list_meta_ads_email_reports`
- `update_meta_ads_email_report`
- `delete_meta_ads_email_report`
- `bulk_update_ads`
- `bulk_update_campaigns`
- `bulk_update_adsets`
- `bulk_create_ads`
- `bulk_create_ad_creatives`
- `bulk_get_ad_creatives`
- `search_interests`
- `bulk_search_interests`
- `get_interest_suggestions`
- `search_behaviors`
- `search_demographics`
- `search_geo_locations`
- `estimate_audience_size`
- `get_custom_audiences`
- `get_saved_audiences`
- `create_custom_audience`
- `update_custom_audience`
- `delete_custom_audience`
- `create_lookalike_audience`
- `add_users_to_audience`
- `remove_users_from_audience`
- `list_value_rule_sets`
- `create_value_rule_set`
- `update_value_rule_set`
- `delete_value_rule_set`
- `get_instagram_accounts`
- `get_instagram_posts`
- `get_instagram_account_insights`
- `resolve_instagram_media`
- `get_facebook_posts`
- `get_facebook_page_insights`
- `check_post_boost_eligibility`
- `manage_partnership_ad_permission`
- `resolve_branded_content_creator`
- `create_lead_gen_form`
- `get_lead_gen_forms`
- `update_lead_gen_form_status`
- `publish_lead_gen_draft_form`
- `list_catalogs`
- `create_catalog`
- `list_product_sets`
- `create_product_set`
- `add_catalog_product`
- `update_catalog_product`
- `upload_conversion_events`

## News (NewsAPI) (`news-newsapi`)

JSON para preencher na credencial **Jarvis · News (NewsAPI)** (substitua cada valor):

```json
{
  "newsapi_key": "PREENCHER"
}
```

### `search_news`

Search news articles by keyword. Parameters: query (search keywords, required), language (ISO code like 'en', 'de', optional), sort_by ('publishedAt', 'relevancy', or 'popularity', optional)

```json
{
  "query": "PREENCHER",
  "language": "PREENCHER",
  "sort_by": "PREENCHER"
}
```

## Nextcloud Files (`nextcloud-files`)

JSON para preencher na credencial **Jarvis · Nextcloud Files** (substitua cada valor):

```json
{
  "nextcloud_url": "PREENCHER",
  "nextcloud_username": "PREENCHER",
  "nextcloud_password": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `list_files`

List files and folders in a Nextcloud directory. Parameters: path (optional, default / for root directory, e.g. /Documents or /Photos/2026)

```json
{
  "path": "PREENCHER"
}
```

### `read_file`

Read the text content of a file on Nextcloud. Works best with text files (.txt, .md, .csv, .json, .xml). Parameters: path (file path, e.g. /Documents/notes.txt)

```json
{
  "path": "PREENCHER"
}
```

### `write_file`

Create or overwrite a file on Nextcloud with text content. Parent folders are created automatically. Parameters: path (file path, e.g. /Documents/notes.txt), content (text content to write)

```json
{
  "path": "PREENCHER",
  "content": "PREENCHER"
}
```

### `upload_from_url`

Download a file from a URL and save it to Nextcloud. Use this to upload images, PDFs, or any file from the internet or Telegram file URLs. Parameters: url (source URL to download from), path (destination path on Nextcloud, e.g. /Photos/image.jpg)

```json
{
  "url": "PREENCHER",
  "path": "PREENCHER"
}
```

### `create_folder`

Create a new folder on Nextcloud. Parameters: path (folder path to create, e.g. /Projects/NewProject)

```json
{
  "path": "PREENCHER"
}
```

### `delete_file`

Delete a file or folder on Nextcloud. Deleting a folder removes all its contents. Parameters: path (path to delete, e.g. /Documents/old-file.txt)

```json
{
  "path": "PREENCHER"
}
```

### `move_file`

Move or rename a file or folder on Nextcloud. Parameters: source (current path, e.g. /Documents/old-name.txt), destination (new path, e.g. /Archive/new-name.txt)

```json
{
  "source": "PREENCHER",
  "destination": "PREENCHER"
}
```

### `upload_file`

Upload a binary file (PDF, image, etc.) to Nextcloud from a file_ref or external URL. For files sent by the user in chat, use file_ref (preferred). For external URLs, use file_url. Parameters: path (full destination path including filename, e.g. /Documents/report.pdf), file_ref (File Bridge ID, preferred for user-sent files), file_url (external URL, alternative)

```json
{
  "path": "PREENCHER",
  "file_ref": "PREENCHER",
  "file_url": "PREENCHER"
}
```

### `download_file`

Download a file from Nextcloud and prepare it for sending to the user. Use this when the user asks to receive/download a binary file (PDF, image, etc.). Returns a send_file link. Parameters: path (file path on Nextcloud, e.g. /Documents/report.pdf)

```json
{
  "path": "PREENCHER"
}
```

## NocoDB (`nocodb-crm`)

JSON para preencher na credencial **Jarvis · NocoDB** (substitua cada valor):

```json
{
  "nocodb_url": "PREENCHER",
  "nocodb_token": "PREENCHER"
}
```

### `nocodb_list_bases`

List all NocoDB bases (databases) with their IDs. Use this first to discover available bases, then use nocodb_list_tables with a base ID.

```json
{}
```

### `nocodb_list_tables`

List all tables in a NocoDB base. Parameters: base_id (required, base ID from nocodb_list_bases)

```json
{
  "base_id": "PREENCHER"
}
```

### `nocodb_list_records`

List records from a NocoDB table. Parameters: table_id (required, table ID from nocodb_list_tables), limit (max records, default 25), offset (skip N records), where (filter like '(Status,eq,Active)'), sort (field name, prefix with '-' for descending), fields (comma-separated field names)

```json
{
  "table_id": "PREENCHER",
  "limit": "PREENCHER",
  "offset": "PREENCHER",
  "where": "PREENCHER",
  "sort": "PREENCHER",
  "fields": "PREENCHER"
}
```

### `nocodb_get_record`

Get a single record from a NocoDB table by ID. Parameters: table_id (required), record_id (required, the row ID)

```json
{
  "table_id": "PREENCHER",
  "record_id": "PREENCHER"
}
```

### `nocodb_create_record`

Create a new record in a NocoDB table. Parameters: table_id (required), data (required, JSON string of field:value pairs like '{"Name":"John","Email":"john@example.com"}')

```json
{
  "table_id": "PREENCHER",
  "data": "PREENCHER"
}
```

### `nocodb_update_record`

Update an existing record in a NocoDB table. Parameters: table_id (required), record_id (required), data (required, JSON string of fields to update like '{"Status":"Done"}')

```json
{
  "table_id": "PREENCHER",
  "record_id": "PREENCHER",
  "data": "PREENCHER"
}
```

### `nocodb_delete_record`

Delete a record from a NocoDB table. Parameters: table_id (required), record_id (required)

```json
{
  "table_id": "PREENCHER",
  "record_id": "PREENCHER"
}
```

### `nocodb_get_table_schema`

Read the full schema of a NocoDB table: field names, types (uidt), primary key, and select options. Use this before creating or updating records so you use the correct field names. Parameters: table_id (required, from nocodb_list_tables)

```json
{
  "table_id": "PREENCHER"
}
```

### `nocodb_create_table`

Create a new table in a NocoDB base. Parameters: base_id (required), title (required, table name), columns (optional JSON array like [{"title":"Name","uidt":"SingleLineText"},{"title":"Age","uidt":"Number"}]; defaults to one Title text field). Common uidt values: SingleLineText, LongText, Number, Decimal, Checkbox, Date, DateTime, SingleSelect, MultiSelect, Email, URL, PhoneNumber, Currency, Percent, Rating

```json
{
  "base_id": "PREENCHER",
  "title": "PREENCHER",
  "columns": "PREENCHER"
}
```

### `nocodb_update_table`

Rename a NocoDB table. Parameters: table_id (required), title (required, the new name)

```json
{
  "table_id": "PREENCHER",
  "title": "PREENCHER"
}
```

### `nocodb_delete_table`

Delete a NocoDB table and ALL its records. Irreversible — confirm with the user first. Parameters: table_id (required)

```json
{
  "table_id": "PREENCHER"
}
```

### `nocodb_create_column`

Add a new field/column to a NocoDB table. Parameters: table_id (required), title (required, field name), uidt (required, field type, one of: SingleLineText, LongText, Number, Decimal, Checkbox, Date, DateTime, SingleSelect, MultiSelect, Email, URL, PhoneNumber, Currency, Percent, Rating), extra (optional JSON for advanced config, e.g. for SingleSelect: {"colOptions":{"options":[{"title":"Open"},{"title":"Done"}]}})

```json
{
  "table_id": "PREENCHER",
  "title": "PREENCHER",
  "uidt": "PREENCHER",
  "extra": "PREENCHER"
}
```

### `nocodb_update_column`

Update a field/column in a NocoDB table (rename or change type). Parameters: column_id (required, from nocodb_get_table_schema), data (required JSON of fields to change, e.g. {"title":"NewName"} or {"uidt":"Number"})

```json
{
  "column_id": "PREENCHER",
  "data": "PREENCHER"
}
```

### `nocodb_delete_column`

Delete a field/column from a NocoDB table including its data. Irreversible — confirm with the user first. Parameters: column_id (required, from nocodb_get_table_schema)

```json
{
  "column_id": "PREENCHER"
}
```

### `nocodb_create_base`

Create a new NocoDB base (database). Parameters: title (required, base name), workspace_id (optional; defaults to the first workspace)

```json
{
  "title": "PREENCHER",
  "workspace_id": "PREENCHER"
}
```

### `nocodb_update_base`

Rename a NocoDB base. Parameters: base_id (required), title (required, the new name)

```json
{
  "base_id": "PREENCHER",
  "title": "PREENCHER"
}
```

### `nocodb_delete_base`

Delete a NocoDB base (database) and ALL its tables and records. Irreversible — confirm with the user first. Parameters: base_id (required)

```json
{
  "base_id": "PREENCHER"
}
```

## Notion (`notion`)

JSON para preencher na credencial **Jarvis · Notion** (substitua cada valor):

```json
{
  "notion_token": "PREENCHER"
}
```

### `search_pages`

Search for pages in Notion by title. Parameter: query (required, search term to match against page titles)

```json
{
  "query": "PREENCHER"
}
```

### `read_page`

Read the content of a Notion page. Returns the page title and content as markdown. Parameter: page_id (required, the page UUID from search_pages)

```json
{
  "page_id": "PREENCHER"
}
```

### `create_page`

Create a new page in Notion. Parameters: title (required, page title), content (markdown content or empty string), parent_id (parent page UUID or empty string for first available page)

```json
{
  "title": "PREENCHER",
  "content": "PREENCHER",
  "parent_id": "PREENCHER"
}
```

## ntfy.sh (`ntfy`)

JSON para preencher na credencial **Jarvis · ntfy.sh** (substitua cada valor):

```json
{
  "ntfy_topic": "PREENCHER"
}
```

### `send_notification`

Send a push notification via ntfy.sh to the user's phone. Parameters: message (required, notification body text), title (optional short title), priority (optional 1-5, 3=default, 5=urgent with sound+vibration, 1=silent), tags (optional comma-separated emoji shortcuts like 'warning,fire' or 'heavy_check_mark'), click (optional URL that opens when tapping the notification), attach (optional URL to an image/file to attach), filename (optional custom filename for attachment).

```json
{
  "message": "PREENCHER",
  "title": "PREENCHER",
  "priority": "PREENCHER",
  "tags": "PREENCHER",
  "click": "PREENCHER",
  "attach": "PREENCHER",
  "filename": "PREENCHER"
}
```

## ÖBB (`oebb`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_station`

Search for an Austrian train station by name (ÖBB). Returns station names and IDs. Parameter: query (station name to search for, e.g. 'Wien Hbf')

```json
{
  "query": "PREENCHER"
}
```

### `get_departures`

Get upcoming departures from an Austrian train station (ÖBB). Accepts station name (auto-resolved) or ID. Parameters: station (station name or ID, e.g. 'Wien Hbf'), duration (optional, minutes to look ahead, default 60)

```json
{
  "station": "PREENCHER",
  "duration": "PREENCHER"
}
```

### `get_arrivals`

Get upcoming arrivals at an Austrian train station (ÖBB). Accepts station name (auto-resolved) or ID. Parameters: station (station name or ID, e.g. 'Salzburg Hbf'), duration (optional, minutes to look ahead, default 60)

```json
{
  "station": "PREENCHER",
  "duration": "PREENCHER"
}
```

### `search_journey`

Search for Austrian train connections between two stations (ÖBB). Accepts station names (auto-resolved) or IDs. Parameters: from (origin station, e.g. 'Wien Hbf'), to (destination, e.g. 'Salzburg Hbf'), departure (optional, ISO 8601 datetime), results (optional, number of connections, default 3)

```json
{
  "from": "PREENCHER",
  "to": "PREENCHER",
  "departure": "PREENCHER",
  "results": "PREENCHER"
}
```

## ÖPNV Deutschland (`oepnv`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_station`

Search for a German public transit stop by name (nationwide ÖPNV: S-Bahn, U-Bahn, Tram, Bus, regional). Returns stop names and IDs. Parameter: query (stop name to search for, e.g. 'München Hauptbahnhof')

```json
{
  "query": "PREENCHER"
}
```

### `get_departures`

Get upcoming departures from a German public transit stop (nationwide ÖPNV). Accepts stop name (auto-resolved) or EFA ID. Parameters: station (stop name or ID, e.g. 'Essen Hbf'), results (optional, number of departures, default 10)

```json
{
  "station": "PREENCHER",
  "results": "PREENCHER"
}
```

### `get_arrivals`

Get upcoming arrivals at a German public transit stop (nationwide ÖPNV). Accepts stop name (auto-resolved) or EFA ID. Parameters: station (stop name or ID, e.g. 'Hamburg Hbf'), results (optional, number of arrivals, default 10)

```json
{
  "station": "PREENCHER",
  "results": "PREENCHER"
}
```

### `search_journey`

Search for German public transit connections between two stops (nationwide ÖPNV: includes S/U/Tram/Bus/regional). Accepts stop names (auto-resolved) or EFA IDs. Parameters: from (origin, e.g. 'Essen Hbf'), to (destination, e.g. 'Köln Hbf'), departure (optional, ISO 8601 datetime), results (optional, number of connections, default 3)

```json
{
  "from": "PREENCHER",
  "to": "PREENCHER",
  "departure": "PREENCHER",
  "results": "PREENCHER"
}
```

## Open Terminal (`open-terminal`)

JSON para preencher na credencial **Jarvis · Open Terminal** (substitua cada valor):

```json
{
  "terminal_url": "PREENCHER",
  "terminal_api_key": "PREENCHER"
}
```

### `run_command`

Execute a shell command on the Open Terminal host and return stdout/stderr and the exit code. Polls until the command finishes (up to ~timeout seconds). Parameters: command (required, e.g. 'ls -la' or 'cd /tmp && ./build.sh'), cwd (optional working directory), timeout (optional max seconds to wait, default 60, max 180), confirm (set 'true' to run a command that was flagged as potentially destructive).

```json
{
  "command": "PREENCHER",
  "cwd": "PREENCHER",
  "timeout": "PREENCHER",
  "confirm": "PREENCHER"
}
```

### `send_input`

Send text to the stdin of a still-running process (started by run_command). Use for interactive prompts, sudo passwords, or 2FA / confirmation codes. Parameters: process_id (required, from a run_command that is still running), text (required, the text to send; use \n for Enter, \x03 for Ctrl-C).

```json
{
  "process_id": "PREENCHER",
  "text": "PREENCHER"
}
```

### `read_file`

Read a text file from the Open Terminal host. Parameters: path (required, absolute or relative), start_line (optional, 1-indexed), end_line (optional, 1-indexed).

```json
{
  "path": "PREENCHER",
  "start_line": "PREENCHER",
  "end_line": "PREENCHER"
}
```

### `write_file`

Write text content to a file on the Open Terminal host (creates parent directories, overwrites if it exists). Parameters: path (required), content (required, the full text to write).

```json
{
  "path": "PREENCHER",
  "content": "PREENCHER"
}
```

### `list_files`

List files and directories at a path on the Open Terminal host. Parameter: directory (optional, defaults to current directory '.').

```json
{
  "directory": "PREENCHER"
}
```

### `check_terminal`

Check that the Open Terminal instance is reachable and report which features (terminal, notebooks, system prompt) are enabled. No parameters.

```json
{}
```

## OpenAQ Air Quality (`openaq`)

JSON para preencher na credencial **Jarvis · OpenAQ Air Quality** (substitua cada valor):

```json
{
  "openaq_api_key": "PREENCHER"
}
```

### `get_air_quality`

Current air quality (PM2.5, PM10, NO2, O3, SO2) at the nearest station. Provide either city (auto-geocoded via Nominatim) or lat+lon. Parameters: city (optional), lat+lon (optional), radius (meters, default 25000, max 25000).

```json
{
  "city": "PREENCHER",
  "lat": "PREENCHER",
  "lon": "PREENCHER",
  "radius": "PREENCHER"
}
```

### `find_stations`

List air quality monitoring stations near a location. Use when the user wants to compare multiple stations or find station IDs for history lookups. Parameters: city (optional), lat+lon (optional), radius (meters, default 25000), limit (default 5, max 20).

```json
{
  "city": "PREENCHER",
  "lat": "PREENCHER",
  "lon": "PREENCHER",
  "radius": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_station_history`

Daily mean values for one parameter at a specific station over the last N days. Parameters: location_id (required, from find_stations), parameter (pm25|pm10|no2|o3|so2|co, default pm25), days (default 7, max 7).

```json
{
  "location_id": "PREENCHER",
  "parameter": "PREENCHER",
  "days": "PREENCHER"
}
```

## OpenClaw (`openclaw`)

JSON para preencher na credencial **Jarvis · OpenClaw** (substitua cada valor):

```json
{
  "openclaw_url": "PREENCHER",
  "openclaw_token": "PREENCHER",
  "openclaw_caller_id": "PREENCHER"
}
```

### `openclaw_send_message`

Send a message to an OpenClaw autonomous AI agent and get the response. Uses the OpenAI-compatible Gateway API. Parameters: message (required, the message to send), session_key (session ID for conversation continuity, default 'n8n-claw' — use a unique key per conversation topic), model (agent ID, default 'openclaw:main'), system_message (optional system prompt to prepend)

```json
{
  "message": "PREENCHER",
  "session_key": "PREENCHER",
  "model": "PREENCHER",
  "system_message": "PREENCHER"
}
```

## OpenFoodFacts (`openfoodfacts`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `lookup_barcode`

Look up a food product by its barcode (EAN-8 or EAN-13). Returns nutrition facts, Nutri-Score, NOVA group, Eco-Score, allergens, ingredients, and labels. Parameter: barcode (the barcode number, required)

```json
{
  "barcode": "PREENCHER"
}
```

### `search_food`

Search for food products by name or keyword. Returns a list of matching products with nutrition facts, Nutri-Score, allergens, and barcodes. Parameters: query (search term like 'Nutella' or 'oat milk', required), limit (number of results 1-10, optional, default 5)

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER"
}
```

## Open Library (`openlibrary`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_books`

Search Open Library's catalog of 40M+ books. Parameters: query (required; title, author, subject, or ISBN), limit (optional, default 5, max 20), sort (optional: relevance|new|old|rating|readinglog|editions).

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER",
  "sort": "PREENCHER"
}
```

### `get_book`

Get detailed info about a specific book (description, subjects, cover, authors). Parameters: work_key (e.g. OL27448W from search_books) OR isbn (10/13 digit ISBN). One of them is required.

```json
{
  "work_key": "PREENCHER",
  "isbn": "PREENCHER"
}
```

### `get_author`

Get author profile with bio, birth/death dates and a list of their works. Parameters: author_key (e.g. OL30351A from search_books) OR name (full name). One of them is required.

```json
{
  "author_key": "PREENCHER",
  "name": "PREENCHER"
}
```

## OpenWebUI Knowledge Manager (`openwebui-knowledge`)

JSON para preencher na credencial **Jarvis · OpenWebUI Knowledge Manager** (substitua cada valor):

```json
{
  "openwebui_url": "PREENCHER",
  "openwebui_api_key": "PREENCHER"
}
```

### `list_knowledge`

List all knowledge collections in OpenWebUI with their IDs, names, descriptions, and file counts.

```json
{}
```

### `create_knowledge`

Create a new knowledge collection in OpenWebUI. Parameters: name (collection name), description (optional description)

```json
{
  "name": "PREENCHER",
  "description": "PREENCHER"
}
```

### `get_knowledge`

Get details of a knowledge collection including its files. Parameters: knowledge_id (collection ID)

```json
{
  "knowledge_id": "PREENCHER"
}
```

### `update_knowledge`

Update name or description of a knowledge collection. Parameters: knowledge_id (collection ID), name (new name, optional), description (new description, optional)

```json
{
  "knowledge_id": "PREENCHER",
  "name": "PREENCHER",
  "description": "PREENCHER"
}
```

### `delete_knowledge`

Delete a knowledge collection from OpenWebUI. Parameters: knowledge_id (collection ID)

```json
{
  "knowledge_id": "PREENCHER"
}
```

### `list_files`

List all uploaded files in OpenWebUI with their IDs, names, sizes, and types.

```json
{}
```

### `upload_file`

Upload a file (PDF, DOCX, TXT, etc.) from a URL into an OpenWebUI knowledge collection. Use this for documents and binary files — NOT for web pages. The file is downloaded, uploaded to OpenWebUI, and its text content is extracted for RAG. Parameters: knowledge_id (collection ID), url (direct download URL for the file), filename (name for the file, e.g. report.pdf)

```json
{
  "knowledge_id": "PREENCHER",
  "url": "PREENCHER",
  "filename": "PREENCHER"
}
```

### `ingest_web_url`

Ingest an HTML web page into an OpenWebUI knowledge collection for RAG. Only use this for actual web pages (HTML) — for files like PDFs, DOCX, images, use upload_file instead. Parameters: knowledge_id (collection ID), url (web page URL to ingest)

```json
{
  "knowledge_id": "PREENCHER",
  "url": "PREENCHER"
}
```

### `add_content`

Write text content directly into an OpenWebUI knowledge collection as a file. Use this to save brainstorming results, summaries, notes, or any generated text into a knowledge base for RAG. Parameters: knowledge_id (collection ID), content (the text to save), filename (optional, default: content.md)

```json
{
  "knowledge_id": "PREENCHER",
  "content": "PREENCHER",
  "filename": "PREENCHER"
}
```

### `remove_file`

Remove a file from an OpenWebUI knowledge collection and delete it. Parameters: knowledge_id (collection ID), file_id (file ID to remove)

```json
{
  "knowledge_id": "PREENCHER",
  "file_id": "PREENCHER"
}
```

## Overpass (OpenStreetMap) (`overpass-osm`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `geocode_place`

Convert a place name, address, or city into latitude/longitude coordinates. Parameters: place (name/address, required). Returns human-readable location + coordinates.

```json
{
  "place": "PREENCHER"
}
```

### `find_nearby`

Find points of interest near a location by category. Parameters: category (required, one of: restaurant, cafe, bar, pub, fast_food, biergarten, hotel, guest_house, hostel, alpine_hut, supermarket, bakery, pharmacy, attraction, museum, gallery, information, parking, fuel, charging_station, atm, toilets, drinking_water, shelter, peak, picnic_site, waterfall, spring, camp_site), lat+lon (decimal coordinates) OR place (name/address to auto-geocode), radius (meters, optional, default 1000), limit (max results, optional, default 15).

```json
{
  "category": "PREENCHER",
  "lat": "PREENCHER",
  "lon": "PREENCHER",
  "place": "PREENCHER",
  "radius": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `reverse_geocode`

Convert latitude/longitude coordinates into a human-readable address (street, district, city). Use this after find_nearby when POIs come back with only coordinates and no addr:street tag (e.g. drinking water fountains, park benches, hiking trail markers). Parameters: lat (required), lon (required). Respects Nominatim 1 req/sec rate limit, so call sparingly (e.g. only for top 2-3 results of interest).

```json
{
  "lat": "PREENCHER",
  "lon": "PREENCHER"
}
```

### `search_custom`

Run a custom Overpass QL query (for advanced queries beyond the presets). Parameters: query (Overpass QL string, required). Example: '[out:json][timeout:25];node[historic=castle](around:5000,48.1,11.5);out;'

```json
{
  "query": "PREENCHER"
}
```

## PDF Tools (pdf-mcp.io) (`pdf-mcp`)

JSON para preencher na credencial **Jarvis · PDF Tools (pdf-mcp.io)** (substitua cada valor):

```json
{
  "pdfmcp_api_key": "PREENCHER"
}
```

### `html_to_pdf`

Generate a PDF from HTML content. The HTML can include full styling, images (as base64 or URLs), tables, etc. Parameters: html (required, full HTML document or fragment), css (optional CSS stylesheet or empty string), filename (optional filename like 'report.pdf' or empty string)

```json
{
  "html": "PREENCHER",
  "css": "PREENCHER",
  "filename": "PREENCHER"
}
```

### `extract_text`

Extract text content from a PDF. Parameter: pdf_url (required, URL of the PDF file), pages (optional, page numbers like '1,2,3' or '1-5' or empty string for all)

```json
{
  "pdf_url": "PREENCHER",
  "pages": "PREENCHER"
}
```

### `merge_pdfs`

Merge multiple PDFs into one. Parameter: pdf_urls (required, comma-separated URLs of PDFs to merge), filename (optional, output filename or empty string)

```json
{
  "pdf_urls": "PREENCHER",
  "filename": "PREENCHER"
}
```

### `list_files`

List stored PDF files. No parameters needed.

```json
{}
```

### `get_file`

Get a download link for a stored PDF. Parameter: document_id (required, the document UUID from html_to_pdf or list_files)

```json
{
  "document_id": "PREENCHER"
}
```

## Public Holidays (`public-holidays`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_public_holidays`

Get public holidays for a country. Parameters: country_code (ISO 3166-1 alpha-2, e.g. DE, US, AT, CH, FR), year (optional, default current year), mode (optional: 'year' for full year or 'next' for upcoming holidays only)

```json
{
  "country_code": "PREENCHER",
  "year": "PREENCHER",
  "mode": "PREENCHER"
}
```

## QR Code Generator (`qr-code`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `generate_qr_code`

Generate a QR code image from text or a URL. Returns an image URL that can be shared. Parameters: data (text or URL to encode into QR code), size (optional, image dimensions like '300x300', default '300x300')

```json
{
  "data": "PREENCHER",
  "size": "PREENCHER"
}
```

## Recipes (`recipes`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_recipe`

Search for recipes by name or keyword. Returns ingredients, instructions, and source. Parameter: query (recipe name like 'pasta', 'chicken curry', 'tiramisu')

```json
{
  "query": "PREENCHER"
}
```

### `random_recipe`

Get a random recipe with full ingredients and instructions. No parameters needed.

```json
{}
```

## Route Planner (OpenRouteService) (`route-planner`)

JSON para preencher na credencial **Jarvis · Route Planner (OpenRouteService)** (substitua cada valor):

```json
{
  "ors_api_key": "PREENCHER"
}
```

### `plan_route`

Plan a route with turn-by-turn directions, duration and GPX data. Best for road/urban routes or when you need navigation instructions. The GPX data after '--- GPX DATA ---' can be saved as a .gpx file. Parameters: start (place name or lat,lon), end (place name or lat,lon), waypoints (optional, semicolon-separated intermediate stops), profile (optional: foot-hiking, foot-walking, cycling-regular, cycling-road, cycling-mountain, cycling-electric; default foot-hiking)

```json
{
  "start": "PREENCHER",
  "end": "PREENCHER",
  "waypoints": "PREENCHER",
  "profile": "PREENCHER"
}
```

### `plan_route_outdoor`

Plan a hiking or cycling route with superior track quality using BRouter. Returns GPX track optimized for trail surfaces and elevation. No turn-by-turn directions — best for nature trails, mountain routes, cycling tours where you follow the GPS track. Parameters: start (place name or lat,lon), end (place name or lat,lon), waypoints (optional, semicolon-separated), profile (optional: trekking, fastbike, trekking-bike, mtb, safety; default trekking)

```json
{
  "start": "PREENCHER",
  "end": "PREENCHER",
  "waypoints": "PREENCHER",
  "profile": "PREENCHER"
}
```

### `search_place`

Geocode a place name or address to get its coordinates. Returns latitude, longitude, region, and country. Useful to verify a location before planning a route. Parameters: query (place name or address), limit (optional, number of results, default 3)

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `find_pois`

Find nearby points of interest. Default categories: alpine huts, viewpoints, drinking water, picnic sites, peaks. Parameters: location (place name or lat,lon), radius (optional, meters, max 2000, default 1500), categories (optional, comma-separated: alpine_hut, camp_site, viewpoint, drinking_water, parking, restaurant, shelter, picnic_site, peak, toilet, bench)

```json
{
  "location": "PREENCHER",
  "radius": "PREENCHER",
  "categories": "PREENCHER"
}
```

### `get_elevation_profile`

Get elevation profile between locations. Shows min/max/avg elevation, total ascent/descent, and an ASCII elevation chart. Parameters: start (place name or lat,lon), end (place name or lat,lon), waypoints (optional, semicolon-separated)

```json
{
  "start": "PREENCHER",
  "end": "PREENCHER",
  "waypoints": "PREENCHER"
}
```

### `get_isochrone`

How far can you get in N minutes from a location? Returns the reachable area size and extent. Parameters: location (place name or lat,lon), time (minutes), profile (optional: foot-hiking, foot-walking, cycling-regular, cycling-road, cycling-mountain, cycling-electric; default foot-hiking)

```json
{
  "location": "PREENCHER",
  "time": "PREENCHER",
  "profile": "PREENCHER"
}
```

### `optimize_route`

Find the optimal order for visiting multiple locations. Returns the best route with total distance and duration. Parameters: locations (semicolon-separated, min 3 locations), profile (optional: foot-hiking, foot-walking, cycling-regular, cycling-road, cycling-mountain, cycling-electric, driving-car; default foot-hiking), start_fixed (optional, keep first location as start, default true), end_fixed (optional, keep last location as end, default false)

```json
{
  "locations": "PREENCHER",
  "profile": "PREENCHER",
  "start_fixed": "PREENCHER",
  "end_fixed": "PREENCHER"
}
```

## Salesforce CRM (`salesforce`)

JSON para preencher na credencial **Jarvis · Salesforce CRM** (substitua cada valor):

```json
{
  "salesforce_instance_url": "PREENCHER",
  "salesforce_consumer_key": "PREENCHER",
  "salesforce_consumer_secret": "PREENCHER"
}
```

### `list_contacts`

List recent Salesforce Contacts.

```json
{
  "limit": "PREENCHER"
}
```

### `search_contacts`

Search Contacts via SOQL WHERE. Default field=Name, operator==, use LIKE with % wildcards.

```json
{
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_contact`

Get a Salesforce Contact by Id.

```json
{
  "contact_id": "PREENCHER"
}
```

### `create_contact`

Create a Salesforce Contact. LastName required.

```json
{
  "LastName": "PREENCHER",
  "FirstName": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Title": "PREENCHER",
  "AccountId": "PREENCHER",
  "MailingCity": "PREENCHER",
  "MailingCountry": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_contact`

Update Salesforce Contact by Id.

```json
{
  "contact_id": "PREENCHER",
  "FirstName": "PREENCHER",
  "LastName": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Title": "PREENCHER",
  "AccountId": "PREENCHER",
  "MailingCity": "PREENCHER",
  "MailingCountry": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_contact`

Delete Salesforce Contact by Id (to Recycle Bin).

```json
{
  "contact_id": "PREENCHER"
}
```

### `list_accounts`

List recent Salesforce Accounts (companies).

```json
{
  "limit": "PREENCHER"
}
```

### `search_accounts`

Search Accounts via SOQL. Default field=Name.

```json
{
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_account`

Get a Salesforce Account by Id.

```json
{
  "account_id": "PREENCHER"
}
```

### `create_account`

Create Salesforce Account. Name required.

```json
{
  "Name": "PREENCHER",
  "Phone": "PREENCHER",
  "Website": "PREENCHER",
  "Industry": "PREENCHER",
  "BillingCity": "PREENCHER",
  "BillingCountry": "PREENCHER",
  "Description": "PREENCHER",
  "NumberOfEmployees": "PREENCHER",
  "AnnualRevenue": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_account`

Update Salesforce Account by Id.

```json
{
  "account_id": "PREENCHER",
  "Name": "PREENCHER",
  "Phone": "PREENCHER",
  "Website": "PREENCHER",
  "Industry": "PREENCHER",
  "BillingCity": "PREENCHER",
  "BillingCountry": "PREENCHER",
  "Description": "PREENCHER",
  "NumberOfEmployees": "PREENCHER",
  "AnnualRevenue": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_account`

Delete Salesforce Account by Id.

```json
{
  "account_id": "PREENCHER"
}
```

### `list_leads`

List recent Salesforce Leads. Unconverted by default.

```json
{
  "limit": "PREENCHER",
  "include_converted": "PREENCHER"
}
```

### `search_leads`

Search Leads via SOQL. Default field=Name.

```json
{
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_lead`

Get a Salesforce Lead by Id.

```json
{
  "lead_id": "PREENCHER"
}
```

### `create_lead`

Create Salesforce Lead. LastName + Company required.

```json
{
  "LastName": "PREENCHER",
  "Company": "PREENCHER",
  "FirstName": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Title": "PREENCHER",
  "Status": "PREENCHER",
  "LeadSource": "PREENCHER",
  "Rating": "PREENCHER",
  "Industry": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_lead`

Update Salesforce Lead by Id.

```json
{
  "lead_id": "PREENCHER",
  "FirstName": "PREENCHER",
  "LastName": "PREENCHER",
  "Company": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Title": "PREENCHER",
  "Status": "PREENCHER",
  "LeadSource": "PREENCHER",
  "Rating": "PREENCHER",
  "Industry": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_lead`

Delete Salesforce Lead by Id. Note: Lead conversion via REST is edition-dependent — use SF UI Convert button.

```json
{
  "lead_id": "PREENCHER"
}
```

### `list_opportunities`

List recent Salesforce Opportunities.

```json
{
  "limit": "PREENCHER",
  "open_only": "PREENCHER"
}
```

### `search_opportunities`

Search Opportunities via SOQL. Default field=Name.

```json
{
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_opportunity`

Get a Salesforce Opportunity by Id.

```json
{
  "opportunity_id": "PREENCHER"
}
```

### `create_opportunity`

Create Salesforce Opportunity. Name + StageName + CloseDate required.

```json
{
  "Name": "PREENCHER",
  "StageName": "PREENCHER",
  "CloseDate": "PREENCHER",
  "Amount": "PREENCHER",
  "AccountId": "PREENCHER",
  "Probability": "PREENCHER",
  "Type": "PREENCHER",
  "LeadSource": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_opportunity`

Update Salesforce Opportunity by Id.

```json
{
  "opportunity_id": "PREENCHER",
  "Name": "PREENCHER",
  "StageName": "PREENCHER",
  "CloseDate": "PREENCHER",
  "Amount": "PREENCHER",
  "AccountId": "PREENCHER",
  "Probability": "PREENCHER",
  "Type": "PREENCHER",
  "LeadSource": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_opportunity`

Delete Salesforce Opportunity by Id.

```json
{
  "opportunity_id": "PREENCHER"
}
```

### `list_cases`

List recent Salesforce Cases (Service Cloud).

```json
{
  "limit": "PREENCHER",
  "open_only": "PREENCHER"
}
```

### `get_case`

Get a Salesforce Case by Id.

```json
{
  "case_id": "PREENCHER"
}
```

### `create_case`

Create Salesforce Case. Subject required.

```json
{
  "Subject": "PREENCHER",
  "Description": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "Origin": "PREENCHER",
  "ContactId": "PREENCHER",
  "AccountId": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_case`

Update Salesforce Case by Id.

```json
{
  "case_id": "PREENCHER",
  "Subject": "PREENCHER",
  "Description": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "Origin": "PREENCHER",
  "ContactId": "PREENCHER",
  "AccountId": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_case`

Delete Salesforce Case by Id.

```json
{
  "case_id": "PREENCHER"
}
```

### `list_tasks`

List recent Salesforce Tasks.

```json
{
  "limit": "PREENCHER",
  "open_only": "PREENCHER",
  "who_id": "PREENCHER"
}
```

### `create_task`

Create Salesforce Task. Subject required.

```json
{
  "Subject": "PREENCHER",
  "Description": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "ActivityDate": "PREENCHER",
  "WhoId": "PREENCHER",
  "WhatId": "PREENCHER",
  "OwnerId": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_task`

Update Salesforce Task by Id.

```json
{
  "task_id": "PREENCHER",
  "Subject": "PREENCHER",
  "Description": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "ActivityDate": "PREENCHER",
  "WhoId": "PREENCHER",
  "WhatId": "PREENCHER",
  "OwnerId": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `soql_query`

Run a custom SOQL query. Param: query (full SOQL string).

```json
{
  "query": "PREENCHER"
}
```

### `sosl_search`

Full-text search across multiple SObjects via SOSL.

```json
{
  "query": "PREENCHER",
  "sobjects": "PREENCHER"
}
```

### `describe_object`

Get schema metadata (fields, types, picklist values) for an SObject.

```json
{
  "object_type": "PREENCHER"
}
```

## SBB (`sbb`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_station`

Search for a Swiss train station by name (SBB/CFF/FFS). Returns station names and IDs. Parameter: query (station name to search for, e.g. 'Zürich HB')

```json
{
  "query": "PREENCHER"
}
```

### `get_departures`

Get upcoming departures from a Swiss train station (SBB). Accepts station name or ID. Parameters: station (e.g. 'Zürich HB'), results (optional, number of entries, default 10)

```json
{
  "station": "PREENCHER",
  "results": "PREENCHER"
}
```

### `get_arrivals`

Get upcoming arrivals at a Swiss train station (SBB). Accepts station name or ID. Parameters: station (e.g. 'Bern'), results (optional, number of entries, default 10)

```json
{
  "station": "PREENCHER",
  "results": "PREENCHER"
}
```

### `search_journey`

Search for Swiss train connections between two stations (SBB). Accepts station names or IDs. Parameters: from (origin, e.g. 'Zürich HB'), to (destination, e.g. 'Bern'), departure (optional, ISO 8601 datetime), results (optional, number of connections, default 3)

```json
{
  "from": "PREENCHER",
  "to": "PREENCHER",
  "departure": "PREENCHER",
  "results": "PREENCHER"
}
```

## Seafile (`seafile`)

JSON para preencher na credencial **Jarvis · Seafile** (substitua cada valor):

```json
{
  "seafile_url": "PREENCHER",
  "seafile_token": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `repo_info`

Get info about the connected Seafile library (name, size, file count, last modified)

```json
{}
```

### `list_directory`

List files and folders in a Seafile directory. Parameters: path (directory path, optional, default '/')

```json
{
  "path": "PREENCHER"
}
```

### `get_file_detail`

Get metadata for a file (size, last modified, type). Parameters: path (file path, required, e.g. /docs/readme.md)

```json
{
  "path": "PREENCHER"
}
```

### `download_file`

Get a file download link or read text file content inline. For text files (.txt, .md, .json, .csv, etc.) returns content directly. For binary files returns a download URL. Parameters: path (file path, required)

```json
{
  "path": "PREENCHER"
}
```

### `upload_file`

Upload a binary file to Seafile. IMPORTANT: For files the user sent via Telegram, use file_ref (the ID from the message, e.g. file-abc12345) — do NOT use file_url for stored files. file_url is ONLY for external URLs not from File Bridge. Parameters: path (destination path, required), file_ref (File Bridge ID — preferred for user-sent files), file_url (external URL only)

```json
{
  "path": "PREENCHER",
  "file_ref": "PREENCHER",
  "file_url": "PREENCHER",
  "replace": "PREENCHER"
}
```

### `create_file`

Create a text file in Seafile (overwrites if it already exists). Parameters: path (full file path including filename, required, e.g. /notes/todo.md), content (file content, required)

```json
{
  "path": "PREENCHER",
  "content": "PREENCHER",
  "replace": "PREENCHER"
}
```

### `delete_file`

Delete a file or directory. Parameters: path (file/folder path, required), is_dir ('true' if deleting a directory, optional)

```json
{
  "path": "PREENCHER",
  "is_dir": "PREENCHER"
}
```

### `file_operation`

Rename, move, or copy a file. Parameters: path (source file path, required), operation ('rename', 'move', or 'copy', required). For rename: newname (new filename, required). For move/copy: dst_dir (destination directory path, required)

```json
{
  "path": "PREENCHER",
  "operation": "PREENCHER",
  "newname": "PREENCHER",
  "dst_dir": "PREENCHER"
}
```

## Shopify (`shopify`)

JSON para preencher na credencial **Jarvis · Shopify** (substitua cada valor):

```json
{
  "shopify_store": "PREENCHER",
  "shopify_access_token": "PREENCHER"
}
```

### `list_products`

List Shopify products. Optional: search (Shopify query, e.g. 'title:shirt' or 'status:active'), limit (default 20, max 100), cursor (for pagination).

```json
{
  "search": "PREENCHER",
  "limit": "PREENCHER",
  "cursor": "PREENCHER"
}
```

### `get_product`

Get full details of a single Shopify product including variants, prices, inventory quantities, and inventory_item_ids.

```json
{
  "id": "PREENCHER"
}
```

### `create_product`

Create a new Shopify product. Required: title. Optional: description, vendor, product_type, status (DRAFT/ACTIVE/ARCHIVED), tags (comma-separated), price (default variant).

```json
{
  "title": "PREENCHER",
  "description": "PREENCHER",
  "vendor": "PREENCHER",
  "product_type": "PREENCHER",
  "status": "PREENCHER",
  "tags": "PREENCHER",
  "price": "PREENCHER"
}
```

### `update_product`

Update an existing Shopify product. Required: id. Provide at least one field to update: title, description, vendor, product_type, status, tags, price.

```json
{
  "id": "PREENCHER",
  "title": "PREENCHER",
  "description": "PREENCHER",
  "vendor": "PREENCHER",
  "product_type": "PREENCHER",
  "status": "PREENCHER",
  "tags": "PREENCHER",
  "price": "PREENCHER"
}
```

### `delete_product`

Permanently delete a Shopify product. Required: id. Cannot be undone.

```json
{
  "id": "PREENCHER"
}
```

### `list_orders`

List Shopify orders. Optional: search (Shopify query, e.g. 'financial_status:paid' or 'tag:priority'), limit (default 20, max 100), cursor.

```json
{
  "search": "PREENCHER",
  "limit": "PREENCHER",
  "cursor": "PREENCHER"
}
```

### `get_order`

Get full details of a single Shopify order: line items (with line_item_id), customer, fulfillment status, totals. Use line_item_id for edit_order_quantity.

```json
{
  "id": "PREENCHER"
}
```

### `update_order`

Update an order's tags or internal note (metadata only — to change quantities use edit_order_quantity).

```json
{
  "id": "PREENCHER",
  "tags": "PREENCHER",
  "note": "PREENCHER"
}
```

### `edit_order_quantity`

Change the quantity of a line item on an existing order. Wraps orderEditBegin → orderEditSetQuantity → orderEditCommit. Get line_item_id from get_order first.

```json
{
  "id": "PREENCHER",
  "line_item_id": "PREENCHER",
  "quantity": "PREENCHER"
}
```

### `create_fulfillment`

Mark an order as fulfilled (ship all open fulfillment orders). Optional: tracking_number, tracking_company (e.g. DHL, UPS), tracking_url, notify_customer.

```json
{
  "order_id": "PREENCHER",
  "tracking_number": "PREENCHER",
  "tracking_company": "PREENCHER",
  "tracking_url": "PREENCHER",
  "notify_customer": "PREENCHER"
}
```

### `list_customers`

List Shopify customers. Optional: search (Shopify query, e.g. 'email:example.com' or 'tag:vip'), limit (default 20, max 100), cursor.

```json
{
  "search": "PREENCHER",
  "limit": "PREENCHER",
  "cursor": "PREENCHER"
}
```

### `create_customer`

Create a new customer. At least one of email or phone is required. Optional: first_name, last_name, note, tags.

```json
{
  "email": "PREENCHER",
  "phone": "PREENCHER",
  "first_name": "PREENCHER",
  "last_name": "PREENCHER",
  "note": "PREENCHER",
  "tags": "PREENCHER"
}
```

### `update_customer`

Update an existing customer's fields. Required: id. Provide at least one field to update.

```json
{
  "id": "PREENCHER",
  "email": "PREENCHER",
  "phone": "PREENCHER",
  "first_name": "PREENCHER",
  "last_name": "PREENCHER",
  "note": "PREENCHER",
  "tags": "PREENCHER"
}
```

### `adjust_inventory`

Adjust inventory by a delta (positive = increase, negative = decrease). Required: inventory_item_id (from get_product variants), delta. Auto-picks location if only one exists.

```json
{
  "inventory_item_id": "PREENCHER",
  "delta": "PREENCHER",
  "location_id": "PREENCHER"
}
```

## Stripe (`stripe`)

JSON para preencher na credencial **Jarvis · Stripe** (substitua cada valor):

```json
{
  "stripe_api_key": "PREENCHER"
}
```

### `list_customers`

List recent customers. Parameters: limit (optional default 10).

```json
{
  "limit": "PREENCHER"
}
```

### `search_customers`

Search customers with Stripe search syntax. Examples: email:"x@y.com", name:"Acme", metadata["order_id"]:"123". Parameters: query (required), limit (optional).

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_customer`

Get a customer by id. Parameters: customer_id (required, cus_...).

```json
{
  "customer_id": "PREENCHER"
}
```

### `create_customer`

Create a new customer. At least one of name/email required. Parameters: name, email, phone, description (all optional but at least one required).

```json
{
  "name": "PREENCHER",
  "email": "PREENCHER",
  "phone": "PREENCHER",
  "description": "PREENCHER"
}
```

### `update_customer`

Update fields on a customer. Parameters: customer_id (required), name/email/phone/description (any subset).

```json
{
  "customer_id": "PREENCHER",
  "name": "PREENCHER",
  "email": "PREENCHER",
  "phone": "PREENCHER",
  "description": "PREENCHER"
}
```

### `list_payments`

List PaymentIntents (modern payment flow). Parameters: limit (optional), customer_id (optional filter).

```json
{
  "limit": "PREENCHER",
  "customer_id": "PREENCHER"
}
```

### `get_payment`

Get a PaymentIntent by id. Parameters: payment_id (required, pi_...).

```json
{
  "payment_id": "PREENCHER"
}
```

### `list_charges`

List charges (legacy — still populated alongside PaymentIntents). Parameters: limit, customer_id (optional).

```json
{
  "limit": "PREENCHER",
  "customer_id": "PREENCHER"
}
```

### `list_invoices`

List invoices. Parameters: limit, customer_id (optional), status (optional: draft, open, paid, void, uncollectible).

```json
{
  "limit": "PREENCHER",
  "customer_id": "PREENCHER",
  "status": "PREENCHER"
}
```

### `get_invoice`

Get invoice by id. Parameters: invoice_id (required, in_...).

```json
{
  "invoice_id": "PREENCHER"
}
```

### `create_invoice`

Create a DRAFT invoice for a customer. Line items must be added separately via the Stripe dashboard or API. Parameters: customer_id (required), description (optional), days_until_due (optional).

```json
{
  "customer_id": "PREENCHER",
  "description": "PREENCHER",
  "days_until_due": "PREENCHER"
}
```

### `list_subscriptions`

List subscriptions. Parameters: limit, customer_id (optional), status (optional: active, canceled, past_due, trialing, all).

```json
{
  "limit": "PREENCHER",
  "customer_id": "PREENCHER",
  "status": "PREENCHER"
}
```

### `get_subscription`

Get subscription by id. Parameters: subscription_id (required, sub_...).

```json
{
  "subscription_id": "PREENCHER"
}
```

### `cancel_subscription`

Cancel a subscription IMMEDIATELY. On live mode this stops recurring billing — confirm with user before calling. Parameters: subscription_id (required, sub_...).

```json
{
  "subscription_id": "PREENCHER"
}
```

### `list_products`

List products. Parameters: limit, active (optional, default 'true'; set 'false' to show archived).

```json
{
  "limit": "PREENCHER",
  "active": "PREENCHER"
}
```

### `list_prices`

List prices. Parameters: limit, product_id (optional filter), active (optional).

```json
{
  "limit": "PREENCHER",
  "product_id": "PREENCHER",
  "active": "PREENCHER"
}
```

### `list_refunds`

List refunds. Parameters: limit, charge_id (optional), payment_intent_id (optional).

```json
{
  "limit": "PREENCHER",
  "charge_id": "PREENCHER",
  "payment_intent_id": "PREENCHER"
}
```

### `create_refund`

Refund a charge or payment_intent. On LIVE keys this moves real money — confirm with user before calling. Parameters: charge_id OR payment_intent_id (one required), amount (optional, minor units e.g. 500 = €5.00; omit for full refund), reason (optional: duplicate, fraudulent, requested_by_customer).

```json
{
  "charge_id": "PREENCHER",
  "payment_intent_id": "PREENCHER",
  "amount": "PREENCHER",
  "reason": "PREENCHER"
}
```

### `get_balance`

Current Stripe account balance (available + pending per currency). No parameters.

```json
{}
```

### `list_balance_transactions`

List balance transactions (net amounts after Stripe fees — actual money movement). Parameters: limit, type (optional: charge, refund, payout, adjustment, fee, ...).

```json
{
  "limit": "PREENCHER",
  "type": "PREENCHER"
}
```

### `list_payouts`

List payouts to your bank account. Parameters: limit (optional).

```json
{
  "limit": "PREENCHER"
}
```

### `list_disputes`

List chargebacks and disputes. Parameters: limit (optional).

```json
{
  "limit": "PREENCHER"
}
```

### `create_payment_link`

Create a reusable hosted checkout URL for a given Stripe price. Great for quick invoicing. Parameters: price_id (required, price_...), quantity (optional default 1).

```json
{
  "price_id": "PREENCHER",
  "quantity": "PREENCHER"
}
```

## TikTok Ads (`tiktok-ads`)

JSON para preencher na credencial **Jarvis · TikTok Ads** (substitua cada valor):

```json
{
  "auth_token": "PREENCHER"
}
```

Ponte MCP: https://tiktok-ads.mcp.pipeboard.co/. Os argumentos seguem o schema publicado pelo provedor.

- `list_tiktok_advertisers`
- `get_tiktok_advertiser_info`
- `get_tiktok_campaigns`
- `create_tiktok_campaign`
- `update_tiktok_campaign`
- `update_tiktok_campaign_status`
- `get_tiktok_adgroups`
- `create_tiktok_adgroup`
- `update_tiktok_adgroup`
- `update_tiktok_adgroup_status`
- `get_tiktok_ads`
- `create_tiktok_ad`
- `update_tiktok_ad`
- `update_tiktok_ad_status`
- `get_tiktok_insights`
- `get_tiktok_integrated_report`
- `create_tiktok_report_task`
- `check_tiktok_report_task`
- `cancel_tiktok_report_task`
- `get_tiktok_targeting_regions`
- `get_tiktok_interest_categories`
- `upload_tiktok_image`
- `upload_tiktok_video`
- `get_tiktok_video_info`
- `list_tiktok_pixels`
- `get_tiktok_pixel_event_stats`
- `get_tiktok_identities`
- `create_tiktok_identity`
- `get_tiktok_identity_videos`
- `create_tiktok_catalog`
- `get_tiktok_catalogs`
- `update_tiktok_catalog`
- `get_tiktok_catalog_overview`
- `get_tiktok_catalog_feeds`
- `upload_tiktok_catalog_products`
- `delete_tiktok_catalog_products`
- `get_tiktok_gmv_max_campaign_info`
- `get_tiktok_gmv_max_insights`
- `create_tiktok_smart_plus_campaign`
- `get_tiktok_smart_plus_campaigns`
- `update_tiktok_smart_plus_campaign`
- `update_tiktok_smart_plus_campaign_status`
- `create_tiktok_smart_plus_adgroup`
- `get_tiktok_smart_plus_adgroups`
- `update_tiktok_smart_plus_adgroup`
- `update_tiktok_smart_plus_adgroup_status`
- `create_tiktok_smart_plus_ad`
- `get_tiktok_smart_plus_ads`
- `update_tiktok_smart_plus_ad`
- `update_tiktok_smart_plus_ad_status`
- `update_tiktok_smart_plus_ad_material_status`
- `appeal_tiktok_smart_plus_ad`
- `list_tiktok_custom_audiences`
- `create_tiktok_custom_audience`
- `create_tiktok_lookalike_audience`
- `update_tiktok_custom_audience`
- `delete_tiktok_custom_audiences`
- `share_tiktok_custom_audience`
- `upload_tiktok_customer_file_audience`
- `submit_feedback`

## Timezone & World Clock (`timezone-world-clock`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_time`

Get current date and time in a specific timezone. Parameter: timezone (IANA timezone like 'Europe/Berlin', 'America/New_York', or city name like 'Tokyo', 'London', or abbreviation like 'CET', 'EST')

```json
{
  "timezone": "PREENCHER"
}
```

### `convert_timezone`

Convert a date/time from one timezone to another. Parameters: from_timezone (source timezone), to_timezone (target timezone), datetime (format: YYYY-MM-DD HH:MM:SS)

```json
{
  "from_timezone": "PREENCHER",
  "to_timezone": "PREENCHER",
  "datetime": "PREENCHER"
}
```

## TMDB Movies & TV (`tmdb-movies`)

JSON para preencher na credencial **Jarvis · TMDB Movies & TV** (substitua cada valor):

```json
{
  "tmdb_api_key": "PREENCHER"
}
```

### `search_movie`

Search for movies by title. Parameters: query (movie title, required), year (release year to filter, optional)

```json
{
  "query": "PREENCHER",
  "year": "PREENCHER"
}
```

### `search_tv`

Search for TV shows by title. Parameter: query (TV show title, required)

```json
{
  "query": "PREENCHER"
}
```

### `get_trending`

Get trending movies and TV shows. Parameters: media_type ('movie', 'tv', or 'all', optional, default 'all'), time_window ('day' or 'week', optional, default 'week')

```json
{
  "media_type": "PREENCHER",
  "time_window": "PREENCHER"
}
```

## Todoist (`todoist`)

JSON para preencher na credencial **Jarvis · Todoist** (substitua cada valor):

```json
{
  "todoist_token": "PREENCHER"
}
```

### `list_tasks`

List tasks from Todoist. Parameters: project_id (project ID to filter by, or empty string for all), filter (Todoist filter expression like 'today', 'overdue', 'p1', or empty string for all)

```json
{
  "project_id": "PREENCHER",
  "filter": "PREENCHER"
}
```

### `create_task`

Create a new task in Todoist. Parameters: content (task title, required), description (task details or empty string), due_string (natural language due date like 'tomorrow'/'next Monday' or empty string), priority (1-4 where 4=P1/highest, or empty string for default), project_id (project ID or empty string for inbox), labels (comma-separated label names or empty string)

```json
{
  "content": "PREENCHER",
  "description": "PREENCHER",
  "due_string": "PREENCHER",
  "priority": "PREENCHER",
  "project_id": "PREENCHER",
  "labels": "PREENCHER"
}
```

### `complete_task`

Mark a Todoist task as completed. Parameter: task_id (the task ID, required — get IDs from list_tasks)

```json
{
  "task_id": "PREENCHER"
}
```

### `list_projects`

List all Todoist projects with their IDs. No parameters needed.

```json
{}
```

## Trivia (`trivia`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_trivia`

Get random trivia questions with answers. Parameters: amount (number of questions, 1-10, default 1), category (optional, e.g. 'science', 'history', 'geography', 'sports', 'art', 'music', 'film', 'animals', 'computers', 'mathematics', 'general'), difficulty (optional: 'easy', 'medium', 'hard')

```json
{
  "amount": "PREENCHER",
  "category": "PREENCHER",
  "difficulty": "PREENCHER"
}
```

## Unsplash (`unsplash`)

JSON para preencher na credencial **Jarvis · Unsplash** (substitua cada valor):

```json
{
  "unsplash_access_key": "PREENCHER"
}
```

### `search_photos`

Search Unsplash for free photos matching a keyword. Returns image URLs plus photographer attribution. Parameters: query (required), limit (optional, default 5, max 20), orientation (optional: landscape|portrait|squarish).

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER",
  "orientation": "PREENCHER"
}
```

### `get_random_photo`

Get a single random Unsplash photo. Parameters: query (optional topic filter), orientation (optional: landscape|portrait|squarish).

```json
{
  "query": "PREENCHER",
  "orientation": "PREENCHER"
}
```

### `get_photo`

Get detailed info about a specific Unsplash photo including tags, dimensions, likes, and location. Parameters: photo_id (required, e.g. eAAjKAGEKmI).

```json
{
  "photo_id": "PREENCHER"
}
```

## Vexa Meetings (`vexa-meetings`)

JSON para preencher na credencial **Jarvis · Vexa Meetings** (substitua cada valor):

```json
{
  "vexa_api_key": "PREENCHER",
  "vexa_tx_key": "PREENCHER"
}
```

### `deploy_meeting_bot`

Deploy a transcription bot to a Google Meet, Teams, or Zoom meeting. The bot joins and transcribes the conversation. IMPORTANT for Microsoft Teams: the bot cannot join without the passcode, so pass the FULL invitation link (it ends in "?p=...") or supply the passcode parameter separately. Parameters: meeting_url (required), passcode (Teams/Zoom, if not already in the URL), language (optional ISO code such as en or de, auto-detected when omitted), bot_name (optional display name), recording (optional true/false). Returns a Vexa run ID; remember it and pass it to get_transcript as vexa_run_id, otherwise a recurring meeting can return the wrong session.

```json
{
  "meeting_url": "PREENCHER",
  "language": "PREENCHER",
  "bot_name": "PREENCHER",
  "recording": "PREENCHER",
  "passcode": "PREENCHER"
}
```

### `get_transcript`

Get the transcript of a meeting, grouped into speaker blocks with timestamps. CRITICAL: a recurring Teams or Zoom meeting reuses the same meeting ID for every session, and Vexa only ever serves the MOST RECENT run for a meeting ID. Always pass vexa_run_id, which deploy_meeting_bot returned when the bot was sent in; the tool then refuses rather than hand back a different session. Without it you may silently receive another meeting. Parameters: platform (google_meet/teams/zoom) and meeting_id, OR meeting_url; vexa_run_id (strongly recommended); from_time and to_time (HH:MM) to read part of a long meeting.

```json
{
  "platform": "PREENCHER",
  "meeting_id": "PREENCHER",
  "meeting_url": "PREENCHER",
  "from_time": "PREENCHER",
  "to_time": "PREENCHER",
  "vexa_run_id": "PREENCHER"
}
```

### `share_transcript`

Create a public, time limited link to a meeting transcript. Anyone holding the link can read the transcript until it expires, so only use it when the user explicitly asks to share. Parameters: platform and meeting_id, OR meeting_url.

```json
{
  "platform": "PREENCHER",
  "meeting_id": "PREENCHER",
  "meeting_url": "PREENCHER"
}
```

### `list_bots`

List all bots that are currently running in meetings, with their platform, meeting ID and status.

```json
{}
```

### `stop_bot`

Stop a running bot and make it leave the meeting. Parameters: platform and meeting_id, OR meeting_url.

```json
{
  "platform": "PREENCHER",
  "meeting_id": "PREENCHER",
  "meeting_url": "PREENCHER"
}
```

## Vikunja (`vikunja`)

JSON para preencher na credencial **Jarvis · Vikunja** (substitua cada valor):

```json
{
  "vikunja_url": "PREENCHER",
  "vikunja_token": "PREENCHER"
}
```

### `vikunja_list_projects`

List all Vikunja projects with their IDs. No parameters needed.

```json
{}
```

### `vikunja_list_tasks`

List tasks in a Vikunja project. Parameters: project_id (required, from vikunja_list_projects), page (page number, default 1), per_page (tasks per page, default 20), sort_by (field to sort by like 'due_date' or 'priority'), order_by ('asc' or 'desc')

```json
{
  "project_id": "PREENCHER",
  "page": "PREENCHER",
  "per_page": "PREENCHER",
  "sort_by": "PREENCHER",
  "order_by": "PREENCHER"
}
```

### `vikunja_get_task`

Get details of a single Vikunja task. Parameters: task_id (required)

```json
{
  "task_id": "PREENCHER"
}
```

### `vikunja_create_task`

Create a new task in a Vikunja project. Parameters: project_id (required), title (required), description (task details), due_date (ISO format like '2026-04-01T12:00:00Z'), priority (0=unset, 1=low, 2=medium, 3=high, 4=urgent)

```json
{
  "project_id": "PREENCHER",
  "title": "PREENCHER",
  "description": "PREENCHER",
  "due_date": "PREENCHER",
  "priority": "PREENCHER"
}
```

### `vikunja_update_task`

Update an existing Vikunja task. Parameters: task_id (required), title (new title), description (new description), due_date (new due date in ISO format), done ('true' or 'false' to change completion), priority (0-4)

```json
{
  "task_id": "PREENCHER",
  "title": "PREENCHER",
  "description": "PREENCHER",
  "due_date": "PREENCHER",
  "done": "PREENCHER",
  "priority": "PREENCHER"
}
```

### `vikunja_delete_task`

Delete a Vikunja task. Parameters: task_id (required)

```json
{
  "task_id": "PREENCHER"
}
```

## Weather (Open-Meteo) (`weather-openmeteo`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `get_weather`

Current weather and daily forecast for a city: temperature, feels-like, conditions, precipitation amount and probability, wind and gusts, UV index, sunrise/sunset, snowfall. Parameters: city (required), days (optional, 1-16, default 3)

```json
{
  "city": "PREENCHER",
  "days": "PREENCHER"
}
```

### `get_hourly_forecast`

Hour-by-hour weather forecast for a city: temperature, feels-like, rain probability and amount, conditions, wind, UV, humidity, cloud cover. Parameters: city (required), hours (optional, next 1-48 hours, default 24), date (optional, YYYY-MM-DD within the next 16 days, returns that full day instead)

```json
{
  "city": "PREENCHER",
  "hours": "PREENCHER",
  "date": "PREENCHER"
}
```

### `get_air_quality`

Current model-based air quality and pollen for a city: European and US AQI, PM2.5, PM10, ozone, NO2, SO2, UV index, and pollen levels (alder, birch, grass, mugwort, olive, ragweed; pollen data Europe only). Parameter: city (required)

```json
{
  "city": "PREENCHER"
}
```

### `get_weather_history`

Historical daily weather for a city from the archive (data since 1940): conditions, min/max temperature, precipitation, wind. Parameters: city, start_date, end_date (YYYY-MM-DD, past dates only, max 31 days per call; the archive lags about 5 days behind)

```json
{
  "city": "PREENCHER",
  "start_date": "PREENCHER",
  "end_date": "PREENCHER"
}
```

### `get_marine_weather`

Sea/marine conditions for a coastal location: current wave height, wave direction, wave period, sea surface temperature, plus a daily max-wave forecast. Parameters: city (required, must be coastal), days (optional, 1-7, default 3)

```json
{
  "city": "PREENCHER",
  "days": "PREENCHER"
}
```

### `get_weather_alerts`

Official weather warnings for a European city from national weather services (MeteoAlarm; Germany via DWD/Bright Sky). Returns active alerts matching the city/region, or a country-level summary. Parameter: city (required). Europe only

```json
{
  "city": "PREENCHER"
}
```

## Website Check (`website-check`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `check_website`

Comprehensive website health check. Measures load time (10 requests), checks security headers, extracts meta tags and Open Graph data, checks for JSON-LD structured data, robots.txt, and server info. Parameter: url (website URL to check)

```json
{
  "url": "PREENCHER"
}
```

## wger Exercises (`wger-exercises`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_exercises`

Search the wger exercise database (845+ exercises). Filter by muscle group, equipment, category, language. Returns a list with exercise IDs you can pass to get_exercise. Parameters: muscles (muscle ID from list_muscles, optional), equipment (equipment ID from list_equipment, optional), category (category ID from list_categories, optional), name (free-text name to bias ranking, optional), language (de/en/es/fr/it, optional, default en), limit (1-50, optional, default 10)

```json
{
  "muscles": "PREENCHER",
  "equipment": "PREENCHER",
  "category": "PREENCHER",
  "name": "PREENCHER",
  "language": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_exercise`

Get the full details of one exercise by its wger ID — name, description (instructions), aliases, primary/secondary muscles, equipment, and image URLs. Parameters: exercise_id (integer ID from search_exercises, required), language (de/en/es/fr/it, optional, default en)

```json
{
  "exercise_id": "PREENCHER",
  "language": "PREENCHER"
}
```

### `list_categories`

List all wger exercise categories with their IDs (Arms, Legs, Cardio, Chest, Back, Shoulders, Abs). Use these IDs in search_exercises (parameter: category). No parameters.

```json
{}
```

### `list_muscles`

List all muscle groups available for filtering with their IDs (e.g. Quadriceps femoris, Pectoralis major, Latissimus dorsi). Use these IDs in search_exercises (parameter: muscles). No parameters.

```json
{}
```

### `list_equipment`

List all equipment types with their IDs (Barbell, Dumbbell, Bodyweight, Pull-up bar, etc.). Use these IDs in search_exercises (parameter: equipment). No parameters.

```json
{}
```

### `list_public_templates`

List public workout routine templates available on wger (Stronglifts 5x5, Push-Pull-Legs, Starting Strength, etc.). Returns templates with IDs you can pass to get_template_detail. Parameter: limit (1-50, optional, default 20)

```json
{
  "limit": "PREENCHER"
}
```

### `get_template_detail`

Get the full structure of a public workout template — all sessions/days with exercises, sets, reps, and weight prescriptions. Returns both human-readable text and raw JSON in 'raw' for programmatic import. Parameter: template_id (integer ID from list_public_templates, required)

```json
{
  "template_id": "PREENCHER"
}
```

## Wiener Linien (`wiener-linien`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `create_route_public_transport_vienna`

Create a routing plan with the Vienna public transport system. Provide a destination address (street and house number, no zip code, no city) and the arrival time (when the user should arrive). Parameters: destination_address (street and house number), arrival_time (time in HH:MM:SS format), start_station_id (optional, defaults to Gasometer)

```json
{
  "destination_address": "PREENCHER",
  "arrival_time": "PREENCHER",
  "start_station_id": "PREENCHER"
}
```

## Wikipedia (`wikipedia`)

Configuração da credencial: `{}`. Preserve a chave do estado gerada pelo instalador.

### `search_wikipedia`

Search Wikipedia and get article summaries. Parameter: query (search term)

```json
{
  "query": "PREENCHER"
}
```

## WordPress (`wordpress`)

JSON para preencher na credencial **Jarvis · WordPress** (substitua cada valor):

```json
{
  "wp_url": "PREENCHER",
  "wp_username": "PREENCHER",
  "wp_app_password": "PREENCHER"
}
```

Arquivos usam o cofre interno cifrado: até 10 MB por arquivo, 200 MB no cache, expiração de 24 horas. Não há porta pública de arquivos.

### `list_posts`

List WordPress posts. Optional filters: search (keyword), status (publish/draft/pending/private), per_page (default 10, max 100), page (pagination).

```json
{
  "search": "PREENCHER",
  "status": "PREENCHER",
  "per_page": "PREENCHER",
  "page": "PREENCHER"
}
```

### `get_post`

Get a single WordPress post by ID (full content, status, author, categories, tags).

```json
{
  "id": "PREENCHER"
}
```

### `create_post`

Create a new WordPress post. Default status is 'draft'. Categories/tags are comma-separated lists of IDs (use list_categories/list_tags to find IDs). Content accepts HTML.

```json
{
  "title": "PREENCHER",
  "content": "PREENCHER",
  "status": "PREENCHER",
  "excerpt": "PREENCHER",
  "categories": "PREENCHER",
  "tags": "PREENCHER"
}
```

### `update_post`

Update a WordPress post (provide only fields you want to change). Use status='publish' to publish a draft.

```json
{
  "id": "PREENCHER",
  "title": "PREENCHER",
  "content": "PREENCHER",
  "status": "PREENCHER",
  "excerpt": "PREENCHER",
  "categories": "PREENCHER",
  "tags": "PREENCHER"
}
```

### `delete_post`

Delete a post. Without force it goes to trash (recoverable). With force=true it's permanently deleted.

```json
{
  "id": "PREENCHER",
  "force": "PREENCHER"
}
```

### `list_pages`

List WordPress pages (static pages like About, Contact, Imprint). Optional: search, status, per_page.

```json
{
  "search": "PREENCHER",
  "status": "PREENCHER",
  "per_page": "PREENCHER"
}
```

### `get_page`

Get a single WordPress page by ID (full content, parent).

```json
{
  "id": "PREENCHER"
}
```

### `create_page`

Create a new WordPress page. Default status is 'draft'. Optional parent (another page ID) for hierarchy.

```json
{
  "title": "PREENCHER",
  "content": "PREENCHER",
  "status": "PREENCHER",
  "parent": "PREENCHER"
}
```

### `update_page`

Update a WordPress page (only provided fields are changed).

```json
{
  "id": "PREENCHER",
  "title": "PREENCHER",
  "content": "PREENCHER",
  "status": "PREENCHER",
  "parent": "PREENCHER"
}
```

### `delete_page`

Delete a page (trash by default, force=true for permanent).

```json
{
  "id": "PREENCHER",
  "force": "PREENCHER"
}
```

### `list_comments`

List comments. Optional: post (filter by post ID), status (approve/hold/spam/trash), per_page.

```json
{
  "post": "PREENCHER",
  "status": "PREENCHER",
  "per_page": "PREENCHER"
}
```

### `moderate_comment`

Change a comment's moderation status. Status values: approved (or approve), hold (pending), spam, trash.

```json
{
  "id": "PREENCHER",
  "status": "PREENCHER"
}
```

### `list_categories`

List post categories with their IDs and post counts.

```json
{
  "search": "PREENCHER",
  "per_page": "PREENCHER"
}
```

### `create_category`

Create a new post category. Required: name. Optional: description, parent (for hierarchy), slug.

```json
{
  "name": "PREENCHER",
  "description": "PREENCHER",
  "parent": "PREENCHER",
  "slug": "PREENCHER"
}
```

### `list_tags`

List post tags with their IDs and post counts.

```json
{
  "search": "PREENCHER",
  "per_page": "PREENCHER"
}
```

### `list_users`

List WordPress users (authors/editors/admins).

```json
{
  "per_page": "PREENCHER"
}
```

### `search`

Cross-type search across posts, pages, and other content. Returns ID, type, title, and URL of each match.

```json
{
  "query": "PREENCHER",
  "type": "PREENCHER",
  "per_page": "PREENCHER"
}
```

### `list_media`

List Media Library items (images, videos, audio, documents). Optional: search, media_type (image/video/audio/application).

```json
{
  "search": "PREENCHER",
  "media_type": "PREENCHER",
  "per_page": "PREENCHER"
}
```

### `upload_media`

Upload a file from a user-sent file (File Bridge) to the WordPress Media Library. Required: file_ref (the ID from the user's message, e.g. file-abc12345). Optional: title, alt_text, caption, filename (custom name).

```json
{
  "file_ref": "PREENCHER",
  "title": "PREENCHER",
  "alt_text": "PREENCHER",
  "caption": "PREENCHER",
  "filename": "PREENCHER"
}
```

## YouTube Data (`youtube`)

JSON para preencher na credencial **Jarvis · YouTube Data** (substitua cada valor):

```json
{
  "youtube_api_key": "PREENCHER"
}
```

### `search_videos`

Search YouTube for videos. QUOTA WARNING: costs 100 units per call (100 calls/day on free tier). Parameters: query (required), limit (default 5, max 25), order (relevance|date|viewCount|rating, default relevance).

```json
{
  "query": "PREENCHER",
  "limit": "PREENCHER",
  "order": "PREENCHER"
}
```

### `get_video`

Get video details: stats (views, likes, comments), duration, tags, full description. Only costs 1 quota unit. Parameters: video_id (required, e.g. vcvRVlc_VFg — the v= part of a YouTube URL).

```json
{
  "video_id": "PREENCHER"
}
```

### `get_channel`

Get YouTube channel profile and stats (subs, views, video count). Parameters: channel_id (UC...) OR handle (@username). One is required.

```json
{
  "channel_id": "PREENCHER",
  "handle": "PREENCHER"
}
```

### `list_channel_videos`

List most recent uploads from a specific YouTube channel. Parameters: channel_id (UC...) OR handle (@username) — one required; limit (default 5, max 20).

```json
{
  "channel_id": "PREENCHER",
  "handle": "PREENCHER",
  "limit": "PREENCHER"
}
```

## Zoho CRM (`zoho-crm`)

JSON para preencher na credencial **Jarvis · Zoho CRM** (substitua cada valor):

```json
{
  "zoho_region": "PREENCHER",
  "zoho_client_id": "PREENCHER",
  "zoho_client_secret": "PREENCHER",
  "zoho_grant_code": "PREENCHER"
}
```

### `list_leads`

List recent Zoho Leads. Returns all fields (incl. custom fields).

```json
{
  "limit": "PREENCHER"
}
```

### `search_leads`

Search Zoho Leads. Use either word (full-text) OR field+operator+value (criteria).

```json
{
  "word": "PREENCHER",
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_lead`

Get single Zoho Lead by Id. Returns all fields.

```json
{
  "lead_id": "PREENCHER"
}
```

### `create_lead`

Create a Zoho Lead. Required: Last_Name, Company.

```json
{
  "Last_Name": "PREENCHER",
  "Company": "PREENCHER",
  "First_Name": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Mobile": "PREENCHER",
  "Title": "PREENCHER",
  "Lead_Source": "PREENCHER",
  "Lead_Status": "PREENCHER",
  "Industry": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_lead`

Update a Zoho Lead by Id. Any subset of fields.

```json
{
  "lead_id": "PREENCHER",
  "First_Name": "PREENCHER",
  "Last_Name": "PREENCHER",
  "Company": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Title": "PREENCHER",
  "Lead_Source": "PREENCHER",
  "Lead_Status": "PREENCHER",
  "Industry": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_lead`

Delete a Zoho Lead by Id (Soft-Delete, 60d Recycle Bin).

```json
{
  "lead_id": "PREENCHER"
}
```

### `convert_lead`

Convert a Zoho Lead into Contact + Account (+ optional Deal). Zoho's classic Lead-Qualification flow.

```json
{
  "lead_id": "PREENCHER",
  "Deal_Name": "PREENCHER",
  "Stage": "PREENCHER",
  "Closing_Date": "PREENCHER",
  "Amount": "PREENCHER",
  "Probability": "PREENCHER",
  "assign_to": "PREENCHER"
}
```

### `list_contacts`

List recent Zoho Contacts. Returns all fields.

```json
{
  "limit": "PREENCHER"
}
```

### `search_contacts`

Search Zoho Contacts. word OR field+operator+value.

```json
{
  "word": "PREENCHER",
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_contact`

Get single Zoho Contact by Id.

```json
{
  "contact_id": "PREENCHER"
}
```

### `create_contact`

Create a Zoho Contact. Required: Last_Name.

```json
{
  "Last_Name": "PREENCHER",
  "First_Name": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Mobile": "PREENCHER",
  "Title": "PREENCHER",
  "Account_Name": "PREENCHER",
  "Mailing_City": "PREENCHER",
  "Mailing_Country": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_contact`

Update a Zoho Contact by Id.

```json
{
  "contact_id": "PREENCHER",
  "First_Name": "PREENCHER",
  "Last_Name": "PREENCHER",
  "Email": "PREENCHER",
  "Phone": "PREENCHER",
  "Title": "PREENCHER",
  "Account_Name": "PREENCHER",
  "Mailing_City": "PREENCHER",
  "Mailing_Country": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_contact`

Delete a Zoho Contact by Id (Soft-Delete, 60d).

```json
{
  "contact_id": "PREENCHER"
}
```

### `list_accounts`

List recent Zoho Accounts (companies). Returns all fields.

```json
{
  "limit": "PREENCHER"
}
```

### `search_accounts`

Search Zoho Accounts.

```json
{
  "word": "PREENCHER",
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_account`

Get single Zoho Account by Id.

```json
{
  "account_id": "PREENCHER"
}
```

### `create_account`

Create a Zoho Account. Required: Account_Name.

```json
{
  "Account_Name": "PREENCHER",
  "Phone": "PREENCHER",
  "Website": "PREENCHER",
  "Industry": "PREENCHER",
  "Billing_City": "PREENCHER",
  "Billing_Country": "PREENCHER",
  "Employees": "PREENCHER",
  "Annual_Revenue": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_account`

Update a Zoho Account by Id. No delete — remove via Zoho UI for safety.

```json
{
  "account_id": "PREENCHER",
  "Account_Name": "PREENCHER",
  "Phone": "PREENCHER",
  "Website": "PREENCHER",
  "Industry": "PREENCHER",
  "Billing_City": "PREENCHER",
  "Billing_Country": "PREENCHER",
  "Employees": "PREENCHER",
  "Annual_Revenue": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `list_deals`

List recent Zoho Deals. Returns all fields.

```json
{
  "limit": "PREENCHER"
}
```

### `search_deals`

Search Zoho Deals.

```json
{
  "word": "PREENCHER",
  "field": "PREENCHER",
  "operator": "PREENCHER",
  "value": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `get_deal`

Get single Zoho Deal by Id.

```json
{
  "deal_id": "PREENCHER"
}
```

### `create_deal`

Create a Zoho Deal. Required: Deal_Name, Stage, Closing_Date.

```json
{
  "Deal_Name": "PREENCHER",
  "Stage": "PREENCHER",
  "Closing_Date": "PREENCHER",
  "Amount": "PREENCHER",
  "Account_Name": "PREENCHER",
  "Contact_Name": "PREENCHER",
  "Probability": "PREENCHER",
  "Type": "PREENCHER",
  "Lead_Source": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_deal`

Update a Zoho Deal by Id. No delete — remove via Zoho UI for safety.

```json
{
  "deal_id": "PREENCHER",
  "Deal_Name": "PREENCHER",
  "Stage": "PREENCHER",
  "Closing_Date": "PREENCHER",
  "Amount": "PREENCHER",
  "Probability": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `list_tasks`

List recent Zoho Tasks.

```json
{
  "limit": "PREENCHER"
}
```

### `get_task`

Get single Zoho Task by Id.

```json
{
  "task_id": "PREENCHER"
}
```

### `create_task`

Create a Zoho Task. Required: Subject.

```json
{
  "Subject": "PREENCHER",
  "Description": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "Due_Date": "PREENCHER",
  "What_Id": "PREENCHER",
  "Who_Id": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_task`

Update a Zoho Task by Id — typically to mark it Completed.

```json
{
  "task_id": "PREENCHER",
  "Subject": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "Due_Date": "PREENCHER",
  "Description": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `delete_task`

Delete a Zoho Task by Id (Soft-Delete, 60d Recycle Bin).

```json
{
  "task_id": "PREENCHER"
}
```

### `list_cases`

List recent Zoho Cases (Service module).

```json
{
  "limit": "PREENCHER"
}
```

### `get_case`

Get single Zoho Case by Id.

```json
{
  "case_id": "PREENCHER"
}
```

### `create_case`

Create a Zoho Case. Required: Subject, Status.

```json
{
  "Subject": "PREENCHER",
  "Status": "PREENCHER",
  "Description": "PREENCHER",
  "Priority": "PREENCHER",
  "Case_Origin": "PREENCHER",
  "Type": "PREENCHER",
  "Account_Name": "PREENCHER",
  "Contact_Name": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `update_case`

Update a Zoho Case by Id — typically to update Status or Description.

```json
{
  "case_id": "PREENCHER",
  "Subject": "PREENCHER",
  "Status": "PREENCHER",
  "Priority": "PREENCHER",
  "Description": "PREENCHER",
  "Case_Origin": "PREENCHER",
  "custom_fields": "PREENCHER"
}
```

### `list_notes`

List Notes attached to a record (any module). Notes are Zoho's record-level comments/activity log.

```json
{
  "parent_module": "PREENCHER",
  "parent_id": "PREENCHER",
  "limit": "PREENCHER"
}
```

### `create_note`

Attach a Note to any Zoho record. Common use: log an interaction, meeting outcome, or status update.

```json
{
  "parent_module": "PREENCHER",
  "parent_id": "PREENCHER",
  "Note_Title": "PREENCHER",
  "Note_Content": "PREENCHER"
}
```

### `list_users`

List Zoho CRM users (for Owner_ID picker / assignment). Default: ActiveUsers only.

```json
{
  "type": "PREENCHER"
}
```

### `coql_query`

Run raw COQL query (SQL-like). Requires WHERE clause.

```json
{
  "query": "PREENCHER"
}
```

### `describe_module`

Get metadata for a Zoho module — list all fields incl. custom fields, types, picklist values. Use this first to discover custom field api_names.

```json
{
  "module_name": "PREENCHER"
}
```
