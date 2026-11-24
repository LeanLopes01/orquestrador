import { test, expect, type Page } from '@playwright/test';

// Respostas simuladas do serviço: valida a UI sem depender do modelo nem do índice real.
const health = { service: 'unity-rag', online: true, starting: false, startup_error: null, version: '0.1.0',
  embeddings: { state: 'ready', model: 'multilingual', error: null },
  index: { state: 'ready', code_pointers: 494, document_chunks: 869, documents: 12 },
  watcher: { state: 'running', error: null, events_seen: 0 },
  model: { state: 'unloaded', reason: null, name: 'Qwen/Qwen2.5-1.5B-Instruct', device: 'cpu', max_new_tokens: 384 } };
const source = (id: string, kind: string, relpath: string, text: string, extra: Record<string, unknown> = {}) => ({
  id, record_id: id, kind, filepath: relpath, relpath, text, distance: 0.3, hash: 'a'.repeat(64), read_at: kind === 'code_pointer' ? '2026-10-21T21:00:00-03:00' : '',
  lines: [1, 3], chunk_index: null, state: kind === 'code_pointer' ? 'current' : 'snapshot', section: null, full_file: kind === 'code_pointer',
  provenance: kind === 'code_pointer' ? { main_class: 'SteamLobbyManager' } : { source_url: 'https://partner.steamgames.com/doc/features/multiplayer/matchmaking', extracted_at: '2026-10-21T21:30:00-03:00', source_type: 'article' }, ...extra });

async function mockRag(page: Page, online = true) {
  const asks: string[] = [];
  await page.route('**/api/rag/**', async route => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace('/api/rag/', '');
    if (!online) return route.fulfill({ status: 503, json: { error: 'rag_offline', message: 'RAG local desligado. Ligue o helper (iniciar-tudo.cmd ou o botão Ligar) e aguarde alguns segundos.' } });
    if (path === 'health') return route.fulfill({ json: health });
    if (route.request().method() === 'POST') expect(route.request().headers()['x-orchestrator-request']).toBe('1');
    if (path === 'retrieve') return route.fulfill({ json: { query: 'q', bytes_read: 2048, files_read: ['Assets/Scripts/Salas/SteamLobbyManager.cs'], timings_ms: { embedding: 20, code: 5, documents: 3 },
      warnings: ['document_needs_reindex: antigo.md mudou ou sumiu desde a indexação.'],
      sources: [source('S1', 'code_pointer', 'Assets/Scripts/Salas/SteamLobbyManager.cs', 'public class SteamLobbyManager {}'), source('S2', 'documentation', 'artigo-x.md', 'Lobbies are created with CreateLobby.')] } });
    if (path === 'asks' && route.request().method() === 'POST') { asks.push(route.request().postDataJSON().request_id); return route.fulfill({ status: 202, json: { ask_id: 'ask1', state: 'queued' } }); }
    if (path === 'asks/ask1') return route.fulfill({ json: { id: 'ask1', query: 'Como o lobby é criado?', state: 'completed', progress: { stage: 'done', message: 'Concluído.', elapsed_ms: 400000 },
      result: { answer: 'O SteamLobbyManager chama CreateLobbyAsync [S1].', model: 'Qwen/Qwen2.5-1.5B-Instruct', prompt_tokens: 1662, generated_tokens: 120, timings_ms: { total: 400000 },
        warnings: ['context_excerpt: S1 (Assets/Scripts/Salas/SteamLobbyManager.cs) entrou só nas linhas 1-159 de 593.'],
        sources: [{ ...source('S1', 'code_pointer', 'Assets/Scripts/Salas/SteamLobbyManager.cs', 'public class SteamLobbyManager {}'), included: true, scope: 'lines 1-159' }] } } });
    return route.fulfill({ status: 404, json: { message: 'rota de teste ausente' } });
  });
  return asks;
}

test('consulta fontes reais com origem, hash e avisos, e mostra a resposta do modelo local', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  const asks = await mockRag(page);
  await page.goto('/#rag');
  await expect(page.getByText('Helper + RAG ligados neste PC')).toBeVisible();
  await expect(page.getByText(/494 scripts · 869 trechos de 12 documentos/)).toBeVisible();
  await page.getByLabel('Pergunta sobre o projeto').fill('Como o lobby é criado?');
  await page.getByRole('button', { name: 'Buscar fontes' }).click();
  await expect(page.getByText('[S1] Assets/Scripts/Salas/SteamLobbyManager.cs').first()).toBeVisible();
  await expect(page.getByText('Documento mudou — reindexe: antigo.md mudou ou sumiu desde a indexação.')).toBeVisible();
  await page.getByText('[S2] artigo-x.md').click();
  await expect(page.getByText('https://partner.steamgames.com/doc/features/multiplayer/matchmaking')).toBeVisible();
  await page.getByRole('button', { name: 'Perguntar ao modelo local' }).click();
  await expect(page.getByText('O SteamLobbyManager chama CreateLobbyAsync [S1].')).toBeVisible();
  await expect(page.getByText(/Trecho parcial: S1/)).toBeVisible();
  expect(asks).toHaveLength(1);
  expect(errors).toEqual([]);
});

test('RAG desligado mostra o motivo e oferece ligar, sem quebrar a janela de contexto', async ({ page }) => {
  await mockRag(page, false);
  await page.goto('/#rag');
  await expect(page.getByText('Helper + RAG desligados')).toBeVisible();
  await expect(page.getByText(/RAG local desligado/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ligar helper + RAG' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Buscar fontes' })).toBeDisabled();
  await page.goto('/#context');
  await expect(page.getByRole('heading', { name: 'Janela de contexto' })).toBeVisible();
  await expect(page.getByLabel('RAG local do DiceVTT')).toBeVisible();
});
