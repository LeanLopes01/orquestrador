import { fileURLToPath } from 'node:url';
import { serviceBridge } from './local-service-proxy.mjs';

// /api/audits/* → 127.0.0.1:8768/v1/* (runner de relatórios). O token fica no Vite.
const root = process.env.JARVIS_WORKSPACE ? process.env.JARVIS_WORKSPACE.replace(/[\\/]$/, '') + '/' : fileURLToPath(new URL('..', import.meta.url));
const tokenFile = `${root}.local/audits/api-token`;
const run = 'AUD-\\d{8}-\\d{6}-[0-9a-f]{6}';

// A ponte remonta o caminho: /api/audits/health → /v1/audits/health, que o runner expõe como /v1/diagnostics/health.
export function auditsPath(path) {
  if (path === '/v1/audits/health') return '/v1/diagnostics/health';
  if (path === '/v1/audits/settings') return '/v1/settings';
  if (path === '/v1/audits/runs') return '/v1/audits';
  return path.replace(/^\/v1\/audits\/runs\//, '/v1/audits/');
}

export function allowedAuditRoute(method, path) {
  if (method === 'GET') return new RegExp(`^/v1/audits/(?:health|settings|runs|runs/${run}|runs/${run}/report)$`).test(path);
  if (method === 'PUT') return path === '/v1/audits/settings';
  if (method === 'POST') return new RegExp(`^/v1/audits/(?:runs|runs/${run}/(?:cancel|investigation))$`).test(path);
  return false;
}

export function auditsBridge() {
  return serviceBridge({
    name: 'audits', mount: '/api/audits', upstream: '/v1/audits', port: 8768, tokenFile,
    allowedRoute: (method, path) => allowedAuditRoute(method, path),
    rewrite: auditsPath,
    requestHeaders: ['idempotency-key'],
    responseHeaders: ['content-type', 'content-disposition', 'content-security-policy', 'x-content-type-options'],
    timeoutMs: 15000, maxBody: 64000,
    offlineMessage: 'Runner de relatórios desligado. Ele sobe junto com o helper (iniciar-tudo.cmd).',
  });
}
