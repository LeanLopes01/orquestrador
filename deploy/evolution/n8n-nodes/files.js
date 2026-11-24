// File-bridge protocol implemented in-process: encrypted volume, no public port.
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const crypto=require('node:crypto');
const MAX=10*1024*1024;
async function fileBridge(options,policy,request,base=path.join(os.homedir(),'.n8n','jarvis-files')){
 await fs.mkdir(base,{recursive:true,mode:0o700});
 const keyFile=path.join(base,'key');
 try{await fs.writeFile(keyFile,crypto.randomBytes(32),{flag:'wx',mode:0o600});}catch(e){if(e.code!=='EEXIST')throw e;}
 const key=await fs.readFile(keyFile),url=new URL(options.url),method=(options.method||'GET').toUpperCase();
 const encode=value=>{const iv=crypto.randomBytes(12),cipher=crypto.createCipheriv('aes-256-gcm',key,iv);const data=Buffer.concat([cipher.update(JSON.stringify(value)),cipher.final()]);return Buffer.concat([iv,cipher.getAuthTag(),data]);};
 const decode=data=>{const cipher=crypto.createDecipheriv('aes-256-gcm',key,data.subarray(0,12));cipher.setAuthTag(data.subarray(12,28));return JSON.parse(Buffer.concat([cipher.update(data.subarray(28)),cipher.final()]).toString());};
 const body=typeof options.body==='string'?JSON.parse(options.body):options.body||{};
 if(url.pathname==='/health')return {ok:true,storage:'encrypted',max_size:MAX};
 if(url.pathname==='/upload/base64'||url.pathname==='/upload'){
  const part=options.formData?.file;const bytes=part?Buffer.from(part.value||part):Buffer.from(body.content_base64||'','base64');
  if(!bytes.length||bytes.length>MAX)throw Error('Arquivo vazio ou maior que 10 MB.');
  let used=0;
  for(const name of await fs.readdir(base))if(/^file-[a-f0-9]{32}\.enc$/.test(name)){
   const file=path.join(base,name),info=await fs.stat(file);
   if(info.mtimeMs<Date.now()-86400000)await fs.unlink(file);else used+=info.size;
  }
  if(used+bytes.length*1.4>200*1024*1024)throw Error('Cache de arquivos cheio (200 MB). Aguarde a expiração de 24 horas.');
  const id='file-'+crypto.randomBytes(16).toString('hex');
  const meta={id,file_name:body.file_name||part?.options?.filename||'upload',mime_type:body.mime_type||part?.options?.contentType||'application/octet-stream',size_bytes:bytes.length,created_at:new Date().toISOString(),expires_at:new Date(Date.now()+86400000).toISOString()};
  await fs.writeFile(path.join(base,id+'.enc'),encode({meta,content:bytes.toString('base64')}),{flag:'wx',mode:0o600});
  return meta;
 }
 const match=url.pathname.match(/^\/files\/(file-[a-f0-9]{32})(?:\/(meta|forward))?$/);
 if(!match)throw Error('Rota do arquivo não suportada.');
 const id=match[1],file=path.join(base,id+'.enc');
 let stored;try{stored=decode(await fs.readFile(file));}catch{throw Error('Arquivo não encontrado ou inválido.');}
 if(new Date(stored.meta.expires_at)<new Date()){await fs.unlink(file);throw Error('Arquivo expirado.');}
 if(method==='DELETE'){await fs.unlink(file);return {success:true,deleted:id};}
 if(match[2]==='meta')return stored.meta;
 const bytes=Buffer.from(stored.content,'base64');
 if(match[2]==='forward'){
  const result=await request({method:body.method||'POST',url:body.url,headers:body.headers||{},returnFullResponse:true,
   ...(body.raw_body?{body:bytes}:{formData:{...(body.form_fields||{}),[body.file_field||'file']:{value:bytes,options:{filename:body.filename||stored.meta.file_name,contentType:stored.meta.mime_type}}}})},policy);
  return {success:true,file_id:id,file_name:stored.meta.file_name,size_bytes:bytes.length,remote_status:result.statusCode,remote_response:result.body};
 }
 let content=options.encoding===null||options.encoding==='arraybuffer'?bytes:bytes.toString('utf8');
 if(options.json===true&&typeof content==='string')content=JSON.parse(content);
 return options.returnFullResponse?{body:content,statusCode:200,headers:{'content-type':stored.meta.mime_type}}:content;
}
module.exports={fileBridge};
