import { spawn } from 'node:child_process';
import { createServer } from 'vite';

// Own the test server directly: no orphaned npm/cmd/Vite process tree on Windows.
const existing = await fetch('http://127.0.0.1:1420', {signal:AbortSignal.timeout(1500)})
  .then(async response => response.ok && (await response.text()).includes('J.A.R.V.I.S.'))
  .catch(() => false);
let server;
try {
  if (!existing) { server = await createServer({server:{host:'127.0.0.1'}}); await server.listen(); }
  const child = spawn(process.execPath, ['node_modules/@playwright/test/cli.js','test',...process.argv.slice(2)], {stdio:'inherit'});
  process.exitCode = await new Promise((resolve,reject)=>{child.on('error',reject);child.on('exit',code=>resolve(code ?? 1));});
} finally { await server?.close(); }
