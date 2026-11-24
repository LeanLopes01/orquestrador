const dns=require('node:dns').promises;
const {privateAddress}=require('./network');
async function mailBridge(options,policy){
 const body=typeof options.body==='string'?JSON.parse(options.body):options.body;
 const read=new URL(options.url).pathname==='/read-emails';
 if(!read&&new URL(options.url).pathname!=='/send-email')throw Error('Operação de e-mail não permitida.');
 const host=String(body.host||'').trim(),port=Number(body.port||(read?993:587));
 if(!/^[a-z0-9.-]+$/i.test(host)||!body.user||!body.password)throw Error('Servidor e credenciais de e-mail obrigatórios.');
 if(read?port!==993:![465,587].includes(port))throw Error('Use IMAP TLS 993 ou SMTP TLS 465/STARTTLS 587.');
 const origin=`${read?'imaps':port===465?'smtps':'smtp'}://${host}:${port}`;
 if(!policy.origins.includes(origin))throw Error('Cadastre a origem de e-mail na credencial: '+origin);
 const addresses=await dns.lookup(host,{all:true});
 if(!addresses.length||addresses.some(a=>privateAddress(a.address))&&!policy.privateNetwork)throw Error('Servidor de e-mail em rede privada não autorizado.');
 const shared={host:addresses[0].address,port,auth:{user:body.user,pass:body.password},tls:{servername:host,rejectUnauthorized:true},connectionTimeout:15000,socketTimeout:20000};
 if(!read){
  const nodemailer=require('nodemailer');
  const transport=nodemailer.createTransport({...shared,secure:port===465,requireTLS:port===587,logger:false,debug:false,disableFileAccess:true,disableUrlAccess:true});
  policy.signal?.addEventListener('abort',()=>transport.close(),{once:true});
  try{
   const result=await transport.sendMail({from:body.user,to:String(body.to||''),subject:String(body.subject||''),text:String(body.body||''),html:body.html?String(body.html):undefined});
   return {success:true,messageId:result.messageId};
  }catch{throw Error('SMTP recusou o envio. Confira credenciais e resultado antes de repetir.');}
  finally{transport.close();}
 }
 const {ImapFlow}=require('imapflow');
 const client=new ImapFlow({...shared,secure:true,logger:false});
 policy.signal?.addEventListener('abort',()=>client.close(),{once:true});
 client.on('error',()=>{});
 try{
  await client.connect();const lock=await client.getMailboxLock(String(body.folder||'INBOX'),{readOnly:true});
  try{
   const criteria={};
   for(const key of ['since','before'])if(body[key]){const date=new Date(body[key]);if(!Number.isFinite(date.getTime()))throw Error('Data inválida.');criteria[key]=date;}
   if(body.unseen)criteria.seen=false;if(body.from)criteria.from=String(body.from);
   const ids=await client.search(Object.keys(criteria).length?criteria:{all:true},{uid:true});
   const messages=[],limit=Math.max(1,Math.min(50,Number(body.limit)||10));
   for(const uid of ids.slice(-limit)){
    const message=await client.fetchOne(uid,{envelope:true,bodyParts:[{key:'text',start:0,maxLength:8192}]},{uid:true});
    if(!message)continue;
    const envelope=message.envelope;
    messages.push({uid,from:(envelope.from||[]).map(a=>a.address).join(', '),to:(envelope.to||[]).map(a=>a.address).join(', '),subject:envelope.subject||'',date:envelope.date?.toISOString()||'',text:[...(message.bodyParts||new Map()).values()].map(b=>b.toString()).join('\n').slice(0,2000)});
   }
   return {emails:messages,total:ids.length};
  }finally{lock.release();}
 }catch{throw Error('Não foi possível consultar o IMAP. Confira servidor, credenciais e pasta.');}
 finally{await client.logout().catch(()=>client.close());}
}
module.exports={mailBridge};
