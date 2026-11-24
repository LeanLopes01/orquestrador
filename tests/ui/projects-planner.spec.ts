import { test, expect } from '@playwright/test';

test('three stages persist, send model and effort, and change idempotency when edited', async ({page}) => {
  const posts: any[] = [];
  let fail = true;
  const conv = {id:'stages',title:'Três etapas',state:'planning',updated_at:Date.now()/1000,messages:[],plans:[],runs:[],jobs:[]};
  await page.route('**/api/orchestrator/v1/**', async route => {
    if (route.request().method() === 'POST') {
      posts.push(route.request().postDataJSON());
      await route.fulfill({status:fail?503:202,json:fail?{message:'Temporariamente indisponível'}:conv}); return;
    }
    await route.fulfill({json:route.request().url().endsWith('/runtime')?{online:true,planning_routing:{version:1,pipeline_version:1,agents:['codex','antigravity'],execution_agent:'claude',execution_agents:['claude','codex','antigravity']}}:{conversations:[]}});
  });
  await page.goto('/#projects');
  await expect(page.getByLabel('Agente — 1')).toHaveValue('antigravity');
  await expect(page.getByLabel('Agente — 2')).toHaveValue('codex');
  await expect(page.getByLabel('Agente — 3')).toHaveValue('claude');
  await page.getByLabel('Modelo — 2').fill('gpt-6.1-sol');
  await page.getByLabel('Esforço — 2').selectOption('xhigh');
  await page.getByLabel('Pedido para o Jarvis').fill('Criar UI e lógica');
  await page.getByRole('button',{name:'Enviar ao Jarvis'}).click();
  await expect(page.getByRole('alert')).toContainText('Temporariamente');
  await page.getByRole('button',{name:'Enviar ao Jarvis'}).click();
  await expect.poll(()=>posts.length).toBe(2);
  expect(posts[0].request_id).toBe(posts[1].request_id);
  expect(posts[0].pipeline.ui).toMatchObject({agent:'codex',model:'gpt-6.1-sol',effort:'xhigh'});
  await page.getByLabel('Incluir UI quando necessária').uncheck();
  fail = false;
  await page.getByRole('button',{name:'Enviar ao Jarvis'}).click();
  await expect.poll(()=>posts.length).toBe(3);
  expect(posts[2].request_id).not.toBe(posts[1].request_id);
  expect(posts[2].pipeline.ui.enabled).toBe(false);
  await page.reload();
  await expect(page.getByLabel('Incluir UI quando necessária')).not.toBeChecked();
  await page.screenshot({path:'.local/screenshots/pipeline-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false);
  await page.screenshot({path:'.local/screenshots/pipeline-mobile.png',fullPage:true});
});

test('old backend cannot discard three stage choices', async ({page}) => {
  await page.route('**/api/orchestrator/v1/**', route=>route.fulfill({json:route.request().url().endsWith('/runtime')?{online:true,planning_routing:{version:1,agents:['codex','antigravity'],execution_agent:'claude'}}:{conversations:[]}}));
  await page.goto('/#projects');
  await page.getByLabel('Pedido para o Jarvis').fill('Teste');
  await expect(page.getByRole('button',{name:'Enviar ao Jarvis'})).toBeDisabled();
  await expect(page.getByText(/precisam confirmar suporte às três etapas/)).toBeVisible();
});
