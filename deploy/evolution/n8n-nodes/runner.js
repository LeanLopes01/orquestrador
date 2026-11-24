const vm=require('node:vm');
const crypto=require('node:crypto');
const {request}=require('./network');
const {database}=require('./state');
const {fileBridge}=require('./files');
const {mailBridge}=require('./mail');
function mapInput(record,tool,args){
 const node=record.workflow.server.nodes.find(n=>n.type.endsWith('.toolWorkflow')&&(n.parameters.name||n.name)===tool);
 if(!node)throw Error('Ferramenta ausente no workflow.');
 const mapping=node.parameters.workflowInputs?.value||{};const result={};
 for(const [key,value] of Object.entries(mapping)){
  if(typeof value==='string'&&value.startsWith('=')){
   const match=value.match(/\$fromAI\(['"]([^'"]+)['"]/);
   if(!match)throw Error('Mapeamento de ferramenta não suportado.');
   if(args[match[1]]!==undefined)result[key]=args[match[1]];
  }else result[key]=value;
 }
 return result;
}
function hosts(code){
 return [...new Set([...code.matchAll(/https?:\/\/([a-zA-Z0-9.-]+)(?=[/:'"`])/g)].map(m=>m[1]).filter(h=>h.includes('.')&&!h.endsWith('.invalid')))];
}
function redact(value,secrets){
 let result=JSON.stringify(value);
 for(const secret of Object.values(secrets))if(typeof secret==='string'&&secret.length>=8)result=result.split(secret).join('[redacted]');
 if(result.length>120000)return [{json:{error:'Resposta excede o limite. Reduza a consulta.'}}];
 return JSON.parse(result);
}
function parseMcp(body){
 if(typeof body!=='string')return body;
 for(const line of body.split('\n').reverse())if(line.startsWith('data: ')){try{return JSON.parse(line.slice(6));}catch{}}
 try{return JSON.parse(body);}catch{throw Error('Resposta MCP inválida.');}
}
async function bridge(record,tool,args,config,policy,httpRequest){
 const settings=record.manifest.bridge;const url=settings.mcp_url;
 const headers={'Content-Type':'application/json',Accept:'application/json, text/event-stream'};
 if(settings.auth_type==='bearer')headers.Authorization=`Bearer ${config.auth_token||''}`;
 const init=await httpRequest({method:'POST',url,headers,returnFullResponse:true,body:{jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-03-26',capabilities:{},clientInfo:{name:'Jarvis',version:'0.3.0'}}}},policy);
 const response=parseMcp(init.body);
 if(response.error)throw Error('Inicialização MCP recusada.');
 headers['MCP-Protocol-Version']=response.result?.protocolVersion||'2025-03-26';
 if(init.headers?.['mcp-session-id'])headers['Mcp-Session-Id']=init.headers['mcp-session-id'];
 await httpRequest({method:'POST',url,headers,body:{jsonrpc:'2.0',method:'notifications/initialized'}},policy);
 const result=parseMcp(await httpRequest({method:'POST',url,headers,body:{jsonrpc:'2.0',id:2,method:'tools/call',params:{name:tool,arguments:args}}},policy));
 return [{json:result.result||{error:result.error?.message||'MCP sem resultado.'}}];
}
async function execute(record,tool,args,config,state,options={}){
 const names=record.manifest.tools.map(t=>typeof t==='string'?t:t.name);
 if(!names.includes(tool))throw Error('Ferramenta não permitida.');
 if(!args||typeof args!=='object'||Array.isArray(args)||JSON.stringify(args).length>32000)throw Error('Argumentos inválidos.');
 const code=record.type==='native'?record.workflow.sub.nodes.filter(n=>n.type==='n8n-nodes-base.code').map(n=>n.parameters.jsCode).join('\n'):'';
 const policy={hosts:record.type==='bridge'?[new URL(record.manifest.bridge.mcp_url).hostname]:hosts(code),origins:options.origins||[],privateNetwork:!!options.privateNetwork,signal:options.signal,publicWeb:['website-check','pdf-mcp'].includes(record.id)};
 const network=options.httpRequest||request;
 if(record.type==='bridge')return redact(await bridge(record,tool,args,config,policy,network),config);
 const helpers={httpRequest:async options=>{
  if(policy.signal?.aborted)throw Error('Tempo limite da integração.');
  if(options.url.startsWith('https://jarvis-state.invalid/'))return database(state,config,options);
  if(options.url.startsWith('http://file-bridge:3200/'))return fileBridge(options,policy,network);
  if(options.url.startsWith('http://email-bridge:3100/'))return mailBridge(options,policy);
  return network(options,policy);
 }};
 const input=mapInput(record,tool,args);
 const script=code.replaceAll('{{SUPABASE_URL}}','https://jarvis-state.invalid').replaceAll('{{SUPABASE_SERVICE_KEY}}','unused-local-state');
 if(/\{\{[A-Z_]+\}\}/.test(script))throw Error('Dependência de template não resolvida.');
 const context=vm.createContext({helpers,$input:{first:()=>({json:input})},Buffer,URL,URLSearchParams,TextEncoder,TextDecoder,setTimeout,clearTimeout,
   require:name=>{if(name==='crypto')return crypto;throw Error('Módulo não permitido.');},
 },{codeGeneration:{strings:false,wasm:false}});
 const promise=new vm.Script(`(async function(){${script}\n}).call({helpers})`,{filename:`${record.id}.js`}).runInContext(context,{timeout:2000});
 return redact(await promise,{...config,...state.tokens});
}
async function run(record,tool,args,config,state,options={}){
 const controller=new AbortController(),base=options.httpRequest||request;
 const httpRequest=(input,policy)=>{if(controller.signal.aborted)throw Error('Tempo limite da integração.');return base({...input,signal:controller.signal},policy);};
 let timer;
 try{return await Promise.race([execute(record,tool,args,config,state,{...options,httpRequest,signal:controller.signal}),new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error('Tempo limite da integração.'));},60000);})]);}
 finally{clearTimeout(timer);controller.abort();}
}
module.exports={run,mapInput,hosts,redact};
