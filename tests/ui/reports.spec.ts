import { test, expect, type Download, type Page, type Route } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

// A API do runner é simulada: estes testes nunca disparam auditorias reais nem webhooks.
const RUN = 'AUD-20261025-210206-b897ac';

async function contents(download: Download) {
  const stream = await download.createReadStream();
  let text = ''; for await (const chunk of stream!) text += chunk.toString();
  return text;
}

const settings = { version: 1, revision: 3, on_startup: true, profile: 'startup-light', sync_to_server: false, investigate_with_ai: false, workflow_url: '', ai_provider: 'local-rag', allow_code_to_provider: false, updated_at: '2026-10-25T20:00:00+00:00' };
const summary = { findings: 2, by_severity: { high: 1, medium: 0, low: 1, info: 0 }, new: 1, recurring: 1, resolved: 1, not_rechecked: 0, coverage: { collected: 3, partial: 1, error: 0, skipped: 0 } };
const row = { id: RUN, project: 'dicevtt', profile: 'startup-light', trigger: 'startup', state: 'partial', created_at: '2026-10-25T21:02:06.000+00:00', started_at: '2026-10-25T21:02:06.100+00:00', finished_at: '2026-10-25T21:02:10.200+00:00', summary, revision: null, error: null, sync_state: 'local_only', checks_total: 4, checks_done: 4 };
const report = {
  schema_version: 1, kind: 'audit', executed: true, run_id: RUN, state: 'partial', profile: 'startup-light', trigger: 'startup',
  started_at: row.started_at, finished_at: row.finished_at, duration_ms: 4100, previous_run_id: 'AUD-20261024-100000-aaaaaa', startup_ids: ['s1'],
  revision: { vcs: 'plastic', source_state: 'working_tree', git_root: 'C:/ProjetoTablepRPG', project_relative_path: 'DiceVTT', commit: null, branch: 'main', dirty: true, plastic: { repository: 'r', branch: '/main/Salas', changeset: 189, pending: 148, private: 720 } },
  summary, sync: { state: 'local_only', note: 'n' },
  checks: [
    { id: 'vcs', name: 'Controle de versão', status: 'collected', note: 'Unity Version Control · changeset 189', problems: [], duration_ms: 2800, evidence: [{ id: 'vcs-E1', kind: 'command', source: 'cm status', detail: '148 pendentes', sha256: null, observed_at: null }] },
    { id: 'logs', name: 'Logs do Editor e do build', status: 'partial', note: 'Editor.log', problems: ['Editor.log possivelmente desatualizado'], duration_ms: 16, evidence: [{ id: 'logs-E1', kind: 'log_excerpt', source: 'Editor.log', detail: 'bytes 0-10', sha256: 'abcdef0123456789', observed_at: null }] },
  ],
  findings: [
    { fingerprint: 'f1', check_id: 'logs', rule: 'unity.compile-error', severity: 'high', state: 'suspected', comparison: 'new', summary: 'Erro de compilação <img src=x onerror=alert(1)>', file: 'Assets/Scripts/A.cs', line: 20, evidence: ['logs-E1'], recommendation: 'Corrija e recompile.', occurrences: 1 },
    { fingerprint: 'f2', check_id: 'vcs', rule: 'vcs.private-scripts', severity: 'low', state: 'confirmed', comparison: 'recurring', summary: '62 scripts fora do controle de versão', file: null, line: null, evidence: ['vcs-E1'], recommendation: '', occurrences: 62 },
    { fingerprint: 'f3', check_id: 'vcs', rule: 'vcs.locally-deleted', severity: 'medium', state: 'confirmed', comparison: 'resolved', summary: 'Itens apagados resolvidos', file: null, line: null, evidence: [], recommendation: '', occurrences: 0 },
  ],
};
const health = (extra: Record<string, unknown> = {}) => ({
  service: 'dicevtt-diagnostics', online: true, version: '0.1.0', project: 'DiceVTT', project_root: 'C:/ProjetoTablepRPG/DiceVTT',
  capabilities: { profiles: ['startup-light', 'full-audit'], full_audit: true, sync: false, ai_investigation: true, auto_fix: false },
  settings, settings_error: null, current: null, active: [], last_run: row,
  last_startup: { startup_id: 's1', run_id: RUN, outcome: 'created', created_at: row.created_at }, sync: { state: 'local_only', message: '' }, ...extra,
});

type Seen = { method: string; path: string; key?: string; body?: unknown };
async function mockRunner(page: Page, overrides: Partial<Record<string, (route: Route, seen: Seen) => Promise<void> | void>> = {}) {
  const seen: Seen[] = [];
  await page.route('**/api/audits/**', async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/audits/', '');
    const entry: Seen = { method: request.method(), path, key: request.headers()['idempotency-key'], body: request.postDataJSON?.() ?? undefined };
    seen.push(entry);
    const custom = overrides[`${request.method()} ${path}`];
    if (custom) return custom(route, entry);
    if (path === 'health') return route.fulfill({ json: health() });
    if (path === 'runs' && request.method() === 'GET') return route.fulfill({ json: { items: [row], next_cursor: null } });
    if (path === `runs/${RUN}`) return route.fulfill({ json: { ...row, startup_ids: ['s1'], checks: [], artifacts: [], report } });
    if (path === 'settings') return route.fulfill({ json: settings });
    return route.fulfill({ status: 404, json: { message: 'não simulado' } });
  });
  return seen;
}

test('offline runner is explicit, never claims zero failures and keeps the example separate', async ({ page }) => {
  await page.route('**/api/audits/**', route => route.fulfill({ status: 503, json: { error: 'audits_offline', message: 'Runner de relatórios desligado.' } }));
  await page.goto('/#reports');
  await expect(page.getByRole('alert').first()).toContainText('Runner de relatórios indisponível');
  await expect(page.getByText('Sem conexão com o runner.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Gerar agora' })).toBeDisabled();
  await expect(page.getByText('0 ocorrência')).toHaveCount(0);
  await page.getByRole('button', { name: 'Ver relatório de exemplo' }).click();
  await expect(page.getByText('Exemplo fictício · não executado')).toBeVisible();
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar exemplo JSON' }).click();
  expect(JSON.parse(await contents(await pending))).toMatchObject({ kind: 'example', executed: false, commit: null });
});

test('real report shows coverage, comparison and escaped findings', async ({ page }) => {
  await mockRunner(page);
  await page.goto('/#reports');
  const detail = page.getByRole('region', { name: `Relatório ${RUN}` });
  await expect(detail).toBeVisible();
  await expect(detail.getByText('Unity VCS /main/Salas · cs 189 · 148 pendente(s)')).toBeVisible();
  await expect(detail.getByText('Editor.log possivelmente desatualizado')).toBeVisible();
  await expect(detail.getByText('Erro de compilação <img src=x onerror=alert(1)>')).toBeVisible(); // texto, não HTML
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
  await expect(detail.getByText('Itens apagados resolvidos')).toHaveCount(0);
  await detail.getByRole('checkbox', { name: /Resolvidas e não reverificadas/ }).check();
  await expect(detail.getByText('Itens apagados resolvidos')).toBeVisible();
  await detail.getByLabel('Filtrar gravidade').selectOption('low');
  await expect(detail.getByText('62 scripts fora do controle de versão')).toBeVisible();
  await expect(detail.getByText(/Erro de compilação/)).toHaveCount(0);
  await expect(detail.getByRole('link', { name: 'HTML' })).toHaveAttribute('href', `/api/audits/runs/${RUN}/report?format=html`);
});

test('generate now is idempotent: retry reuses the key and an active run blocks duplicates', async ({ page }) => {
  let attempts = 0;
  let active = false;
  const seen = await mockRunner(page, {
    'POST runs': async route => {
      attempts += 1;
      if (attempts === 1) return route.fulfill({ status: 503, json: { message: 'Runner reiniciando.' } });
      active = true;
      return route.fulfill({ status: 202, json: { run_id: RUN, outcome: 'created', duplicate: false, coalesced: false } });
    },
    'GET health': route => route.fulfill({ json: health(active ? { active: [{ id: RUN, state: 'collecting', profile: 'startup-light', trigger: 'manual', checks_done: 1, checks_total: 4 }] } : {}) }),
  });
  await page.goto('/#reports');
  await page.getByRole('button', { name: 'Gerar agora' }).click();
  await expect(page.getByRole('alert')).toContainText('reaproveita o mesmo pedido');
  await page.getByRole('button', { name: 'Gerar agora' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Coleta iniciada' })).toBeVisible();
  const posts = seen.filter(s => s.method === 'POST' && s.path === 'runs');
  expect(posts).toHaveLength(2);
  expect(posts[0].key).toBeTruthy();
  expect(posts[1].key).toBe(posts[0].key);
  expect(posts[0].body).toEqual({ trigger: 'manual', auto_fix: false });
  await expect(page.getByRole('button', { name: 'Coleta em andamento' })).toBeDisabled();
});

test('settings save with revision, conflicts reload and imports never apply silently', async ({ page }) => {
  let conflict = true;
  const seen = await mockRunner(page, {
    'PUT settings': async (route, entry) => {
      if (conflict) { conflict = false; return route.fulfill({ status: 409, json: { error: 'revision_conflict', message: 'mudou' } }); }
      const body = entry.body as { settings: typeof settings };
      return route.fulfill({ json: { ...settings, ...body.settings, revision: 4 } });
    },
  });
  await page.addInitScript(() => localStorage.setItem('orchestrator.audit-draft.v1', JSON.stringify({ version: 1, settings: { onStartup: false, profile: 'full-audit', syncToServer: true, investigateWithAI: false, workflowUrl: '' } })));
  await page.goto('/#reports');
  await page.getByRole('button', { name: 'Rotina de abertura', exact: true }).click();
  await expect(page.getByText('Salvo no runner · revisão 3')).toBeVisible();
  await page.getByRole('button', { name: 'Importar rascunho antigo' }).click();
  await expect(page.getByRole('status')).toContainText('Nada foi ativado');
  await expect(page.getByRole('switch', { name: /Gerar ao abrir/ })).not.toBeChecked();
  expect(seen.filter(s => s.method === 'PUT')).toHaveLength(0);
  await page.getByRole('button', { name: 'Salvar preferências' }).click();
  await expect(page.getByRole('alert')).toContainText('mudaram em outra janela');
  await expect(page.getByRole('switch', { name: /Gerar ao abrir/ })).toBeChecked(); // recarregou do runner
  await page.getByRole('switch', { name: /Gerar ao abrir/ }).uncheck();
  await page.getByRole('button', { name: 'Salvar preferências' }).click();
  await expect(page.getByRole('status')).toContainText('revisão 4');
  const puts = seen.filter(s => s.method === 'PUT');
  expect(puts.at(-1)?.body).toMatchObject({ expected_revision: 3, settings: { on_startup: false } });
});

test('workflow links require editor URLs', async ({ page }) => {
  await mockRunner(page);
  await page.goto('/#reports');
  await page.getByRole('button', { name: 'Fluxo e conexões', exact: true }).click();
  const input = page.getByLabel('Link do workflow de relatórios');
  for (const value of ['javascript:alert(1)', 'https://user:password@example.com/workflow/123', 'https://example.com/webhook/test', 'https://example.com/workflow/123?token=secret']) {
    await input.fill(value);
    await expect(page.getByRole('button', { name: 'Salvar preferências' })).toBeDisabled();
    await expect(page.getByRole('link', { name: 'Abrir workflow' })).toHaveCount(0);
  }
  await input.fill('http://localhost:5679/workflow/audit-test');
  await expect(page.getByRole('button', { name: 'Salvar preferências' })).toBeEnabled();
  await page.getByRole('button', { name: /Receber no n8n/ }).click();
  await expect(page.locator('.audit-flow-detail')).toContainText('O helper enviará pelo canal autenticado existente');
});

test('all report views fit mobile and desktop without runtime errors', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await mockRunner(page);
  await mkdir('.local/screenshots', { recursive: true });
  await page.goto('/#reports');
  await expect(page.getByRole('region', { name: `Relatório ${RUN}` })).toBeVisible();
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 1080 });
    for (const label of ['Relatórios', 'Rotina de abertura', 'Fluxo e conexões']) {
      await page.getByRole('group', { name: 'Áreas de relatórios' }).getByRole('button', { name: label, exact: true }).click();
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), `${label} @ ${width}`).toBe(false);
      if (width !== 1024) await page.screenshot({ path: `.local/screenshots/reports-${width}-${label === 'Relatórios' ? 'overview' : label === 'Rotina de abertura' ? 'routine' : 'flow'}.png`, fullPage: true });
    }
  }
  expect(errors).toEqual([]);
});

const validatorsCheck = { id: 'validators', name: 'Validadores do projeto na cópia', status: 'partial', note: '3 validador(es)', problems: [], duration_ms: 90000, evidence: [],
  data: { validators: [{ id: 'ok', name: 'Ficha Cyberpunk Alpha', status: 'passed', result: 'OK', duration_ms: 61000 }, { id: 'falha', name: 'Iluminação das salas', status: 'failed', failures: 2, duration_ms: 70000 }, { id: 'lic', name: 'Guildas', status: 'error', note: 'licença indisponível' }] } };
const investigation = {
  run_id: RUN, state: 'completed', trigger: 'manual', attempt: 1, provider: 'local-rag', model: 'Qwen-teste', prompt_version: '2026-10-25.1',
  requested_at: row.finished_at, started_at: row.finished_at, finished_at: row.finished_at, error: null, findings_total: 2, findings_done: 2,
  result: { state: 'completed', reason: null, provider: 'local-rag', model: 'Qwen-teste', prompt_version: '2026-10-25.1', report_sha256: 'x', data_left_pc: false,
    note: 'Hipóteses geradas por IA. Não confirmam nem resolvem ocorrências; confira as fontes citadas.', items: [
      { fingerprint: 'f1', rule: 'unity.compile-error', severity: 'high', finding_summary: 'Erro de compilação em A.cs', file: 'Assets/Scripts/A.cs', status: 'supported', hypothesis: 'Falta um ponto e vírgula [S1].', sources: [{ ref: 'S1', path: 'Assets/Scripts/A.cs', lines: [1, 9], valid: true }, { ref: 'S7', path: null, valid: false }], duration_ms: 300000 },
      { fingerprint: 'f2', rule: 'vcs.private-scripts', severity: 'low', finding_summary: '62 scripts fora do controle', file: null, status: 'timeout', error: 'Sem resposta do modelo local em 900 s.' },
    ] },
};

test('full audit is a separate manual request and shows each project validator', async ({ page }) => {
  const seen = await mockRunner(page, {
    'POST runs': route => route.fulfill({ status: 202, json: { run_id: RUN, outcome: 'created', duplicate: false, coalesced: false } }),
    [`GET runs/${RUN}`]: route => route.fulfill({ json: { ...row, profile: 'full-audit', startup_ids: ['s1'], checks: [], artifacts: [], report: { ...report, profile: 'full-audit', checks: [...report.checks, validatorsCheck] } } }),
  });
  await page.goto('/#reports');
  await page.getByRole('button', { name: 'Auditoria completa' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Auditoria completa iniciada' })).toBeVisible();
  await page.getByRole('button', { name: 'Gerar agora' }).click();
  const posts = seen.filter(s => s.method === 'POST' && s.path === 'runs');
  expect(posts[0].body).toEqual({ trigger: 'manual', auto_fix: false, profile: 'full-audit' });
  expect(posts[1].body).toEqual({ trigger: 'manual', auto_fix: false });
  expect(posts[1].key).not.toBe(posts[0].key);
  const validators = page.getByRole('list', { name: 'Validadores do projeto' });
  await expect(validators.getByText('Ficha Cyberpunk Alpha')).toBeVisible();
  await expect(validators.getByText('Com falhas')).toBeVisible();
  await expect(validators.getByText('licença indisponível')).toBeVisible();
});

test('AI hypotheses stay separate, show sources and can be requested', async ({ page }) => {
  let requested = false;
  const seen = await mockRunner(page, {
    [`GET runs/${RUN}`]: route => route.fulfill({ json: { ...row, startup_ids: ['s1'], checks: [], artifacts: [], report, ...(requested ? { investigation } : {}) } }),
    [`POST runs/${RUN}/investigation`]: route => { requested = true; return route.fulfill({ status: 202, json: { run_id: RUN, state: 'queued', created: true } }); },
  });
  await page.goto('/#reports');
  const panel = page.getByRole('region', { name: 'Investigação por IA' });
  await expect(panel.getByText('nunca confirmam uma ocorrência sozinhas')).toBeVisible();
  await panel.getByRole('button', { name: 'Investigar com IA' }).click();
  await expect(panel.getByText('Hipótese com fonte')).toBeVisible();
  await expect(panel.getByText('Tempo esgotado')).toBeVisible();
  await panel.getByText('Erro de compilação em A.cs').click();
  await expect(panel.getByText('fonte inexistente, desconsiderada')).toBeVisible();
  await expect(panel.getByRole('button', { name: 'Investigar de novo' })).toHaveCount(0); // concluída
  expect(seen.filter(s => s.method === 'POST' && s.path === `runs/${RUN}/investigation`)).toHaveLength(1);
  // A ocorrência original continua como estava: a hipótese não muda o relatório.
  await expect(page.getByText('Suspeita: evidência possivelmente desatualizada').first()).toBeVisible();
});

test('claude provider requires explicit consent and imports never carry it', async ({ page }) => {
  const seen = await mockRunner(page, {
    'PUT settings': (route, entry) => route.fulfill({ json: { ...settings, ...(entry.body as { settings: object }).settings, revision: 4 } }),
  });
  await page.addInitScript(() => localStorage.setItem('orchestrator.audit-draft.v1', JSON.stringify({ version: 1, settings: { onStartup: true, profile: 'startup-light', syncToServer: false, investigateWithAI: true, workflowUrl: '', ai_provider: 'claude-code', allow_code_to_provider: true } })));
  await page.goto('/#reports');
  await page.getByRole('button', { name: 'Rotina de abertura', exact: true }).click();
  await page.getByRole('button', { name: 'Importar rascunho antigo' }).click();
  await expect(page.getByRole('radio', { name: /Claude Code/ })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: /Autorizo enviar/ })).not.toBeChecked();
  await expect(page.getByText('Sem a autorização, a investigação pelo Claude Code não roda.')).toBeVisible();
  await page.getByRole('checkbox', { name: /Autorizo enviar/ }).check();
  await page.getByRole('button', { name: 'Salvar preferências' }).click();
  await expect(page.getByRole('status')).toContainText('revisão 4');
  expect(seen.filter(s => s.method === 'PUT').at(-1)?.body).toMatchObject({ settings: { ai_provider: 'claude-code', allow_code_to_provider: true, investigate_with_ai: true } });
  await page.getByRole('radio', { name: /Local · AirLLM/ }).check();
  await expect(page.getByRole('checkbox', { name: /Autorizo enviar/ })).toHaveCount(0);
});
