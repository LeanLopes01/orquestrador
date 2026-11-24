import { readVault } from './context-reader.mjs';
import { localRequest } from './local-service-proxy.mjs';

export function contextBridge() {
  const configure = server => { server.middlewares.use(async (req, res, next) => {
    if (req.url?.split('?')[0] !== '/api/context') return next();
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    if (!localRequest(req)) { res.writeHead(403); res.end('{}'); return; }
    if (req.method !== 'GET') { res.writeHead(405); res.end('{}'); return; }
    try {
      const vaultRoot = process.env.ORCHESTRATOR_VAULT || 'C:\\J.A.R.V.I.S\\JanelaContextoPessoal';
      const data = await readVault(vaultRoot, {
        maxNotes: 5000,
        maxEntries: 200000,
        maxBytes: 1_048_576,
        maxBodyChars: 24_000,
        truncateLarge: true,
      });
      res.end(JSON.stringify(data));
    } catch {
      res.writeHead(503);
      res.end(JSON.stringify({ error: 'Contexto local indisponível. Confira a pasta configurada.' }));
    }
  }); };
  return { name: 'context-bridge', configureServer: configure, configurePreviewServer: configure };
}
