const fs=require('node:fs');
const path=require('node:path');
const {vault}=require('./state');
const {run}=require('./runner');
class JarvisCatalog {
 constructor(){this.description={
  displayName:'Jarvis · Conector',name:'jarvisCatalog',group:['transform'],version:1,
  description:'Conector do catálogo fixado, com credencial isolada e tráfego limitado.',defaults:{name:'Jarvis · Conector'},inputs:['main'],outputs:['main'],
  credentials:[{name:'jarvisConnection',required:true},{name:'oAuth2Api',required:false},{name:'notionApi',required:false}],
  properties:[
   {displayName:'ID do template',name:'template',type:'string',default:'',required:true},
   {displayName:'Usar OAuth Google existente',name:'googleOAuth',type:'boolean',default:false},
   {displayName:'Usar Notion existente',name:'notionAuth',type:'boolean',default:false},
  ]};}
 async execute(){
  const id=this.getNodeParameter('template',0);
  if(!/^[a-z0-9-]+$/.test(id))throw Error('ID inválido.');
  const record=JSON.parse(fs.readFileSync(path.join(__dirname,'catalog-source',id+'.json'),'utf8'));
  const credentials=await this.getCredentials('jarvisConnection');
  if(!credentials.stateSecret||credentials.stateSecret.length<32)throw Error('Chave do estado não configurada. Execute o instalador de conexões.');
  let config;
  try{config=JSON.parse(credentials.configuration||'{}');}catch{throw Error('Configuração da conta deve ser um objeto JSON válido.');}
  if(!config||typeof config!=='object'||Array.isArray(config))throw Error('Configuração deve ser um objeto JSON.');
  if(this.getNodeParameter('googleOAuth',0,false)){
   const oauth=await this.getCredentials('oAuth2Api');const tokens=oauth.oauthTokenData||{};
   let expiry=Number(tokens.expires_at)||0;if(expiry&&expiry<1e12)expiry*=1000;
   Object.assign(config,{client_id:oauth.clientId,client_secret:oauth.clientSecret,access_token:tokens.access_token,refresh_token:tokens.refresh_token,token_expiry:new Date(expiry||Date.now()-1000).toISOString()});
  }
  if(this.getNodeParameter('notionAuth',0,false)){const notion=await this.getCredentials('notionApi');config.notion_token=notion.apiKey;}
  const protectedState=vault(this.getWorkflowStaticData('node'),{stateSecret:credentials.stateSecret});
  const output=[];
  try{
   for(const item of this.getInputData()){
    const input=item.json.body||item.json;
    if(!input.tool||!input.arguments)throw Error('Envie tool e arguments.');
    const result=await run(record,input.tool,input.arguments,config,protectedState.state,{origins:String(credentials.origins||'').split(',').map(s=>s.trim()).filter(Boolean),privateNetwork:credentials.privateNetwork});
    output.push(...result);
   }
  }finally{protectedState.save();}
  return [output];
 }
}
module.exports={JarvisCatalog};
