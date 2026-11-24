import test from 'node:test';
import assert from 'node:assert/strict';
import { allowedRagRoute } from '../services/rag-bridge.mjs';
import { allowedIngestionRoute } from '../services/ingestion-bridge.mjs';
import { localRequest } from '../services/local-service-proxy.mjs';

test('ponte RAG só expõe rotas fixas', () => {
  assert.ok(allowedRagRoute('GET', '/v1/rag/health'));
  assert.ok(allowedRagRoute('GET', '/v1/rag/document-folder'));
  assert.ok(allowedRagRoute('POST', '/v1/rag/document-folder/open'));
  assert.ok(!allowedRagRoute('POST', '/v1/rag/document-folder/open/../../other'));
  assert.ok(allowedRagRoute('POST', '/v1/rag/retrieve'));
  assert.ok(allowedRagRoute('GET', '/v1/rag/asks/abc123'));
  assert.ok(allowedRagRoute('POST', '/v1/rag/asks/abc123/cancel'));
  assert.ok(!allowedRagRoute('GET', '/v1/rag/asks/../../etc'));
  assert.ok(!allowedRagRoute('DELETE', '/v1/rag/asks/abc'));
  assert.ok(!allowedRagRoute('POST', '/v1/rag/retrieve/extra'));
});

test('ponte de ingestão só expõe rotas fixas', () => {
  assert.ok(allowedIngestionRoute('POST', '/v1/ingestion/batches'));
  assert.ok(allowedIngestionRoute('POST', '/v1/ingestion/batches/abc/cancel'));
  assert.ok(!allowedIngestionRoute('POST', '/v1/ingestion/shutdown'));
  assert.ok(!allowedIngestionRoute('GET', '/v1/ingestion/documents/../x'));
});

test('somente requisições da própria origem local', () => {
  assert.ok(localRequest({headers: {host: '127.0.0.1:1420'}}));
  assert.ok(!localRequest({headers: {host: 'evil.example:1420'}}));
  assert.ok(!localRequest({headers: {host: '127.0.0.1:1420', origin: 'http://evil.example'}}));
  assert.ok(!localRequest({headers: {host: '127.0.0.1:1420', 'sec-fetch-site': 'cross-site'}}));
});
