// Isolated integration test against the same n8n release as the server.
import {spawn,execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {appendFileSync} from 'node:fs';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..'),home=resolve(root,`.local/evolution/n8n-sandbox-${Date.now()}`);
await mkdir(home,{recursive:true});
await writeFile(resolve(root,'.local/evolution/n8n-last-sandbox.txt'),home);
const env={...process.env,N8N_USER_FOLDER:home,N8N_CUSTOM_EXTENSIONS:resolve(root,'deploy/evolution/n8n-nodes'),NODES_INCLUDE:'["CUSTOM.jarvisCatalog","n8n-nodes-base.webhook"]',N8N_LOG_LEVEL:'debug',N8N_PORT:'5687',N8N_LISTEN_ADDRESS:'127.0.0.1',N8N_RUNNERS_ENABLED:'false',N8N_DIAGNOSTICS_ENABLED:'false',N8N_ENCRYPTION_KEY:'test-only-not-a-production-secret',EXECUTIONS_DATA_SAVE_ON_SUCCESS:'none',EXECUTIONS_DATA_SAVE_ON_ERROR:'none'};
const cli=resolve(root,'.local/n8n-validation/node_modules/n8n/bin/n8n');
const registry=JSON.parse(await readFile(resolve(root,'deploy/evolution/registry.json'),'utf8'));
const entry=registry.entries.find(e=>e.id==='timezone-world-clock');
const creds=[{id:'jarvisGatewayAuth',name:'Test gateway',type:'httpHeaderAuth',data:{name:'X-Jarvis-Gateway',value:'test-only'}},{id:entry.credential_id,name:'Test account',type:'jarvisConnection',data:{stateSecret:'test-only-'.repeat(8),configuration:'{}',origins:'',privateNetwork:false}}];
await writeFile(resolve(home,'credentials.json'),JSON.stringify(creds));
const exec=promisify(execFile);
for(const args of [['import:credentials',`--input=${resolve(home,'credentials.json')}`],['import:workflow',`--input=${resolve(root,'deploy/evolution/workflows/timezone-world-clock.json')}`],['publish:workflow',`--id=${entry.workflow_id}`]]){
 process.stdout.write(`n8n: ${args[0]}\n`);
 try{await exec(process.execPath,[cli,...args],{env,timeout:300000,maxBuffer:5e6,windowsHide:true});}
 catch(e){await writeFile(resolve(home,'cli-error.log'),String(e.stdout)+String(e.stderr));throw Error('n8n CLI failed; see sandbox/cli-error.log');}
}
const child=spawn(process.execPath,[cli,'start'],{env,windowsHide:true,stdio:['ignore','pipe','pipe']});
const serverLog=resolve(home,'server.log');
child.stdout.on('data',chunk=>appendFileSync(serverLog,chunk));child.stderr.on('data',chunk=>appendFileSync(serverLog,chunk));
const url='http://127.0.0.1:5687';
try{
 let ready=false;
 const deadline=Date.now()+300000;
 while(Date.now()<deadline){if(child.exitCode!==null)break;if(await fetch(url+'/healthz/readiness',{signal:AbortSignal.timeout(1500)}).then(r=>r.ok).catch(()=>false)){ready=true;break;}await new Promise(r=>setTimeout(r,1000));}
 assert.ok(ready,'n8n readiness');
 const webhook=url+'/webhook/jarvis-catalog/timezone-world-clock';
 // Readiness precedes asynchronous webhook publication in n8n 2.44.
 let r; const publishedDeadline=Date.now()+60000;
 do {
  r=await fetch(webhook,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(10000)});
  if(![404,503].includes(r.status))break;
  await r.arrayBuffer();await new Promise(resolve=>setTimeout(resolve,500));
 }while(Date.now()<publishedDeadline);
 assert.equal(r.status,403);await r.arrayBuffer();
 r=await fetch(webhook,{method:'POST',headers:{'Content-Type':'application/json','X-Jarvis-Gateway':'test-only'},body:JSON.stringify({tool:'get_time',arguments:{timezone:'America/Sao_Paulo'}}),signal:AbortSignal.timeout(20000)});
 const result=await r.text();await writeFile(resolve(home,'result.json'),result);
 assert.equal(r.status,200,result);assert.ok(!result.includes('"error"'),result);assert.match(result,/Paulo|2026|time/i);
 process.stdout.write('PASS: real n8n 2.44.6 imports custom credential/workflow, denies anonymous calls and executes the clock connector.\n');
}finally{
 // Kill only this disposable n8n process tree, including its test task runner.
 if(process.platform==='win32')await exec('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true}).catch(()=>{});
 else child.kill();
}
