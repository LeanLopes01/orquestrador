import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
const root=process.env.JARVIS_HOME || 'C:\\J.A.R.V.I.S\\jarvis';
const python=`${root}\\.venv\\Scripts\\python.exe`;
let ownedHelper;
export function startHelper(){
  if(process.platform!=='win32'||ownedHelper)return;
  const child=spawn(python,['-m','jarvis_desktop','run'],{cwd:`${root}\\src`,stdio:'ignore',windowsHide:true});
  ownedHelper=child;
  child.on('exit',()=>{if(ownedHelper===child)ownedHelper=undefined;});
  child.on('error',()=>{if(ownedHelper===child)ownedHelper=undefined;});
  setTimeout(()=>{
    if(ownedHelper!==child)return;
    const workspace=process.env.JARVIS_WORKSPACE||resolve(import.meta.dirname,'..');
    const config=resolve(workspace,'.local/diagnostics.toml'),runner=resolve(workspace,'.venv-rag/Scripts/pythonw.exe');
    if(existsSync(config)&&existsSync(runner)){
      const audit=spawn(runner,['-m','dicevtt_diagnostics','--config',config,'request-startup'],{cwd:workspace,stdio:'ignore',windowsHide:true});
      audit.on('error',()=>{});
    }
  },1500).unref();
}
export function stopHelper(){
  if(!ownedHelper)return Promise.resolve(0);
  return new Promise(resolve=>{
    const child=spawn(python,['-m','jarvis_desktop','stop'],{cwd:`${root}\\src`,stdio:'ignore',windowsHide:true});
    const timer=setTimeout(()=>{child.kill();resolve(1);},45000);
    child.on('error',()=>{clearTimeout(timer);resolve(1);});
    child.on('exit',code=>{clearTimeout(timer);resolve(code??1);});
  });
}
export function lifecycleBridge(onShutdown){
 return {name:'lifecycle',configureServer(server){server.middlewares.use(async(req,res,next)=>{
  if(req.url!=='/api/system/exit')return next();
  const host=req.headers.host||'';
  if(req.method!=='POST'||req.headers['x-orchestrator-request']!=='1'||!/^127\.0\.0\.1:1420$/.test(host)||(req.headers.origin&&req.headers.origin!==`http://${host}`)){
   res.writeHead(403);res.end('{}');return;
  }
  const code=await stopHelper();
  res.setHeader('Content-Type','application/json');
  res.writeHead(code===0?200:409);
  res.end(JSON.stringify({stopped:code===0,message:code===3?'Há uma tarefa ativa. Cancele em Projetos ou aguarde a conclusão antes de sair.':code===0?'Serviços encerrados.':'Não foi possível encerrar os serviços. Tente novamente.'}));
  if(code===0)setTimeout(onShutdown,250);
 });}};
}
