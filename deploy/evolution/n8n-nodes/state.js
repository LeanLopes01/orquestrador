const crypto=require('node:crypto');
function vault(staticData,configuration){
 const key=crypto.createHash('sha256').update(JSON.stringify(configuration)).digest();
 let state={};
 if(staticData.encrypted){try{
  const data=Buffer.from(staticData.encrypted,'base64');const decipher=crypto.createDecipheriv('aes-256-gcm',key,data.subarray(0,12));decipher.setAuthTag(data.subarray(12,28));state=JSON.parse(Buffer.concat([decipher.update(data.subarray(28)),decipher.final()]).toString());
 }catch{throw Error('Estado protegido pertence a outra configuração. Reautorize ou limpe somente o cache desta conexão.');}}
 return {state,save(){const iv=crypto.randomBytes(12);const cipher=crypto.createCipheriv('aes-256-gcm',key,iv);const body=Buffer.concat([cipher.update(JSON.stringify(state)),cipher.final()]);staticData.encrypted=Buffer.concat([iv,cipher.getAuthTag(),body]).toString('base64');}};
}
function filters(url,row){
 for(const [key,value] of url.searchParams){
  if(['select','order','limit','offset','on_conflict'].includes(key))continue;
  const dot=value.indexOf('.'),op=value.slice(0,dot),expected=value.slice(dot+1),actual=row[key];
  if(op==='eq'&&String(actual)!==expected)return false;
  if(op==='neq'&&String(actual)===expected)return false;
  if(op==='gte'&&String(actual)<expected)return false;
  if(op==='lte'&&String(actual)>expected)return false;
  if(op==='gt'&&String(actual)<=expected)return false;
  if(op==='lt'&&String(actual)>=expected)return false;
  if(!['eq','neq','gte','lte','gt','lt'].includes(op))throw Error('Filtro de armazenamento não suportado.');
 }return true;
}
function database(state,configuration,options){
 const url=new URL(options.url),table=url.pathname.split('/').pop();const method=(options.method||'GET').toUpperCase();
 if(!/^[a-z_]+$/.test(table))throw Error('Tabela inválida.');
 if(table==='template_credentials'){
  state.tokens||={};const values={...configuration,...state.tokens};
  if(method==='GET')return Object.entries(values).filter(([k])=>!url.searchParams.get('cred_key')||url.searchParams.get('cred_key')===`eq.${k}`).map(([cred_key,cred_value])=>({cred_key,cred_value}));
  const body=typeof options.body==='string'?JSON.parse(options.body):options.body;
  if(method==='DELETE'){const key=url.searchParams.get('cred_key')?.slice(3);if(key)delete state.tokens[key];return [];}
  if(['POST','PATCH'].includes(method)&&body?.cred_key){state.tokens[body.cred_key]=body.cred_value;return [body];}
  throw Error('Atualização de credencial inválida.');
 }
 state.tables||={};let rows=state.tables[table]||[];
 const matched=rows.filter(row=>filters(url,row));
 if(method==='GET'){
  const order=url.searchParams.get('order');if(order){const [field,direction]=order.split('.');matched.sort((a,b)=>String(a[field]).localeCompare(String(b[field]))*(direction==='desc'?-1:1));}
  return matched.slice(Number(url.searchParams.get('offset')||0),Number(url.searchParams.get('offset')||0)+Math.min(Number(url.searchParams.get('limit')||1000),1000));
 }
 const body=typeof options.body==='string'?JSON.parse(options.body):options.body;
 if(method==='POST'){
  const input=Array.isArray(body)?body:[body];
  if(rows.length+input.length>5000)throw Error('Limite de 5000 registros deste conector atingido. Exporte e remova dados antes de continuar.');
  const keys=(url.searchParams.get('on_conflict')||'id').split(',');
  const merge=String(options.headers?.Prefer||options.headers?.prefer||'').includes('resolution=merge-duplicates');
  const added=input.map(row=>{
   const previous=merge?rows.find(item=>keys.every(key=>row[key]!==undefined&&item[key]===row[key])):null;
   if(previous){Object.assign(previous,row);return previous;}
   const next={id:crypto.randomUUID(),created_at:new Date().toISOString(),...row};rows.push(next);return next;
  });
  state.tables[table]=rows;return added;
 }
 if(method==='PATCH'){for(const row of matched)Object.assign(row,body);return matched;}
 if(method==='DELETE'){state.tables[table]=rows.filter(row=>!matched.includes(row));return matched;}
 throw Error('Operação de armazenamento inválida.');
}
module.exports={vault,database};
