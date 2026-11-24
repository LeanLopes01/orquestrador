export type SourceKind = 'article' | 'video';
export type IngestionSource = { id: string; originalUrl: string; canonicalUrl: string; kind: SourceKind; videoId?: string; addedAt: string };
export type UrlIssue = { line: number; value: string; message: string };
export const INGESTION_KEY = 'orq.ingestion.v1';
export const MAX_SOURCES = 200;
const youtubeHosts = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com', 'youtu.be', 'www.youtu.be']);

export function classifyUrl(raw: string): Omit<IngestionSource, 'id' | 'addedAt'> {
  const originalUrl = raw.trim();
  if (originalUrl.length > 4096) throw new Error('URL muito longa (máximo de 4.096 caracteres).');
  let url: URL;
  try { url = new URL(originalUrl); } catch { throw new Error('Informe uma URL completa com https:// ou http://.'); }
  if (!['https:', 'http:'].includes(url.protocol)) throw new Error('Somente links HTTP ou HTTPS são aceitos.');
  if (url.username || url.password) throw new Error('Remova usuário e senha da URL.');
  const host = url.hostname.toLowerCase();
  if (!host || host === 'localhost' || host.endsWith('.localhost') || !host.includes('.') || host.startsWith('[') || /^\d+(\.\d+){3}$/.test(host) || host.endsWith('.local')) {
    throw new Error('Use um domínio público de documentação ou YouTube.');
  }
  if (youtubeHosts.has(host)) {
    const parts = url.pathname.split('/').filter(Boolean);
    const videoId = host.endsWith('youtu.be') ? (parts.length === 1 ? parts[0] : '') : url.pathname === '/watch' ? url.searchParams.get('v') : ['shorts', 'embed', 'live'].includes(parts[0]) && parts.length === 2 ? parts[1] : '';
    if (!videoId || !/^[\w-]{11}$/.test(videoId)) throw new Error('Use o link de um vídeo; canais e playlists não são aceitos.');
    return { originalUrl, canonicalUrl: `https://www.youtube.com/watch?v=${videoId}`, kind: 'video', videoId };
  }
  url.hash = '';
  return { originalUrl, canonicalUrl: url.href, kind: 'article' };
}

export function prepareSources(text: string, existing: IngestionSource[]) {
  const sources: IngestionSource[] = [];
  const issues: UrlIssue[] = [];
  const known = new Set(existing.map(source => source.canonicalUrl));
  let duplicates = 0;
  text.split(/\r?\n/).forEach((value, index) => {
    if (!value.trim()) return;
    try {
      const source = classifyUrl(value);
      if (known.has(source.canonicalUrl)) { duplicates++; return; }
      if (existing.length + sources.length >= MAX_SOURCES) throw new Error(`O lote aceita até ${MAX_SOURCES} fontes. Exporte ou remova itens antes de adicionar mais.`);
      known.add(source.canonicalUrl);
      sources.push({ ...source, id: crypto.randomUUID(), addedAt: new Date().toISOString() });
    } catch (error) { issues.push({ line: index + 1, value, message: error instanceof Error ? error.message : 'URL inválida.' }); }
  });
  return { sources, issues, duplicates };
}

export function restoreSources(raw: string | null): IngestionSource[] {
  if (!raw) return [];
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed) || parsed.length > MAX_SOURCES) throw new Error('Lote salvo inválido.');
  const ids = new Set<string>(), urls = new Set<string>();
  return parsed.map(value => {
    if (!value || typeof value.id !== 'string' || typeof value.originalUrl !== 'string' || typeof value.addedAt !== 'string' || !Number.isFinite(Date.parse(value.addedAt)) || ids.has(value.id)) throw new Error('Lote salvo inválido.');
    const source = classifyUrl(value.originalUrl);
    if (urls.has(source.canonicalUrl)) throw new Error('Lote salvo contém duplicatas.');
    ids.add(value.id); urls.add(source.canonicalUrl);
    return { ...source, id: value.id, addedAt: value.addedAt };
  });
}

export function createManifest(sources: IngestionSource[]) {
  return { schema_version: 1, status: 'draft', collection_executed: false, created_at: new Date().toISOString(), output_directory: 'documentacao_rag', languages: ['pt-BR', 'pt', 'en'], sources: sources.map(source => ({ original_url: source.originalUrl, canonical_url: source.canonicalUrl, kind: source.kind, ...(source.videoId ? { video_id: source.videoId } : {}) })) };
}

export function previewMarkdown(source: IngestionSource) {
  return `Fonte: ${source.originalUrl}\nTipo: ${source.kind === 'video' ? 'Vídeo' : 'Artigo'}\nData de Extração: [preenchida após a coleta]\n\n---\n\n# [Título da fonte]\n\n[${source.kind === 'video' ? 'Legenda existente em PT-BR, PT ou EN, organizada em parágrafos com timestamps.' : 'Conteúdo principal convertido em Markdown pelo Trafilatura.'}]\n`;
}
