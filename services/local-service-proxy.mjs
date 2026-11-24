import { readFile } from 'node:fs/promises';
import { request } from 'node:http';

// Proxy da UI local para um serviço Python em 127.0.0.1. O token fica no servidor Vite:
// o navegador nunca o recebe. Só rotas fixas; POST exige o cabeçalho anti-CSRF da UI.
export function localRequest(req) {
  const host = req.headers.host || '';
  return /^(127\.0\.0\.1|localhost):1420$/.test(host)
    && (!req.headers.origin || req.headers.origin === `http://${host}`)
    && (!req.headers['sec-fetch-site'] || ['same-origin','none'].includes(req.headers['sec-fetch-site']));
}

export async function readToken(file) {
  try { return (await readFile(file, 'ascii')).trim(); } catch { return ''; }
}

export function forward({port, path, method, body, token, timeoutMs, headers = {}}) {
  return new Promise((resolve, reject) => {
    const upstream = request({host: '127.0.0.1', port, path, method, headers: {
      ...headers, 'Content-Type': 'application/json', 'X-Local-Token': token, ...(body ? {'Content-Length': Buffer.byteLength(body)} : {}),
    }}, res => {
      let data = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { data += chunk; if (data.length > 8_000_000) { upstream.destroy(); reject(new Error('size')); } });
      res.on('end', () => resolve({status: res.statusCode || 502, data, headers: res.headers}));
    });
    upstream.setTimeout(timeoutMs, () => upstream.destroy(new Error('timeout')));
    upstream.on('error', reject);
    if (body) upstream.write(body);
    upstream.end();
  });
}

// requestHeaders: cabeçalhos do navegador repassados ao serviço (ex.: Idempotency-Key).
// responseHeaders: cabeçalhos do serviço devolvidos ao navegador (ex.: download de relatório).
// rewrite: caminho público já validado → caminho real do serviço.
export function serviceBridge({name, mount, upstream, port, tokenFile, allowedRoute, offlineMessage, timeoutMs = 70000, maxBody = 512000, requestHeaders = [], responseHeaders = [], rewrite = path => path}) {
  const configure = server => { server.middlewares.use(async (req, res, next) => {
    if (!req.url?.startsWith(`${mount}/`)) return next();
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    const send = (status, payload) => { res.writeHead(status); res.end(typeof payload === 'string' ? payload : JSON.stringify(payload)); };
    if (!localRequest(req)) return send(403, {message: 'Origem local obrigatória.'});
    const url = new URL(req.url, 'http://local');
    const path = upstream + url.pathname.slice(mount.length);
    if (!allowedRoute(req.method, path)) return send(404, {message: 'Rota indisponível.'});
    const withBody = req.method === 'POST' || req.method === 'PUT';
    if (withBody && req.headers['x-orchestrator-request'] !== '1') return send(403, {message: 'Requisição inválida.'});
    let raw = '';
    for await (const chunk of req) {
      raw += chunk;
      if (Buffer.byteLength(raw) > maxBody) return send(413, {message: 'Pedido muito grande.'});
    }
    const headers = Object.fromEntries(requestHeaders.filter(h => typeof req.headers[h] === 'string').map(h => [h, req.headers[h]]));
    try {
      const result = await forward({port, path: rewrite(path) + url.search, method: req.method, body: withBody ? (raw || '{}') : undefined, token: await readToken(tokenFile), timeoutMs, headers});
      for (const h of responseHeaders) if (result.headers?.[h]) res.setHeader(h, result.headers[h]);
      send(result.status, result.data || '{}');
    } catch {
      send(503, {error: `${name}_offline`, message: offlineMessage});
    }
  }); };
  return {name: `${name}-bridge`, configureServer: configure, configurePreviewServer: configure};
}
