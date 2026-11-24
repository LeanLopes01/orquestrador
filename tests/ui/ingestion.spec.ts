import { test, expect } from '@playwright/test';

const article = 'https://docs.unity3d.com/Manual/';
const video = 'https://youtu.be/abcdefghijk';

test('prepares a mixed batch, deduplicates and persists without contacting sources', async ({ page }) => {
  const external: string[] = [], errors: string[] = [];
  page.on('request', request => { if (!request.url().startsWith('http://127.0.0.1:1420') && !request.url().startsWith('data:')) external.push(request.url()); });
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button', { name: 'Ingestão de fontes', exact: true }).click();
  await expect(page.getByText('Coleta conectada ao serviço local.', { exact: true })).toBeVisible();
  await page.getByLabel('Links de documentação ou YouTube').fill(`${article}\n${video}\nhttps://www.youtube.com/watch?v=abcdefghijk&t=10\n${article}#section\nnot-a-url\nhttps://youtube.com/playlist?list=123`);
  await page.getByRole('button', { name: 'Adicionar ao lote' }).click();
  await expect(page.locator('.ingestion-source')).toHaveCount(2);
  await expect(page.getByRole('status')).toContainText('2 duplicata(s) ignorada(s)');
  await expect(page.getByRole('list', { name: 'Links que precisam de correção' }).locator('li')).toHaveCount(2);
  await page.reload();
  await expect(page.locator('.ingestion-source')).toHaveCount(2);
  await page.getByRole('button', { name: 'Vídeos', exact: true }).click();
  await expect(page.locator('.ingestion-source')).toHaveCount(1);
  await page.locator('.ingestion-source-select').click();
  await expect(page.getByLabel('Prévia do formato Markdown')).toContainText('Tipo: Vídeo');
  await expect(page.getByLabel('Prévia do formato Markdown')).toContainText('[preenchida após a coleta]');
  await page.getByRole('button', { name: `Remover ${video}`, exact: true }).click();
  await expect(page.getByText('Nenhuma fonte neste filtro', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Todas', exact: true }).click();
  await expect(page.locator('.ingestion-source')).toHaveCount(1);
  expect(external).toEqual([]); expect(errors).toEqual([]);
});

test('imports text and exports an honest draft manifest', async ({ page }) => {
  await page.goto('/#ingestion');
  await expect(page.getByRole('button', { name: 'Exportar lote preparado' })).toBeDisabled();
  await page.locator('input[type=file]').setInputFiles({ name: 'urls.txt', mimeType: 'text/plain', buffer: Buffer.from(`${article}\n${video}`) });
  await expect(page.getByLabel('Links de documentação ou YouTube')).toHaveValue(`${article}\n${video}`);
  await page.getByRole('button', { name: 'Adicionar ao lote' }).click();
  const pending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar lote preparado' }).click();
  const file = await pending;
  const stream = await file.createReadStream(); let content = '';
  for await (const chunk of stream!) content += chunk.toString();
  const manifest = JSON.parse(content);
  expect(manifest.collection_executed).toBe(false);
  expect(manifest.status).toBe('draft');
  expect(manifest.sources).toHaveLength(2);
  expect(manifest.sources[1].video_id).toBe('abcdefghijk');
  expect(manifest.sources[1].original_url).toBe(video);
  expect(manifest.languages).toEqual(['pt-BR', 'pt', 'en']);
  const textPending = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar URLs', exact: true }).click();
  const textFile = await textPending;
  const textStream = await textFile.createReadStream(); let urls = '';
  for await (const chunk of textStream!) urls += chunk.toString();
  expect(urls).toBe(`${article}\n${video}\n`);
});

test('rejects invalid destinations and keeps distinct article query strings', async ({ page }) => {
  await page.goto('/#ingestion');
  await page.getByLabel('Links de documentação ou YouTube').fill('javascript:alert(1)\nfile:///C:/secrets\nhttp://localhost:8000\nhttp://127.0.0.1\nhttps://user:pass@example.org\nhttps://docs.example.org/?version=1\nhttps://docs.example.org/?version=2\nhttps://youtube.com.evil.example/watch?v=abcdefghijk');
  await page.getByRole('button', { name: 'Adicionar ao lote' }).click();
  await expect(page.locator('.ingestion-source')).toHaveCount(3);
  await expect(page.getByRole('list', { name: 'Links que precisam de correção' }).locator('li')).toHaveCount(5);
  await page.getByRole('button', { name: 'Vídeos', exact: true }).click();
  await expect(page.locator('.ingestion-source')).toHaveCount(0);
  await page.getByRole('button', { name: 'Artigos', exact: true }).click();
  await page.getByLabel('Buscar URL no lote').fill('version=2');
  await expect(page.locator('.ingestion-source')).toHaveCount(1);
});

test('recovers from invalid local storage and reports persistence failure', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('orq.ingestion.v1', '{broken'));
  await page.goto('/#ingestion');
  await expect(page.getByRole('alert')).toContainText('Não foi possível recuperar');
  await page.evaluate(() => { Storage.prototype.setItem = () => { throw new Error('quota'); }; });
  await page.getByLabel('Links de documentação ou YouTube').fill(article);
  await page.getByRole('button', { name: 'Adicionar ao lote' }).click();
  await expect(page.getByRole('alert')).toContainText('apenas na sessão');
  await expect(page.getByRole('status')).toContainText('apenas nesta sessão');
  await expect(page.locator('.ingestion-source')).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Exportar lote preparado' })).toBeEnabled();
});

test('ingestion fits desktop, tablet and mobile with long URLs', async ({ page }) => {
  await page.goto('/#ingestion');
  await page.getByLabel('Links de documentação ou YouTube').fill(`${article}\n${video}\nhttps://docs.example.org/${'long-path-'.repeat(80)}`);
  await page.getByRole('button', { name: 'Adicionar ao lote' }).click();
  for (const width of [1440, 1024, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await expect(page.getByRole('heading', { name: 'Das fontes ao conhecimento.' })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), `overflow at ${width}`).toBe(false);
    await page.screenshot({ path: `.local/screenshots/ingestion-${width}.png`, fullPage: true });
  }
});
