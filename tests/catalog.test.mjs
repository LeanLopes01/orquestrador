import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync,readdirSync} from 'node:fs';
import {createServer} from 'node:http';
import {mkdtemp,readFile,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const require=createRequire(import.meta.url);
const {vault,database}=require('../deploy/evolution/n8n-nodes/state.js');
const {run,mapInput}=require('../deploy/evolution/n8n-nodes/runner.js');
const {request}=require('../deploy/evolution/n8n-nodes/network.js');
const {fileBridge}=require('../deploy/evolution/n8n-nodes/files.js');
const {JarvisCatalog}=require('../deploy/evolution/n8n-nodes/JarvisCatalog.node.js');
const {mailBridge}=require('../deploy/evolution/n8n-nodes/mail.js');
const root=new URL('../deploy/evolution/catalog-source/',import.meta.url);

test('all 75 catalog records compile and every tool maps to a fixed action',()=>{
 const files=readdirSync(root);assert.equal(files.length,75);
 for(const file of files){const record=JSON.parse(readFileSync(new URL(file,root),'utf8'));
  if(record.type==='native'){
   const code=record.workflow.sub.nodes.find(n=>n.type==='n8n-nodes-base.code').parameters.jsCode;
   new (Object.getPrototypeOf(async function(){}).constructor)(code);
   for(const entry of record.manifest.tools)assert.ok(mapInput(record,typeof entry==='string'?entry:entry.name,{}));
  }
 }
});
test('custom node executes the clock connector with an encrypted state credential',async()=>{
 const state={};const node=new JarvisCatalog();
 const result=await node.execute.call({
  getNodeParameter:(name,_index,fallback)=>name==='template'?'timezone-world-clock':fallback,
  getCredentials:async()=>({stateSecret:'clock-test-'.repeat(4),configuration:'{}'}),
  getWorkflowStaticData:()=>state,
  getInputData:()=>[{json:{body:{tool:'get_time',arguments:{timezone:'America/Sao_Paulo'}}}}],
 });
 assert.equal(result.length,1);assert.ok(!result[0][0].json.error,JSON.stringify(result));
 assert.match(JSON.stringify(result),/Paulo/);assert.ok(state.encrypted);
});
test('encrypted state cannot be read with another connection key',()=>{
 const data={},key={stateSecret:'a'.repeat(32)};const value=vault(data,key);value.state.tokens={access_token:'hidden-value'};value.save();
 assert.ok(!JSON.stringify(data).includes('hidden-value'));assert.deepEqual(vault(data,key).state,value.state);
 assert.throws(()=>vault(data,{stateSecret:'b'.repeat(32)}));
});
test('credential store is isolated and unknown tool never reaches network',async()=>{
 const state={};database(state,{api_key:'one'},{url:'https://jarvis-state.invalid/rest/v1/template_credentials',method:'POST',body:{cred_key:'access_token',cred_value:'two'}});
 assert.equal(database(state,{api_key:'one'},{url:'https://jarvis-state.invalid/rest/v1/template_credentials?cred_key=eq.access_token'})[0].cred_value,'two');
 const record=JSON.parse(readFileSync(new URL(readdirSync(root)[0],root),'utf8'));
 await assert.rejects(run(record,'__invalid__',{}, {}, {},{httpRequest:()=>assert.fail('network')}));
});
test('network pins DNS, blocks private hosts and validates every redirect',async()=>{
 const server=createServer((req,res)=>{if(req.url==='/redirect'){res.writeHead(302,{Location:'http://localhost:12/x'});res.end();}else{res.setHeader('Content-Type','application/json');res.end('{"ok":true}');}});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin=`http://127.0.0.1:${server.address().port}`;
 try{
  await assert.rejects(request({url:origin},{hosts:['127.0.0.1']}),/privada/);
  const policy={origins:[origin],privateNetwork:true};assert.deepEqual(await request({url:origin},policy),{ok:true});
  await assert.rejects(request({url:origin+'/redirect'},policy),/origens/);
 }finally{await new Promise(resolve=>server.close(resolve));}
});
test('file bridge stores encrypted bytes and reuses network policy for forwarding',async()=>{
 const folder=await mkdtemp(join(tmpdir(),'jarvis-files-test-'));
 const data='private-test-document';
 const meta=await fileBridge({url:'http://file-bridge:3200/upload/base64',method:'POST',body:{content_base64:Buffer.from(data).toString('base64'),file_name:'demo.txt'}},{},request,folder);
 for(const name of await readdir(folder))assert.ok(!(await readFile(join(folder,name))).includes(Buffer.from(data)));
 assert.equal(await fileBridge({url:'http://file-bridge:3200/files/'+meta.id},{},request,folder),data);
 await assert.rejects(fileBridge({url:'http://file-bridge:3200/files/'+meta.id+'/forward',method:'POST',body:{url:'http://127.0.0.1/private'}},{},request,folder),/política/);
 await fileBridge({url:'http://file-bridge:3200/files/'+meta.id,method:'DELETE'},{},request,folder);
 await assert.rejects(fileBridge({url:'http://file-bridge:3200/files/'+meta.id},{},request,folder));
});
test('mail bridge blocks an unlisted server before authenticating or sending',async()=>{
 await assert.rejects(mailBridge({url:'http://email-bridge:3100/send-email',body:{host:'smtp.example.com',port:587,user:'test',password:'test'}},{origins:[]}),/Cadastre/);
 await assert.rejects(mailBridge({url:'http://email-bridge:3100/read-emails',body:{host:'imap.example.com',port:143,user:'test',password:'test'}},{origins:[]}),/TLS/);
});
