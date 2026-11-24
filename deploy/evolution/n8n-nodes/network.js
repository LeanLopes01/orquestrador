// Resolve and pin every destination before connecting, including redirects.
const dns=require('node:dns').promises;
const net=require('node:net');
const http=require('node:http');
const https=require('node:https');
const zlib=require('node:zlib');
const crypto=require('node:crypto');
function privateAddress(ip){
 if(net.isIPv4(ip)){
  const [a,b]=ip.split('.').map(Number);
  return a===0||a===10||a===127||a===169&&b===254||a===172&&b>=16&&b<=31||a===192&&b===168||a===100&&b>=64&&b<=127||a>=224||a===198&&(b===18||b===19);
 }
 const lower=ip.toLowerCase();
 return lower==='::'||lower==='::1'||lower.startsWith('fc')||lower.startsWith('fd')||/^fe[89ab]/.test(lower)||lower.startsWith('ff')||lower.startsWith('::ffff:');
}
function payload(options,headers){
 if(options.form){headers['content-type']='application/x-www-form-urlencoded';return Buffer.from(new URLSearchParams(options.form).toString());}
 if(options.formData){
  const boundary='jarvis-'+crypto.randomBytes(18).toString('hex');const chunks=[];
  headers['content-type']=`multipart/form-data; boundary=${boundary}`;
  for(const [key,entry] of Object.entries(options.formData)){
   const value=entry?.value??entry;const props=entry?.options||{};
   const safe=s=>String(s).replace(/[\r\n"\\]/g,'_');
   chunks.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${safe(key)}"${props.filename?`; filename="${safe(props.filename)}"`:''}\r\n${props.contentType?`Content-Type: ${safe(props.contentType)}\r\n`:''}\r\n`));
   chunks.push(Buffer.isBuffer(value)?value:Buffer.from(String(value)));chunks.push(Buffer.from('\r\n'));
  }
  chunks.push(Buffer.from(`--${boundary}--\r\n`));return Buffer.concat(chunks);
 }
 if(options.body===undefined)return undefined;
 if(Buffer.isBuffer(options.body))return options.body;
 if(typeof options.body==='string')return Buffer.from(options.body);
 headers['content-type']||='application/json';return Buffer.from(JSON.stringify(options.body));
}
async function request(options,policy={},depth=0){
 const url=new URL(options.url||options.uri);
 if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw Error('Destino não permitido.');
 if(options.qs)for(const [key,value] of Object.entries(options.qs))if(value!==undefined&&value!==null)url.searchParams.set(key,String(value));
 const explicit=(policy.origins||[]).includes(url.origin);
 const staticHost=(policy.hosts||[]).includes(url.hostname);
 if(!explicit&&!staticHost&&!policy.publicWeb)throw Error('Origem fora da política do conector.');
 const addresses=await dns.lookup(url.hostname,{all:true});
 if(!addresses.length||addresses.some(a=>privateAddress(a.address))&&!(explicit&&policy.privateNetwork))throw Error('Rede privada não autorizada.');
 const pinned=addresses[0];
 const headers=Object.fromEntries(Object.entries(options.headers||{}).map(([k,v])=>[k.toLowerCase(),String(v)]));
 delete headers.host;delete headers['content-length'];headers['accept-encoding']='identity';
 const body=payload(options,headers);
 if(body?.length>10*1024*1024)throw Error('Arquivo excede o limite de 10 MB.');
 if(body)headers['content-length']=String(body.length);
 const response=await new Promise((resolve,reject)=>{
  const transport=url.protocol==='https:'?https:http;
  const req=transport.request(url,{method:options.method||'GET',headers,signal:options.signal,lookup:(_host,opts,cb)=>opts.all?cb(null,[pinned]):cb(null,pinned.address,pinned.family),timeout:Math.min(options.timeout||30000,45000)},res=>{
   const chunks=[];let size=0;
   res.on('data',chunk=>{size+=chunk.length;if(size>10*1024*1024){req.destroy(Error('Resposta excede 10 MB.'));return;}chunks.push(chunk);});
   res.on('end',()=>resolve({statusCode:res.statusCode,headers:res.headers,buffer:Buffer.concat(chunks)}));
   res.on('error',reject);
  });
  req.on('timeout',()=>req.destroy(Error('Tempo limite do provedor.')));req.on('error',()=>reject(Error('Falha de rede do provedor.')));
  if(body)req.write(body);req.end();
 });
 if([301,302,303,307,308].includes(response.statusCode)&&response.headers.location){
  if(depth>=3)throw Error('Redirecionamentos excedidos.');
  const target=new URL(response.headers.location,url);
  if(target.origin!==url.origin)throw Error('Redirecionamento entre origens bloqueado.');
  const rewrite=response.statusCode===303;
  return request({...options,url:target.href,qs:undefined,...(rewrite?{method:'GET',body:undefined,form:undefined,formData:undefined}:{})},policy,depth+1);
 }
 if(response.statusCode>=400&&!options.ignoreHttpStatusErrors)throw Error(`Provedor respondeu HTTP ${response.statusCode}.`);
 let buffer=response.buffer;
 if(response.headers['content-encoding']==='gzip')buffer=zlib.gunzipSync(buffer,{maxOutputLength:10*1024*1024});
 if(response.headers['content-encoding']==='deflate')buffer=zlib.inflateSync(buffer,{maxOutputLength:10*1024*1024});
 let value=options.encoding===null||options.encoding==='arraybuffer'?buffer:buffer.toString('utf8');
 if(typeof value==='string'&&options.json!==false){try{value=JSON.parse(value);}catch{/* text is a valid response */}}
 return options.returnFullResponse?{statusCode:response.statusCode,headers:response.headers,body:value}:value;
}
module.exports={request,privateAddress};
