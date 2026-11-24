import { startHelper } from './lifecycle.mjs';
import { fileURLToPath } from 'node:url';
import { localRequest, serviceBridge } from './local-service-proxy.mjs';

// /api/rag/* → 127.0.0.1:8767/v1/rag/* (serviço unity_rag, separado da ponte Jarvis).
const root = process.env.JARVIS_WORKSPACE ? process.env.JARVIS_WORKSPACE.replace(/[\\/]$/, '') + '/' : fileURLToPath(new URL('..', import.meta.url));
const tokenFile = `${root}.local/rag/api-token`;
const id = '[A-Za-z0-9]{1,64}';

export function allowedRagRoute(method, path) {
  if (method === 'GET') return new RegExp(`^/v1/rag/(?:health|document-folder|asks|asks/${id}|index-jobs/${id})$`).test(path);
  if (method === 'POST') return new RegExp(`^/v1/rag/(?:retrieve|document-folder/open|asks|asks/${id}/cancel|index-jobs|shutdown)$`).test(path);
  return false;
}

// Ligar a partir da UI: inicia o helper Jarvis Desktop, que sobe o RAG junto.
// Desligar usa POST /api/rag/shutdown: o RAG sai com código 0 e o helper encerra junto.
function helperControl() {
  const configure = server => { server.middlewares.use('/api/rag-control/start', (req, res) => {
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    if (!localRequest(req) || req.method !== 'POST' || req.headers['x-orchestrator-request'] !== '1') {
      res.writeHead(403); res.end(JSON.stringify({message: 'Requisição inválida.'})); return;
    }
    try {
      startHelper();
      res.writeHead(202); res.end(JSON.stringify({starting: true, message: 'Helper iniciando; o RAG sobe junto em alguns segundos.'}));
    } catch {
      res.writeHead(503); res.end(JSON.stringify({message: 'Não foi possível iniciar o helper Jarvis Desktop.'}));
    }
  }); };
  return {name: 'rag-helper-control', configureServer: configure, configurePreviewServer: configure};
}

export function ragBridge() {
  return [
    serviceBridge({name: 'rag', mount: '/api/rag', upstream: '/v1/rag', port: 8767, tokenFile, allowedRoute: allowedRagRoute,
      offlineMessage: 'RAG local desligado. Ligue o helper (iniciar-tudo.cmd ou o botão Ligar) e aguarde alguns segundos.'}),
    helperControl(),
  ];
}
