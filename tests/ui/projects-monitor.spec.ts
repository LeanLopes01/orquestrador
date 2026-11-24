import { test, expect, type Page } from '@playwright/test';

function fixture() {
  const now = Date.now() / 1000;
  return {
    id: 'conversation-monitor', title: 'Revisar seleção de peças', state: 'awaiting_approval', updated_at: now,
    messages: [{ seq: 1, author: 'user', text: 'Verifique a seleção de peças e prepare um plano.' }],
    plans: [{ id: 'plan-1', version: 3, hash: 'a'.repeat(64), state: 'proposed', body: {
      title: 'Corrigir seleção', goal: 'Selecionar peças sem perder o foco do tabuleiro.', summary: 'Ajustar o controlador e verificar a interação.',
      tasks: [{ agent: 'claude', title: 'Revisar controlador', files: ['Assets/Scripts/' + 'Selection'.repeat(20) + '.cs'], acceptance: ['Selecionar uma peça por toque.'] }],
      tests: ['Validar seleção e cancelamento.'], risks: ['Possível conflito com o arraste.'],
    } }],
    jobs: [
      { id: 'job-claude', agent: 'claude', state: 'running', started_at: now - 210, updated_at: now - 120, progress: { stage: 'running', stdout_tail: 'Lendo SelectionController.cs\n' + 'x'.repeat(300), stderr_tail: 'Aviso: aguardando permissão de ferramenta.' } },
      { id: 'job-antigravity', agent: 'antigravity', state: 'completed', started_at: now - 300, finished_at: now - 220, updated_at: now - 220, progress: { stage: 'completed', activity: 'Plano preparado para revisão.', reasoning_summary: 'Separei a correção da seleção e a validação por toque.', usage: { input_tokens: 1234, output_tokens: 0, cost_usd: 0, model: 'modelo-informado', source: 'provider' }, events: [{ id: 'event-1', at: now - 230, kind: 'tool', text: 'Leitura do controlador concluída.' }] } },
    ], runs: [],
  };
}
async function setup(page: Page, options: { online?: boolean; decisionStatus?: number } = {}) {
  const conv = fixture();
  const posts: { path: string; body: unknown }[] = [];
  const state = { online: options.online ?? true, failRead: false };
  await page.route('**/api/orchestrator/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST') {
      posts.push({ path, body: request.postDataJSON() });
      expect(request.headers()['x-orchestrator-request']).toBe('1');
      if (options.decisionStatus) { await route.fulfill({ status: options.decisionStatus, json: { message: 'Detalhe do servidor.' } }); return; }
      conv.plans[0].state = path.endsWith('/approve') ? 'approved' : 'rejected';
      conv.state = 'running';
      await route.fulfill({ json: { ok: true } }); return;
    }
    if (path.endsWith('/runtime')) { await route.fulfill({ json: { online: state.online } }); return; }
    if (path.endsWith('/conversations')) { await route.fulfill({ json: { conversations: [conv] } }); return; }
    await route.fulfill({ status: state.failRead ? 503 : 200, json: state.failRead ? { message: 'Leitura indisponível.' } : conv });
  });
  await page.goto('/#projects');
  await page.getByRole('button', { name: /Revisar seleção de peças/ }).click();
  await expect(page.getByRole('heading', { name: 'Revisar seleção de peças', exact: true })).toBeVisible();
  return { conv, posts, state };
}

test('monitor separates logs, reports silence and uses only supplied telemetry', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  await setup(page);
  const claude = page.getByRole('article', { name: 'Job job-claude', exact: true });
  await expect(claude).toContainText('Sem atualização há 2 min');
  await claude.getByRole('button', { name: 'Saída', exact: true }).click();
  await expect(claude.locator('pre')).toContainText('Lendo SelectionController.cs');
  await expect(claude.locator('pre')).not.toContainText('Aviso:');
  await claude.getByRole('button', { name: 'Erros', exact: true }).click();
  await expect(claude.locator('pre')).toContainText('aguardando permissão');
  await claude.getByRole('button', { name: 'Uso', exact: true }).click();
  await expect(claude.locator('dd')).toHaveText(['Não informado', 'Não informado', 'Não informado']);
  await claude.getByRole('button', { name: 'Resumo de raciocínio' }).click();
  await expect(claude).toContainText('ainda não forneceu um resumo');
  const antigravity = page.getByRole('article', { name: 'Job job-antigravity', exact: true });
  await expect(antigravity).toContainText('Leitura do controlador concluída.');
  await antigravity.getByRole('button', { name: 'Uso', exact: true }).click();
  await expect(antigravity.locator('dd').nth(0)).toHaveText('1.234');
  await expect(antigravity.locator('dd').nth(1)).toHaveText('0');
  await expect(antigravity.locator('dd').nth(2)).toContainText('0,00');
  await antigravity.getByRole('button', { name: 'Resumo de raciocínio' }).click();
  await expect(antigravity).toContainText('Separei a correção');
  await page.getByLabel('Exibir jobs').selectOption('Codex');
  await expect(page.getByText('Nenhuma tarefa recebida para este agente.')).toBeVisible();
  await page.getByLabel('Exibir jobs').selectOption('Todos');
  await page.screenshot({ path: '.local/screenshots/projects-monitor-desktop.png', fullPage: true });
  expect(errors).toEqual([]);
});

test.describe('touch approval', () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  test('review shortcut and approval work by touch with exact version/hash', async ({ page }) => {
    const { posts } = await setup(page);
    const shortcut = page.getByRole('link', { name: /Plano 3 aguarda sua decisão/ });
    await expect(shortcut).toBeVisible();
    await shortcut.tap();
    expect(new URL(page.url()).hash).toBe('#projects');
    const approve = page.getByRole('button', { name: 'Aprovar plano 3 e executar', exact: true });
    await expect(approve).toBeEnabled();
    const bounds = await approve.boundingBox(); expect(bounds!.height).toBeGreaterThanOrEqual(44);
    for (const width of [320, 360, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), `overflow at ${width}`).toBe(false);
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: '.local/screenshots/projects-monitor-mobile.png', fullPage: true });
    await approve.tap();
    await expect(page.getByText('Aprovação do plano 3 registrada.', { exact: false })).toBeVisible();
    await expect(approve).toHaveCount(0);
    await expect(shortcut).toHaveCount(0);
    expect(posts).toEqual([{ path: '/api/orchestrator/v1/plans/plan-1/approve', body: { version: 3, hash: 'a'.repeat(64) } }]);
  });
});

for (const [status, message] of [[403, 'Este dispositivo não tem autorização'], [409, 'O plano mudou'], [503, 'Executor indisponível']] as const) {
  test(`decision error ${status} remains visible after polling`, async ({ page }) => {
    await setup(page, { decisionStatus: status });
    await page.getByRole('button', { name: 'Aprovar plano 3 e executar' }).click();
    await expect(page.getByRole('alert')).toContainText(message);
    await page.getByRole('button', { name: 'Atualizar', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Atualizar', exact: true })).toBeEnabled();
    await expect(page.getByRole('alert')).toContainText(message);
  });
}

test('offline approval has a reason; rejection remains available', async ({ page }) => {
  const { posts } = await setup(page, { online: false });
  await expect(page.getByRole('button', { name: 'Aprovar plano 3 e executar' })).toBeDisabled();
  await expect(page.getByText('Para executar, abra o Orquestrador e o helper no PC.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Rejeitar plano 3', exact: true }).click();
  await expect(page.getByText('Plano 3 rejeitado.', { exact: true })).toBeVisible();
  expect(posts[0].path).toBe('/api/orchestrator/v1/plans/plan-1/reject');
});

test('failed refresh retains evidence and blocks approval of stale data', async ({ page }) => {
  const { state } = await setup(page);
  state.failRead = true;
  await page.getByRole('button', { name: 'Atualizar', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Os dados já recebidos continuam visíveis');
  await expect(page.getByRole('article', { name: 'Job job-claude', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Aprovar plano 3 e executar' })).toBeDisabled();
  state.failRead = false;
  await page.getByRole('button', { name: 'Atualizar', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Aprovar plano 3 e executar' })).toBeEnabled();
});

test('a slow snapshot is not discarded or duplicated by the polling interval', async ({ page }) => {
  await page.clock.install();
  const { conv } = await setup(page);
  let reads = 0;
  let release!: () => void;
  const waiting = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/orchestrator/v1/conversations/conversation-monitor', async route => {
    reads++;
    await waiting;
    await route.fulfill({ json: { ...conv, title: 'Snapshot recuperado' } });
  });
  await page.getByRole('button', { name: 'Atualizar', exact: true }).click();
  await expect.poll(() => reads).toBe(1);
  await page.clock.runFor(6000);
  expect(reads).toBe(1);
  release();
  await expect(page.getByRole('heading', { name: 'Snapshot recuperado' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Atualizar', exact: true })).toBeEnabled();
});

test('approval is locked while the server processes the decision', async ({ page }) => {
  const { conv } = await setup(page);
  let decisions = 0;
  let release!: () => void;
  const waiting = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/orchestrator/v1/plans/plan-1/approve', async route => {
    decisions++;
    await waiting;
    conv.plans[0].state = 'approved';
    await route.fulfill({ json: { state: 'approved' } });
  });
  await page.getByRole('button', { name: 'Aprovar plano 3 e executar' }).click();
  await expect.poll(() => decisions).toBe(1);
  await expect(page.getByRole('article', { name: 'Plano 3', exact: true }).getByRole('button', { name: 'Aguarde…' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Rejeitar plano 3' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Novo pedido', exact: true })).toBeDisabled();
  release();
  await expect(page.getByText('Aprovação do plano 3 registrada.', { exact: false })).toBeVisible();
  expect(decisions).toBe(1);
});
