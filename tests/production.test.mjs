import {test} from 'node:test';
import assert from 'node:assert/strict';
import {productionServer,isDirectRun} from '../services/server.mjs';
import {request} from 'node:http';
import {fileURLToPath} from 'node:url';

test('isDirectRun handles Tauri Windows verbatim resource paths',()=>{
 const serverUrl=new URL('../services/server.mjs',import.meta.url).href;
 const serverPath=fileURLToPath(serverUrl);
 assert.equal(isDirectRun(serverPath,serverUrl),true);
 if(process.platform==='win32'){
  const verbatim='\\\\?\\'+serverPath.replace(/\\services\\server\.mjs$/,'\\services/server.mjs');
  assert.equal(isDirectRun(verbatim,serverUrl),true);
 }
 assert.equal(isDirectRun(fileURLToPath(import.meta.url),serverUrl),false);
});

test('production serves the built UI without Vite and rejects alien origins',async()=>{
 const server=productionServer();
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base=`http://127.0.0.1:${server.address().port}`;
 const fetch=(url,options={})=>new Promise((resolve,reject)=>{
   const req=request(url,options,res=>{let body='';res.on('data',chunk=>body+=chunk);res.on('end',()=>resolve({status:res.statusCode,headers:{get:key=>res.headers[key]},json:()=>JSON.parse(body),text:()=>body}));});req.on('error',reject);req.end();
 });
 try{
  assert.equal((await fetch(base)).status,403);
  const headers={Host:'127.0.0.1:1420'};
  const home=await fetch(base,{headers});assert.equal(home.status,200);assert.ok(home.headers.get('content-security-policy').includes("frame-ancestors 'none'"));
  assert.ok(!(await home.text()).includes('@vite/client'));
  const catalog=await fetch(base+'/api/catalog',{headers});assert.equal((await catalog.json()).entries.length,75);
  assert.equal((await fetch(base+'/api/catalog',{headers:{...headers,Origin:'https://evil.example'}})).status,403);
  assert.equal((await fetch(base+'/api/system/exit',{method:'POST',headers})).status,403);
  assert.equal((await fetch(base+'/.env',{headers})).status,404);
 }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
