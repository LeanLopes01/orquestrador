import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { readVault } from '../services/context-reader.mjs';

async function fixture(t){await mkdir('.local',{recursive:true});const root=await mkdtemp(path.resolve('.local/vault-test-'));t.after(()=>rm(root,{recursive:true,force:true}));return root;}
test('reads notes, preserves provenance and excludes caches and secrets',async t=>{
 const root=await fixture(t);
 await writeFile(path.join(root,'Architecture.md'),'# Architecture\n[[Grid]] ![[Image]]');
 await writeFile(path.join(root,'Grid.md'),'Grid source');
 await writeFile(path.join(root,'.env'),'SECRET=not-for-ui');
 await mkdir(path.join(root,'Library'));await writeFile(path.join(root,'Library','Hidden.md'),'ignored');
 const v=await readVault(root);
 assert.equal(v.notes.length,2);assert.deepEqual(v.edges,[['Architecture.md','Grid.md']]);
 assert.equal(v.notes[0].hash.length,64);assert.equal(v.notes[0].status,'unknown');assert.equal(v.kind,'local');
 assert.ok(!JSON.stringify(v).includes('SECRET'));
});
test('ambiguous wikilinks do not invent connections and scans are bounded',async t=>{
 const root=await fixture(t);await writeFile(path.join(root,'A.md'),'[[Same]]');
 for(const folder of ['one','two']){await mkdir(path.join(root,folder));await writeFile(path.join(root,folder,'Same.md'),'Note');}
 const v=await readVault(root);assert.equal(v.edges.length,0);
 const limited=await readVault(root,{maxNotes:1});assert.equal(limited.notes.length,1);assert.equal(limited.truncated,true);
});
test('maps LightRAG status by exact source path and ignores oversized notes',async t=>{
 const root=await fixture(t);const file=path.join(root,'A.md');await writeFile(file,'Source');
 await writeFile(path.join(root,'Large.md'),'x'.repeat(129000));
 await mkdir(path.join(root,'.brain','lightrag_storage'),{recursive:true});
 await writeFile(path.join(root,'.brain','lightrag_storage','kv_store_doc_status.json'),JSON.stringify({a:{content_summary:`Source Path: ${file}`,status:'processed'}}));
 const v=await readVault(root);assert.equal(v.notes.length,1);assert.equal(v.notes[0].status,'processed');assert.ok(v.warnings.some(w=>w.includes('grande')));
});
test('reads code, data and pdf metadata with categories and optional large truncation',async t=>{
 const root=await fixture(t);
 await mkdir(path.join(root,'Scripts'),{recursive:true});
 await writeFile(path.join(root,'Scripts','Player.cs'),'public class Player {}');
 await writeFile(path.join(root,'data.xml'),'<spell><name>Fireball</name></spell>');
 await writeFile(path.join(root,'manual.pdf'),'%PDF-1.5 fake pdf');
 await writeFile(path.join(root,'Big.txt'),'a'.repeat(150000));
 const v=await readVault(root,{maxNotes:100,maxBytes:128000,truncateLarge:true});
 assert.equal(v.notes.length,4);
 const byExt=Object.fromEntries(v.notes.map(n=>[n.ext,n]));
 assert.equal(byExt['.cs'].category,'codigo');
 assert.equal(byExt['.xml'].category,'dados');
 assert.equal(byExt['.pdf'].category,'documento');
 assert.ok(byExt['.txt'].body.includes('truncado'));
});
