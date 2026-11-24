import { useRef, useState } from 'react';
import { ArrowDownToLine, ArrowRight, Check, CircleAlert, Database, FileText, FolderOpen, Globe, Link2, ListFilter, Plus, Search, ShieldCheck, Trash2, Upload, Video } from 'lucide-react';
import { download } from './domain';
import './ingestion.css';
import IngestionRunPanel from './IngestionRunPanel';
import { createManifest, INGESTION_KEY, MAX_SOURCES, prepareSources, previewMarkdown, restoreSources, type IngestionSource, type UrlIssue } from './ingestion';

export default function IngestionPanel() {
  const [initial] = useState(() => { try { return { sources: restoreSources(localStorage.getItem(INGESTION_KEY)), error: '' }; } catch { return { sources: [], error: 'Não foi possível recuperar o lote salvo. O conteúdo anterior não será alterado até você editar a lista.' }; } });
  const [sources, setSources] = useState<IngestionSource[]>(initial.sources);
  const [storageError, setStorageError] = useState(initial.error);
  const [input, setInput] = useState(''), [issues, setIssues] = useState<UrlIssue[]>([]), [feedback, setFeedback] = useState('');
  const [filter, setFilter] = useState<'all' | 'article' | 'video'>('all'), [search, setSearch] = useState(''), [selectedId, setSelectedId] = useState(initial.sources[0]?.id ?? '');
  const fileInput = useRef<HTMLInputElement>(null);
  const selected = sources.find(source => source.id === selectedId);
  const visible = sources.filter(source => (filter === 'all' || source.kind === filter) && source.originalUrl.toLowerCase().includes(search.toLowerCase()));
  const videos = sources.filter(source => source.kind === 'video').length;
  function save(next: IngestionSource[]) {
    setSources(next);
    try { localStorage.setItem(INGESTION_KEY, JSON.stringify(next)); setStorageError(''); return true; }
    catch { setStorageError('Armazenamento indisponível. Este lote está apenas na sessão; exporte-o para preservar as fontes.'); return false; }
  }
  function add() {
    const result = prepareSources(input, sources);
    const persisted = save([...sources, ...result.sources]);
    if (!selectedId && result.sources[0]) setSelectedId(result.sources[0].id);
    setIssues(result.issues);
    setInput(result.issues.map(issue => issue.value).join('\n'));
    setFeedback(`${result.sources.length} fonte(s) adicionada(s). ${result.duplicates ? `${result.duplicates} duplicata(s) ignorada(s). ` : ''}${result.issues.length ? `${result.issues.length} link(s) precisam de correção.` : persisted ? 'Lote salvo neste navegador.' : 'Lote mantido apenas nesta sessão.'}`);
  }
  function remove(source: IngestionSource) {
    const next = sources.filter(item => item.id !== source.id);
    save(next);
    if (selectedId === source.id) setSelectedId(next[0]?.id ?? '');
    setFeedback('Fonte removida do lote.');
  }
  async function importFile(file?: File) {
    if (!file) return;
    if (!/\.txt$/i.test(file.name) || file.size > 512 * 1024) { setFeedback('Escolha um arquivo .txt de até 512 KB, com uma URL por linha.'); return; }
    try { const text = await file.text(); if (text.length > 100000) throw new Error(); setInput(text); setIssues([]); setFeedback('Lista carregada. Revise os links e clique em Adicionar ao lote.'); }
    catch { setFeedback('Não foi possível ler a lista. Use um .txt UTF-8 com até 100.000 caracteres.'); }
  }
  return <div className="ingestion-page">
    <div className="page-heading"><div><span className="eyebrow">BIBLIOTECA · RAG LOCAL</span><h1>Das fontes ao conhecimento<span className="mint-text">.</span></h1><p>Organize documentações e tutoriais para a memória do seu projeto.</p></div><span className="badge mint"><ShieldCheck size={13}/> Preparação local</span></div>

    <section className="ingestion-hero" aria-label="Etapas da ingestão">
      <div className="ingestion-hero-copy"><span className="eyebrow">INGESTÃO DE FONTES</span><h2>Uma entrada.<br/>{' '}Seu acervo em Markdown.</h2><p>Sites viram artigos. Vídeos usam legendas existentes. Cada documento mantém sua origem.</p></div>
      <ol className="ingestion-steps">{[{ icon: Link2, name: 'Preparar fontes', detail: 'Nesta tela', active: true }, { icon: FileText, name: 'Extrair conteúdo', detail: 'Trafilatura · legendas', active: true }, { icon: FolderOpen, name: 'Salvar Markdown', detail: 'documentacao_rag/', active: true }, { icon: Database, name: 'Indexar no RAG', detail: 'Chroma local', active: true }].map((step, index) => <li key={step.name} className={step.active ? 'current' : ''}><span className="ingestion-step-icon"><step.icon size={21}/></span><strong>{step.name}</strong><small>{step.detail}</small>{index < 3 && <ArrowRight className="ingestion-step-arrow" size={14}/>}</li>)}</ol>
    </section>
    <div className="ingestion-status-note"><CircleAlert size={16}/><p><strong>Coleta conectada ao serviço local.</strong> “Coletar online” acessa os sites e o YouTube; “Reprocessar cache offline” usa só os arquivos já baixados. O serviço sobe junto com o helper (iniciar-tudo.cmd).</p></div>
    {storageError && <div role="alert" className="notice error">{storageError}</div>}

    <div className="ingestion-layout"><div className="ingestion-main">
      <section className="panel ingestion-compose"><div className="panel-heading"><h2><Plus size={17}/> Adicionar fontes</h2><span className="muted">Uma URL por linha</span></div>
        <div className="ingestion-compose-body"><label className="field" htmlFor="ingestion-urls">Links de documentação ou YouTube<textarea id="ingestion-urls" rows={5} maxLength={100000} spellCheck={false} placeholder={'https://docs.unity3d.com/Manual/\nhttps://www.youtube.com/watch?v=…'} value={input} onChange={event => setInput(event.target.value)}/></label>
          <div className="ingestion-compose-actions"><input ref={fileInput} type="file" accept=".txt,text/plain" hidden onChange={event => { void importFile(event.target.files?.[0]); event.target.value = ''; }}/><button className="button subtle" onClick={() => fileInput.current?.click()}><Upload size={15}/>Importar lista .txt</button><button className="button primary" disabled={!input.trim()} onClick={add}><Plus size={16}/>Adicionar ao lote</button></div>
          <p className="ingestion-hint">Até {MAX_SOURCES} fontes · links repetidos são identificados automaticamente</p>
          {issues.length > 0 && <ul className="ingestion-issues" aria-label="Links que precisam de correção">{issues.slice(0,20).map((issue, index) => <li key={index}><CircleAlert size={14}/><span><strong>Linha {issue.line}</strong> · {issue.message}<small>{issue.value.slice(0,140)}</small></span></li>)}{issues.length > 20 && <li>Mais {issues.length - 20} erros. Corrija os links restantes no campo acima.</li>}</ul>}
          <p className="ingestion-feedback" role="status">{feedback}</p>
        </div>
      </section>

      <section className="panel ingestion-library"><div className="panel-heading"><h2>Lote de fontes <span className="count">{sources.length}</span></h2><span className="badge gray">Rascunho</span></div>
        <div className="ingestion-filters"><div className="segmented" aria-label="Filtrar fontes">{([{ id: 'all', label: 'Todas' }, { id: 'article', label: 'Artigos' }, { id: 'video', label: 'Vídeos' }] as const).map(item => <button key={item.id} aria-pressed={filter === item.id} className={filter === item.id ? 'active' : ''} onClick={() => setFilter(item.id)}>{item.label}</button>)}</div><label className="search"><Search size={15}/><input aria-label="Buscar URL no lote" placeholder="Buscar URL…" value={search} onChange={event => setSearch(event.target.value)}/></label></div>
        {visible.length ? <div className="ingestion-source-list">{visible.map(source => <div key={source.id} className={`ingestion-source ${selectedId === source.id ? 'selected' : ''}`}><button className="ingestion-source-select" onClick={() => setSelectedId(source.id)} aria-pressed={selectedId === source.id}><span className={`ingestion-source-icon ${source.kind}`}>{source.kind === 'video' ? <Video size={18}/> : <Globe size={18}/>}</span><span className="ingestion-source-label"><strong>{source.kind === 'video' ? `YouTube · ${source.videoId}` : new URL(source.originalUrl).hostname}</strong><small>{source.originalUrl}</small><span className="ingestion-source-meta">{source.kind === 'video' ? 'Vídeo' : 'Artigo'}<i/>Aguardando coleta</span></span></button><button className="ingestion-remove" aria-label={`Remover ${source.originalUrl}`} onClick={() => remove(source)}><Trash2 size={15}/></button></div>)}</div> : <div className="ingestion-empty"><span><ListFilter size={27}/></span><h3>{sources.length ? 'Nenhuma fonte neste filtro' : 'Sua próxima referência começa aqui'}</h3><p>{sources.length ? 'Tente outro termo ou selecione Todas.' : 'Cole links de regras, APIs ou tutoriais. Organize tudo em um lote antes da extração.'}</p></div>}
        <div className="ingestion-library-footer"><span><Check size={13}/> {storageError ? 'Disponível nesta sessão' : 'Armazenado neste navegador'}</span><button className="text-button" disabled={!sources.length} onClick={() => download('fontes-rag.txt', sources.map(source => source.originalUrl).join('\n') + '\n')}><ArrowDownToLine size={14}/> Exportar URLs</button></div>
      </section>
      <IngestionRunPanel sources={sources}/>
    </div><aside className="ingestion-rail">
      <section className="panel ingestion-summary"><span className="eyebrow">RESUMO DO LOTE</span><div className="ingestion-counts"><div><strong>{String(sources.length - videos).padStart(2, '0')}</strong><span><Globe size={13}/>Artigos</span></div><div><strong>{String(videos).padStart(2, '0')}</strong><span><Video size={13}/>Vídeos</span></div></div><div className="ingestion-destination"><FolderOpen size={18}/><div><strong>Destino planejado</strong><code>documentacao_rag/</code></div><span className="badge gray">.md</span></div><dl className="ingestion-rules"><div><dt>Legendas</dt><dd>PT-BR → PT → EN</dd></div><div><dt>Vídeo sem legenda</dt><dd>Pular e registrar aviso</dd></div><div><dt>Arquivos gerados</dt><dd>0 · coleta pendente</dd></div></dl><button className="button primary full" disabled={!sources.length} onClick={() => download('lote-ingestao-rag.json', JSON.stringify(createManifest(sources), null, 2), 'application/json')}><ArrowDownToLine size={16}/>Exportar lote preparado</button><p className="ingestion-hint">Exporta a lista e as preferências em JSON. Não inicia downloads nem cria documentos.</p></section>
      <section className="panel ingestion-preview"><div className="panel-heading"><h2><FileText size={16}/> Modelo de saída</h2><span className="badge gray">Prévia</span></div>{selected ? <><p>Estrutura prevista para a fonte selecionada. Conteúdo ainda não extraído.</p><pre aria-label="Prévia do formato Markdown">{previewMarkdown(selected)}</pre></> : <div className="ingestion-preview-empty"><FileText size={24}/><p>Adicione uma fonte para visualizar o cabeçalho do documento.</p></div>}</section>
      <div className="ingestion-privacy"><ShieldCheck size={17}/><p>Preparação sem envio a modelos.<br/><span>Trafilatura para sites. Legendas existentes para vídeos. Sem transcrição de áudio.</span></p></div>
    </aside></div>
  </div>;
}
