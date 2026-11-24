import { fileURLToPath } from 'node:url';
import { serviceBridge } from './local-service-proxy.mjs';

// /api/ingestion/* → 127.0.0.1:8766/v1/ingestion/* (serviço rag_ingestion).
const root = process.env.JARVIS_WORKSPACE ? process.env.JARVIS_WORKSPACE.replace(/[\\/]$/, '') + '/' : fileURLToPath(new URL('..', import.meta.url));
const id = '[A-Za-z0-9]{1,64}';

export function allowedIngestionRoute(method, path) {
  if (method === 'GET') return new RegExp(`^/v1/ingestion/(?:health|batches|batches/${id}|documents|documents/${id})$`).test(path);
  if (method === 'POST') return new RegExp(`^/v1/ingestion/(?:batches|batches/${id}/(?:cancel|resume))$`).test(path);
  return false;
}

export function ingestionBridge() {
  return serviceBridge({name: 'ingestion', mount: '/api/ingestion', upstream: '/v1/ingestion', port: 8766,
    tokenFile: `${root}.local/ingestion/api-token`, allowedRoute: allowedIngestionRoute,
    offlineMessage: 'Serviço de ingestão desligado. Ele sobe junto com o helper (iniciar-tudo.cmd).'});
}
