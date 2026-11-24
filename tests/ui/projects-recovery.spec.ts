import { test, expect } from '@playwright/test';

function conversation() {
  const now = Date.now() / 1000;
  return {
    id: 'real-shape-conversation', title: 'Planejar skins dos dados', state: 'failed', updated_at: now,
    messages: [{ seq: 1, author: 'jarvis', text: 'Não consegui um plano do Antigravity: tools refused: RunCommand' }],
    plans: [], runs: [],
    jobs: [
      { id: 'coordinator-plan', agent: null, purpose: 'plan', state: 'failed', started_at: now - 248, finished_at: now, updated_at: now,
        progress: { stage: 'failed', activity: 'Falhou: tools refused: RunCommand', stderr_tail: 'A permissão command foi negada no modo headless.', usage: { source: 'antigravity-cli', input_tokens: 109311, output_tokens: 6308 }, events: [{ id: 'event-1', at: now, kind: 'error', text: 'Permissão negada no modo headless: RunCommand' }] } },
      { id: 'coordinator-report', agent: null, purpose: 'report', state: 'completed', updated_at: now, progress: null },
      { id: 'unknown-agent', agent: null, purpose: 'task', state: 'queued', updated_at: null, progress: null },
      { id: 'missing-agent', purpose: 'task', state: 'queued', updated_at: null, progress: null },
      { id: 'empty-agent', agent: '', purpose: 'task', state: 'queued', updated_at: null, progress: null },
    ],
  };
}

for (const action of ['open', 'send'] as const) {
  test(`nullable coordinator agent does not crash after ${action}`, async ({ page }) => {
    const conv = conversation();
    const errors: string[] = [];
    let posts = 0;
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/orchestrator/v1/**', async route => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (request.method() === 'POST') { posts++; await route.fulfill({ status: 202, json: conv }); return; }
      await route.fulfill({ json: path.endsWith('/runtime') ? { online: true, planning_routing: { version: 1, agents: ['codex', 'antigravity'], execution_agent: 'claude' } } : path.endsWith('/conversations') ? { conversations: [conv] } : conv });
    });
    await page.goto('/#projects');
    if (action === 'open') await page.getByRole('button', { name: /Planejar skins dos dados/ }).click();
    else {
      await page.getByLabel('Pedido para o Jarvis').fill('Planejar skins dos dados');
      await page.getByRole('button', { name: 'Enviar ao Jarvis' }).click();
    }
    await expect(page.getByRole('heading', { name: 'Planejar skins dos dados', exact: true })).toBeVisible();
    const plan = page.getByRole('article', { name: 'Job coordinator-plan', exact: true });
    await expect(plan.getByRole('heading')).toContainText('Coordenador');
    await expect(plan).toContainText('Permissão negada no modo headless: RunCommand');
    await page.getByLabel('Exibir jobs').selectOption('Coordenador');
    await expect(page.locator('.job-detail')).toHaveCount(5);
    await plan.getByRole('button', { name: 'Uso', exact: true }).click();
    await expect(plan.locator('dd')).toHaveText(['109.311', '6.308', 'Não informado']);
    await page.getByLabel('Exibir jobs').selectOption('Coordenador');
    await expect(page.locator('.job-detail')).toHaveCount(5);
    await page.getByLabel('Exibir jobs').selectOption('Todos');
    await page.getByRole('button', { name: 'Atualizar', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Atualizar', exact: true })).toBeEnabled();
    await expect(page.getByRole('heading', { name: 'Planejar skins dos dados', exact: true })).toBeVisible();
    expect(posts).toBe(action === 'send' ? 1 : 0);
    expect(errors).toEqual([]);
  });
}

test('unexpected render error preserves navigation and recovers without resubmitting', async ({ page }) => {
  const conv = conversation();
  let broken = true;
  let posts = 0;
  await page.route('**/api/orchestrator/v1/**', async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST') posts++;
    await route.fulfill({ json: path.endsWith('/runtime') ? { online: true, planning_routing: { version: 1, agents: ['codex', 'antigravity'], execution_agent: 'claude' } } : path.endsWith('/conversations') ? { conversations: [conv] } : { ...conv, messages: broken ? [{ seq: 1, author: 'jarvis', text: { unexpected: 'invalid render value' } }] : conv.messages } });
  });
  await page.goto('/#projects');
  await page.getByRole('button', { name: /Planejar skins dos dados/ }).click();
  await expect(page.getByRole('alert')).toContainText('Não foi possível exibir esta conversa');
  await expect(page.getByRole('navigation', { name: 'Navegação principal' })).toBeVisible();
  broken = false;
  await page.getByRole('button', { name: 'Voltar às conversas' }).click();
  await page.getByRole('button', { name: /Planejar skins dos dados/ }).click();
  await expect(page.getByRole('heading', { name: 'Planejar skins dos dados', exact: true })).toBeVisible();
  expect(posts).toBe(0);
});

