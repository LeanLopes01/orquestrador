import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Mesmos casos que services/ingestion/tests/test_urls.py: a UI (WHATWG URL) e o Python
// precisam concordar na URL canônica dos artigos.
const cases = JSON.parse(readFileSync(new URL('../services/ingestion/tests/fixtures/url_cases.json', import.meta.url), 'utf8'));

test('canônicas de artigo iguais às do serviço Python', () => {
  for (const c of cases.filter(c => c.kind === 'article')) {
    const url = new URL(c.input);
    url.hash = '';
    assert.equal(url.href, c.canonical, c.input);
  }
});
