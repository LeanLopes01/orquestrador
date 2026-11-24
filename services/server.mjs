// Production loopback host. Reuses the exact allowlisted bridges tested in development.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { contextBridge } from './context-bridge.mjs';
import { jarvisBridge } from './jarvis-bridge.mjs';
import { ragBridge } from './rag-bridge.mjs';
import { ingestionBridge } from './ingestion-bridge.mjs';
import { auditsBridge } from './audits-bridge.mjs';
import { systemBridge } from './system-bridge.mjs';
import { startHelper, stopHelper, lifecycleBridge } from './lifecycle.mjs';

export function productionServer({dist=resolve(fileURLToPath(new URL('..',import.meta.url)),'dist'),onShutdown=()=>{}}={}) {
  const stack=[];
  const adapter={middlewares:{use:(path, fn) => stack.push(typeof path === 'function' ? {fn:path} : {path,fn})}};
  for (const plugin of [contextBridge(),jarvisBridge(),...ragBridge(),ingestionBridge(),auditsBridge(),systemBridge(),lifecycleBridge(onShutdown)]) plugin.configureServer(adapter);
  return createServer((req,res) => {
    res.setHeader('X-Content-Type-Options','nosniff');
    res.setHeader('Referrer-Policy','no-referrer');
    res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
    const host=req.headers.host || '';
    if (!/^(localhost|127\.0\.0\.1):1420$/.test(host)) {res.writeHead(403);res.end();return;}
    let index=0;
    const fail=()=>{if(!res.headersSent)res.writeHead(500);if(!res.writableEnded)res.end('{"message":"Falha no serviço local."}');};
    const next=async()=>{
      const item=stack[index++];
      if(item){
        if(item.path && req.url.split('?')[0]!==item.path)return next();
        try {await item.fn(req,res,next);} catch {fail();}
        return;
      }
      if(req.url.startsWith('/api/')){res.writeHead(404);res.end('{"message":"Rota indisponível."}');return;}
      if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
      try {
        const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
        let file=resolve(dist,'.'+name);
        if(file!==dist&&!file.startsWith(dist+sep)){res.writeHead(403);res.end();return;}
        if((await stat(file).catch(()=>null))?.isDirectory())file=resolve(file,'index.html');
        const content=await readFile(file).catch(()=>null);
        if(!content){res.writeHead(404);res.end();return;}
        res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.json':'application/json','.png':'image/png','.ico':'image/x-icon'})[extname(file)]||'application/octet-stream');
        res.setHeader('Cache-Control',extname(file)==='.html'?'no-store':'public, max-age=3600');
        res.end(req.method==='HEAD'?undefined:content);
      }catch{fail();}
    };
    void next();
  });
}
export function isDirectRun(argv1=process.argv[1],metaUrl=import.meta.url) {
  return Boolean(argv1) && resolve(argv1.replace(/^\\\\\?\\/,''))===fileURLToPath(metaUrl);
}
if(isDirectRun()){
  process.env.JARVIS_PRODUCTION='1';
  const server=productionServer({onShutdown:()=>server.close(()=>process.exit(0))});
  server.on('error',e=>{process.stderr.write(`Jarvis não iniciou: ${e.code || 'erro'}.\n`);process.exitCode=1;});
  server.listen(1420,'127.0.0.1',()=>{process.stdout.write('Jarvis: http://127.0.0.1:1420\n');if(process.argv.includes('--with-helper'))startHelper();});
  if (/^\d+$/.test(process.env.JARVIS_PARENT_PID||'')) {
    const parent=Number(process.env.JARVIS_PARENT_PID);
    let stopping=false;
    setInterval(async()=>{
      try {process.kill(parent,0);} catch {
        if(stopping)return;stopping=true;
        const code=await stopHelper();
        if(code===0)server.close(()=>process.exit(0));
        else stopping=false; // Never kill a running project; retry graceful exit.
      }
    },5000).unref();
  }
  for(const signal of ['SIGINT','SIGTERM']) process.on(signal,async()=>{const code=await stopHelper();if(code===0)server.close(()=>process.exit(0));else process.stderr.write('Tarefa ativa ou falha de encerramento. Cancele pelo Jarvis e tente novamente.\n');});
}
