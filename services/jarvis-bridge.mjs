import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const script = fileURLToPath(new URL('./jarvis-request.py', import.meta.url));
const python = 'C:\\J.A.R.V.I.S\\jarvis\\.venv\\Scripts\\python.exe';
export function allowedRoute(method, path) {
  if (method === 'GET' && /^\/v1\/extension-calls\/[a-f0-9]{32}$/.test(path)) return true;
  if (method === 'PATCH' && /^\/v1\/extensions\/[a-z0-9-]+$/.test(path)) return true;
  if (method === 'POST' && /^\/v1\/(?:extensions\/[a-z0-9-]+\/prepare|extension-calls\/[a-f0-9]{32}\/execute)$/.test(path)) return true;
  if (method === 'GET' && /^\/v1\/(?:integrations|routines|device|extensions|updates)(?:\?[a-z_]+=[A-Za-z0-9_-]+)?$/.test(path)) return true;
  if (method === 'GET' && /^\/v1\/events\?after=\d{1,18}$/.test(path)) return true;
  if (method === 'PATCH' && /^\/v1\/integrations\/(?:google_a|google_b|notion|outlook)$/.test(path)) return true;
  if (method === 'POST' && path === '/v1/routines') return true;
  if (['PUT','DELETE'].includes(method) && /^\/v1\/routines\/[A-Za-z0-9_-]{1,64}$/.test(path)) return true;
  if (method === 'GET') return /^\/v1\/(?:projects|conversations(?:\/[a-zA-Z0-9-]+)?|plans\/pending|runs\/[a-zA-Z0-9-]+|orchestration\/(?:runtime|active))$/.test(path);
  if (method === 'POST') return /^\/v1\/(?:conversations(?:\/[a-zA-Z0-9-]+\/messages)?|plans\/[a-zA-Z0-9-]+\/(?:approve|reject)|runs\/[a-zA-Z0-9-]+\/cancel)$/.test(path);
  return false;
}
export function localRequest(req) {
  const host = req.headers.host || '';
  return /^(127\.0\.0\.1|localhost):1420$/.test(host)
    && (!req.headers.origin || req.headers.origin === `http://${host}`)
    && (!req.headers['sec-fetch-site'] || ['same-origin','none'].includes(req.headers['sec-fetch-site']));
}
export async function proxyRequest(data) {
  return await new Promise((resolve, reject) => {
    const child = spawn(python, [script], { windowsHide: true, stdio: ['pipe','pipe','ignore'], env: {...process.env, PYTHONIOENCODING:'utf-8'} });
    let output = '';
    const timer = setTimeout(() => { child.kill(); reject(new Error('timeout')); }, data.path.includes('/extension-calls/') ? 90000 : 15000);
    child.stdout.on('data', chunk => {
      output += chunk;
      if (output.length > 2100000) { child.kill(); reject(new Error('size')); }
    });
    child.on('error', error => {clearTimeout(timer); reject(error);});
    child.on('close', () => { clearTimeout(timer); try {resolve(JSON.parse(output));} catch {reject(new Error('bridge'));} });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify(data));
  });
}
export function jarvisBridge() {
  const configure = server => { server.middlewares.use(async (req,res,next) => {
    if (!req.url?.startsWith('/api/orchestrator/')) return next();
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control','no-store');
    const send = (status, body) => {res.writeHead(status); res.end(JSON.stringify(body));};
    if (!localRequest(req)) return send(403,{message:'Origem local obrigatória.'});
    if (req.url === '/api/orchestrator/health' && req.method === 'GET') return send(200,{service:'dicevtt-orchestrator',online:true});
    const path = req.url.slice('/api/orchestrator'.length);
    if (!allowedRoute(req.method, path)) return send(404,{message:'Rota indisponível.'});
    if (!['GET','HEAD'].includes(req.method) && req.headers['x-orchestrator-request'] !== '1') return send(403,{message:'Requisição inválida.'});
    try {
      let raw = '';
      for await (const chunk of req) {
        raw += chunk;
        if (Buffer.byteLength(raw) > 32000) return send(413,{message:'Pedido muito grande.'});
      }
      const result = await proxyRequest({method:req.method,path,body:raw ? JSON.parse(raw) : undefined});
      send(result.status,result.body);
    } catch {
      send(503,{message:'Conexão com o Jarvis indisponível.'});
    }
  }); };
  return {name:'jarvis-bridge',configureServer:configure,configurePreviewServer:configure};
}
