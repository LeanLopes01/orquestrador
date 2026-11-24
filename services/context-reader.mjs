import { open, readdir, readFile, stat, realpath } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { inflateRawSync } from 'node:zlib';

const ignored = new Set([
  'library', 'packagecache', 'projectsettings', 'temp', 'logs', 'obj',
  'build', 'builds', 'dist', 'node_modules', 'interface', 'lightrag_storage',
  'burstdebuginformation', 'streamingassets', '__pycache__', 'textmesh pro',
  'vision-ui-dashboard-react-main',
]);

const ignoredFiles = new Set([
  'license.md', 'license.txt', 'changelog.md', 'contributing.md',
  'code_of_conduct.md', 'issue_template.md', 'pull_request_template.md', 'security.md',
]);

const EXTENSION_CATEGORY = new Map([
  ['.md', 'nota'], ['.txt', 'nota'],
  ['.py', 'codigo'], ['.cs', 'codigo'], ['.ino', 'codigo'],
  ['.js', 'codigo'], ['.ts', 'codigo'], ['.php', 'codigo'], ['.html', 'codigo'], ['.sql', 'codigo'],
  ['.xml', 'dados'], ['.json', 'dados'], ['.csv', 'dados'], ['.yaml', 'dados'], ['.yml', 'dados'], ['.dnd5e', 'dados'],
  ['.docx', 'documento'], ['.pdf', 'documento'],
]);

const MAX_BYTES = 128_000;

function extractDocxText(buf) {
  try {
    let offset = 0;
    while (offset + 30 <= buf.length) {
      if (buf.readUInt32LE(offset) !== 0x04034b50) break;
      const method = buf.readUInt16LE(offset + 8);
      const compSize = buf.readUInt32LE(offset + 18);
      const nameLen = buf.readUInt16LE(offset + 26);
      const extraLen = buf.readUInt16LE(offset + 28);
      const name = buf.subarray(offset + 30, offset + 30 + nameLen).toString('utf8');
      const dataStart = offset + 30 + nameLen + extraLen;
      if (compSize === 0 || dataStart + compSize > buf.length) break;
      if (name === 'word/document.xml') {
        const raw = buf.subarray(dataStart, dataStart + compSize);
        const xml = (method === 8 ? inflateRawSync(raw) : raw).toString('utf8');
        return xml
          .replace(/<\/w:p>/g, '\n')
          .replace(/<w:tab\/>/g, '\t')
          .replace(/<[^>]+>/g, '')
          .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'")
          .trim();
      }
      offset = dataStart + compSize;
    }
  } catch {
    // Fallback below if ZIP uses data descriptors
  }
  return '';
}

async function readPartialBuffer(filePath, maxBytes) {
  const handle = await open(filePath, 'r');
  try {
    const buf = Buffer.allocUnsafe(maxBytes);
    const { bytesRead } = await handle.read(buf, 0, maxBytes, 0);
    return buf.subarray(0, bytesRead);
  } finally {
    await handle.close();
  }
}

export async function readVault(
  root,
  {
    maxNotes = 250,
    maxEntries = 12000,
    maxBytes = MAX_BYTES,
    maxBodyChars = 0,
    truncateLarge = false,
  } = {},
) {
  const base = await realpath(root);
  const notes = [], warnings = [], files = [];
  let visited = 0, truncated = false;
  async function walk(dir) {
    let entries;
    try { entries = await readdir(dir, { withFileTypes: true }); }
    catch { warnings.push('Uma pasta não pôde ser lida.'); return; }
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (++visited > maxEntries || files.length >= maxNotes) { truncated = true; return; }
      if (entry.isSymbolicLink() || entry.name.startsWith('.')) continue;
      const lower = entry.name.toLowerCase();
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!ignored.has(lower)) await walk(file);
      } else if (entry.isFile() && !ignoredFiles.has(lower)) {
        const ext = path.extname(lower);
        if (EXTENSION_CATEGORY.has(ext)) files.push(file);
      }
    }
  }
  await walk(base);
  const statuses = new Map();
  const statusFile = path.join(base, '.brain', 'lightrag_storage', 'kv_store_doc_status.json');
  try {
    const resolved = await realpath(statusFile);
    const relative = path.relative(base, resolved);
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('outside root');
    if ((await stat(resolved)).size > 32_000_000) throw new Error('large index');
    const data = JSON.parse(await readFile(resolved, 'utf8'));
    for (const value of Object.values(data)) {
      const match = /^Source Path:\s*(.+)$/m.exec(value?.content_summary || '');
      if (match) statuses.set(path.resolve(match[1].trim()).toLowerCase(), value.status);
    }
  } catch { warnings.push('Status LightRAG indisponível; notas não serão marcadas como indexadas.'); }
  for (const file of files) {
    try {
      const resolved = await realpath(file);
      const relative = path.relative(base, resolved);
      if (relative.startsWith('..') || path.isAbsolute(relative)) continue;
      const info = await stat(resolved);
      const ext = path.extname(file).toLowerCase();
      const category = EXTENSION_CATEGORY.get(ext) || 'nota';
      const relId = path.relative(base, file).replaceAll('\\', '/');
      let body = '';
      let hash = '';

      if (ext === '.pdf') {
        const head = await readPartialBuffer(resolved, Math.min(info.size, 16_384));
        hash = createHash('sha256').update(head).update(String(info.size)).digest('hex');
        body = `[Documento PDF · ${(info.size / 1_048_576).toFixed(2)} MB]\nCaminho: ${relId}\nTamanho: ${info.size.toLocaleString('pt-BR')} bytes\nModificado: ${info.mtime.toISOString()}`;
      } else if (ext === '.docx') {
        if (info.size > maxBytes && !truncateLarge) {
          warnings.push(`Arquivo grande ignorado: ${path.basename(file)}`);
          continue;
        }
        const buf = await readFile(resolved);
        hash = createHash('sha256').update(buf).digest('hex');
        const extracted = extractDocxText(buf);
        body = extracted || `[Documento Word (.docx) · ${(info.size / 1024).toFixed(1)} KB]\nCaminho: ${relId}`;
      } else if (info.size > maxBytes) {
        if (!truncateLarge) {
          warnings.push(`Arquivo grande ignorado: ${path.basename(file)}`);
          continue;
        }
        const head = await readPartialBuffer(resolved, Math.min(info.size, 32_768));
        hash = createHash('sha256').update(head).update(String(info.size)).digest('hex');
        body = `${head.toString('utf8')}\n\n… [Arquivo de ${(info.size / 1024).toFixed(1)} KB truncado na prévia]`;
      } else {
        body = await readFile(resolved, 'utf8');
        hash = createHash('sha256').update(body).digest('hex');
      }

      if (maxBodyChars > 0 && body.length > maxBodyChars) {
        body = `${body.slice(0, maxBodyChars)}\n\n… [Trecho limitado a ${maxBodyChars.toLocaleString('pt-BR')} caracteres]`;
      }

      const links = ext === '.md'
        ? [...body.matchAll(/(?<!!)\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]/g)].map(m => m[1])
        : [];
      const parts = path.relative(base, file).split(path.sep);
      notes.push({
        id: relId,
        title: ext === '.md' ? path.basename(file, '.md') : path.basename(file),
        body,
        hash,
        modified: info.mtime.toISOString(),
        status: statuses.get(resolved.toLowerCase()) || 'unknown',
        links,
        group: parts.length > 1 ? parts[0] : 'Principal',
        ext,
        category,
        size: info.size,
      });
    } catch { warnings.push(`Nota indisponível: ${path.basename(file)}`); }
  }
  const edges = [];
  for (const note of notes) for (const link of note.links) {
    const normalized = link.toLowerCase().replace(/\.md$/, '');
    const exact = notes.filter(n => n.id.replace(/\.md$/i, '').toLowerCase() === normalized);
    const candidates = exact.length ? exact : notes.filter(n => n.title.toLowerCase() === normalized);
    if (candidates.length === 1 && candidates[0].id !== note.id) edges.push([note.id, candidates[0].id]);
  }
  return { root: base, readAt: new Date().toISOString(), notes, edges, truncated, warnings, kind: 'local' };
}
