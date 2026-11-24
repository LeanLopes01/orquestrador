import os from 'node:os';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { localRequest } from './local-service-proxy.mjs';

const catalogFile = fileURLToPath(new URL('../docs/planejamento-jarvis/catalogo-n8n-claw.json', import.meta.url));
let catalog;
export async function publicCatalog() {
  if (!catalog) {
    const snapshot = JSON.parse(await readFile(catalogFile, 'utf8'));
    catalog = { revision: snapshot.revision, entries: snapshot.entries.map(({id, source, manifest:m}) => ({
      id, source, name:m.name, category:m.category, type:m.type || 'native', version:m.version,
      description:m.description, fields:m.credentials_required || [], optional_fields:m.credentials_optional || [],
      tools:(m.tools || []).map(t => typeof t === 'string' ? t : t.name),
    })) };
  }
  return catalog;
}
export function systemBridge() {
  const configure = server => { server.middlewares.use(async (req, res, next) => {
    if (!['/api/system/status', '/api/catalog'].includes(req.url)) return next();
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    if (!localRequest(req) || req.method !== 'GET') { res.writeHead(403); res.end('{}'); return; }
    try {
      const body = req.url === '/api/catalog' ? await publicCatalog() : {
        observed_at: new Date().toISOString(), host:os.hostname(), platform:os.platform(),
        cpu_count:os.cpus().length, memory_total:os.totalmem(), memory_free:os.freemem(),
        uptime_seconds:os.uptime(), runtime: process.env.JARVIS_PRODUCTION === '1' ? 'production' : 'development',
        gpu: null, version:'0.3.0',
      };
      res.end(JSON.stringify(body));
    } catch { res.writeHead(503); res.end(JSON.stringify({message:'Não foi possível consultar este recurso.'})); }
  }); };
  return {name:'jarvis-system',configureServer:configure,configurePreviewServer:configure};
}
