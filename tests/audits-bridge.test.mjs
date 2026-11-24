import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer, request } from 'node:http';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { allowedAuditRoute, auditsPath } from '../services/audits-bridge.mjs';
import { serviceBridge } from '../services/local-service-proxy.mjs';

const RUN = 'AUD-20261025-210206-b897ac';

test('ponte de relatórios só expõe rotas fixas', () => {
  assert.ok(allowedAuditRoute('GET', '/v1/audits/health'));
  assert.ok(allowedAuditRoute('GET', `/v1/audits/runs/${RUN}`));
  assert.ok(allowedAuditRoute('GET', `/v1/audits/runs/${RUN}/report`));
  assert.ok(allowedAuditRoute('POST', '/v1/audits/runs'));
  assert.ok(allowedAuditRoute('POST', `/v1/audits/runs/${RUN}/cancel`));
  assert.ok(allowedAuditRoute('POST', `/v1/audits/runs/${RUN}/investigation`));
  assert.ok(!allowedAuditRoute('GET', `/v1/audits/runs/${RUN}/investigation`));
  assert.ok(allowedAuditRoute('PUT', '/v1/audits/settings'));
  assert.ok(!allowedAuditRoute('POST', '/v1/audits/shutdown'));
  assert.ok(!allowedAuditRoute('GET', '/v1/audits/runs/../../etc'));
  assert.ok(!allowedAuditRoute('GET', '/v1/audits/runs/AUD-1'));
  assert.ok(!allowedAuditRoute('DELETE', `/v1/audits/runs/${RUN}`));
  assert.ok(!allowedAuditRoute('PUT', '/v1/audits/runs'));
});

test('caminhos públicos viram as rotas do runner', () => {
  assert.equal(auditsPath('/v1/audits/health'), '/v1/diagnostics/health');
  assert.equal(auditsPath('/v1/audits/settings'), '/v1/settings');
  assert.equal(auditsPath('/v1/audits/runs'), '/v1/audits');
  assert.equal(auditsPath(`/v1/audits/runs/${RUN}/report`), `/v1/audits/${RUN}/report`);
});

async function listen(handler) {
  const server = createServer(handler);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  return server;
}

function call(port, {method = 'GET', path, headers = {}, body}) {
  return new Promise((resolve, reject) => {
    const req = request({host: '127.0.0.1', port, path, method, headers: {host: '127.0.0.1:1420', ...headers}}, res => {
      let data = ''; res.on('data', c => { data += c; }); res.on('end', () => resolve({status: res.statusCode, headers: res.headers, data}));
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

test('repasse de Idempotency-Key, PUT protegido e cabeçalhos do download', async () => {
  const seen = [];
  const upstream = await listen((req, res) => {
    seen.push({method: req.method, url: req.url, key: req.headers['idempotency-key'], token: req.headers['x-local-token'], cookie: req.headers.cookie});
    if (req.url.endsWith('/report?format=html')) {
      res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8', 'Content-Disposition': 'attachment; filename="r.html"', 'X-Upstream-Secret': 'nao-repassar'});
      res.end('<p>ok</p>'); return;
    }
    res.writeHead(202, {'Content-Type': 'application/json'}); res.end('{"run_id":"x"}');
  });
  const dir = await mkdtemp(join(tmpdir(), 'audits-bridge-'));
  await writeFile(join(dir, 'token'), 'token-local-de-teste');
  let handler;
  const plugin = serviceBridge({
    name: 'audits', mount: '/api/audits', upstream: '/v1/audits', port: upstream.address().port, tokenFile: join(dir, 'token'),
    allowedRoute: allowedAuditRoute, rewrite: auditsPath, requestHeaders: ['idempotency-key'],
    responseHeaders: ['content-type', 'content-disposition'], offlineMessage: 'off',
  });
  plugin.configureServer({middlewares: {use(fn) { handler = fn; }}});
  const bridge = await listen((req, res) => handler(req, res, () => { res.writeHead(404); res.end(); }));
  const port = bridge.address().port;
  try {
    const created = await call(port, {method: 'POST', path: '/api/audits/runs', body: '{}', headers: {'x-orchestrator-request': '1', 'idempotency-key': 'k-12345678', cookie: 'sessao=1'}});
    assert.equal(created.status, 202);
    assert.deepEqual(seen[0], {method: 'POST', url: '/v1/audits', key: 'k-12345678', token: 'token-local-de-teste', cookie: undefined});
    const noCsrf = await call(port, {method: 'PUT', path: '/api/audits/settings', body: '{}'});
    assert.equal(noCsrf.status, 403);
    const report = await call(port, {path: `/api/audits/runs/${RUN}/report?format=html`});
    assert.equal(report.headers['content-type'], 'text/html; charset=utf-8');
    assert.equal(report.headers['content-disposition'], 'attachment; filename="r.html"');
    assert.equal(report.headers['x-upstream-secret'], undefined);
    assert.equal(seen.at(-1).url, `/v1/audits/${RUN}/report?format=html`);
    const foreign = await call(port, {path: '/api/audits/health', headers: {origin: 'http://evil.example'}});
    assert.equal(foreign.status, 403);
  } finally {
    bridge.close(); upstream.close();
  }
});
