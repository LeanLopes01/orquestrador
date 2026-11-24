"""Uma rodada: perfil do código → índices → candidatos → ingestão → indexação no RAG.

`plan` para antes da ingestão (nada sai do PC além dos índices oficiais). `run` entrega
as URLs ao serviço de ingestão, espera o lote, registra o resultado por fonte e pede a
indexação dos documentos ao RAG.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from rag_ingestion.config import load_config as load_ingestion_config
from unity_rag.config import apply_offline_environment
from unity_rag.config import load_config as load_rag_config

from .catalogs import Fetcher, http_fetch, load_entries
from .code_scan import CodeProfile, scan_project
from .config import DiscoveryConfig
from .llm import build_prompt, generate_topics
from .planner import Candidate, api_candidates, topic_candidates
from .services import BATCH_DONE, JOB_DONE, LocalService, ServiceError, wait_until
from .state import Store, ingested_source_ids, ingested_titles, recent_questions

Log = Callable[[str], None]
ITEM_STATUS = {"completed": "ingested", "skipped": "skipped"}


@dataclass
class Plan:
    run_id: str
    candidates: list[Candidate]
    topics: list[tuple[str, str]]
    profile: CodeProfile
    warnings: list[str] = field(default_factory=list)


@dataclass
class Deps:
    """Pontos de troca para testes: rede, embeddings e gerador."""

    fetch: Fetcher = http_fetch
    embedder_factory: Callable[[object], object] | None = None
    topic_generator: Callable[..., list[str]] = generate_topics


def _embedder(rag_config, deps: Deps):
    if deps.embedder_factory is not None:
        return deps.embedder_factory(rag_config)
    from unity_rag.embeddings import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder(rag_config.embedding)


def build_plan(config: DiscoveryConfig, store: Store, *, use_llm: bool, refresh: bool = False,
               log: Log = print, deps: Deps | None = None) -> Plan:
    deps = deps or Deps()
    ingestion = load_ingestion_config(config.ingestion_config)
    rag = load_rag_config(config.rag_config)
    apply_offline_environment(rag)
    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    warnings: list[str] = []

    log(f"Lendo scripts em {rag.scripts_root}...")
    profile = scan_project(rag.scripts_root, rag.unity_project_root)
    log(f"  {profile.files} scripts, {len(profile.usings)} namespaces, {len(profile.declared)} tipos próprios")

    log(f"Carregando índices oficiais (cache de {config.catalog_ttl_days:g} dias)...")
    entries, catalog_warnings = load_entries(config, refresh=refresh, fetch=deps.fetch)
    warnings += catalog_warnings
    log(f"  {len(entries)} páginas conhecidas em {len(config.catalogs)} catálogos")

    known = ingested_source_ids(ingestion.state_path) | store.known_ids()
    api = api_candidates(entries, profile, known, limit=config.max_api_per_run,
                         min_files=config.min_files_per_symbol, include_members=config.include_members)
    log(f"  código: {len(api)} páginas de API usadas no projeto e ausentes do RAG")

    topics: list[tuple[str, str]] = [(t, "lista fixa") for t in config.topics]
    questions = recent_questions(rag.index_state_path) if config.use_recent_asks else []
    topics += [(q, "pergunta recente") for q in questions]
    if use_llm and config.llm_enabled and config.max_topic_per_run:
        from unity_rag.airllm_engine import GeneratorUnavailable

        prompt = build_prompt(rag.project_id, profile, ingested_titles(ingestion.state_path), questions,
                              config.llm_topics)
        log(f"AirLLM ({rag.generator.repo_id or 'gerador local'}) sugerindo {config.llm_topics} tópicos "
            f"(até {config.llm_max_new_tokens} tokens, ~1 s/token em CPU)...")
        started = time.monotonic()
        last = [0.0]

        def progress(tokens: int) -> None:
            if time.monotonic() - last[0] > 15:
                last[0] = time.monotonic()
                log(f"  {tokens} tokens gerados")

        try:
            suggested = deps.topic_generator(rag, prompt, config.llm_topics, config.llm_max_new_tokens,
                                             on_token=progress)
            topics += [(t, "AirLLM") for t in suggested]
            log(f"  {len(suggested)} tópicos em {time.monotonic() - started:.0f} s: " + "; ".join(suggested))
        except GeneratorUnavailable as exc:
            warnings.append(f"AirLLM indisponível ({exc.code}): seguindo só com código e tópicos fixos.")

    topical: list[Candidate] = []
    if topics and config.max_topic_per_run:
        log(f"Buscando páginas para {len(topics)} tópicos com embeddings locais...")
        try:
            embedder = _embedder(rag, deps)
            topical = topic_candidates(
                entries, topics, embedder, known | {c.source_id for c in api}, limit=config.max_topic_per_run,
                min_score=config.min_score, per_topic=config.results_per_topic,
                cache_dir=config.cache_root / "embeddings",
            )
        except Exception as exc:  # embeddings ausentes/corrompidos não derrubam a parte de código
            warnings.append(f"busca por tópicos indisponível ({type(exc).__name__}: {exc})")
        log(f"  tópicos: {len(topical)} páginas acima do limiar {config.min_score}")
    return Plan(run_id, api + topical, topics, profile, warnings)


BATCH_CHUNK = 180


def submit(config: DiscoveryConfig, store: Store, plan: Plan, *, index: bool = True, log: Log = print,
           sleep: Callable[[float], None] = time.sleep) -> dict[str, int]:
    """Entrega à ingestão (em fatias <= 180 URLs), espera os lotes e indexa."""
    ingestion_cfg = load_ingestion_config(config.ingestion_config)
    rag_cfg = load_rag_config(config.rag_config)
    ingestion = LocalService("ingestão", ingestion_cfg.host, ingestion_cfg.port, ingestion_cfg.token_path)
    rag = LocalService("RAG", rag_cfg.host, rag_cfg.port, rag_cfg.token_path)
    if not plan.candidates:
        return {}
    totals: dict[str, int] = {}
    chunks = [plan.candidates[i:i + BATCH_CHUNK] for i in range(0, len(plan.candidates), BATCH_CHUNK)]
    for idx, chunk in enumerate(chunks, start=1):
        by_url = {c.url: c for c in chunk}
        req_id = f"discovery-{plan.run_id}" if len(chunks) == 1 else f"discovery-{plan.run_id}-{idx}"
        batch = ingestion.call("POST", "/v1/ingestion/batches", {
            "mode": "online", "urls": "\n".join(by_url), "request_id": req_id,
        })
        batch_id = batch["id"]
        for c in chunk:
            store.set_status(c.source_id, "submitted", batch_id=batch_id)
        suffix = f" (parte {idx}/{len(chunks)})" if len(chunks) > 1 else ""
        log(f"Lote {batch_id}{suffix} enviado à ingestão com {len(by_url)} fontes; aguardando...")
        seen = [-1]

        def progress(state: dict) -> None:
            counts = state.get("counts", {})
            done = sum(counts.get(k, 0) for k in ("completed", "skipped", "failed", "cancelled", "interrupted"))
            if done != seen[0]:
                seen[0] = done
                log(f"  {done}/{state.get('total', len(by_url))} processadas "
                    f"({counts.get('completed', 0)} ok, {counts.get('failed', 0)} falhas)")

        final = wait_until(lambda: ingestion.call("GET", f"/v1/ingestion/batches/{batch_id}?limit=500"), BATCH_DONE,
                           poll=config.poll_seconds, timeout=config.batch_timeout_minutes * 60, on_poll=progress,
                           sleep=sleep)
        for item in final.get("items", []):
            candidate = by_url.get(item.get("raw_url"))
            if candidate is None:
                continue
            status = ITEM_STATUS.get(item.get("status"), "failed")
            result = item.get("result") or {}
            detail = result.get("reason_code") or result.get("message") or item.get("status")
            store.set_status(candidate.source_id, status, detail=detail)
            totals[status] = totals.get(status, 0) + 1
    if index and totals.get("ingested"):
        try:
            job = rag.call("POST", "/v1/rag/index-jobs", {"scope": "documents"})
            log(f"Indexando documentos no RAG (job {job['job_id']})...")
            done = wait_until(lambda: rag.call("GET", f"/v1/rag/index-jobs/{job['job_id']}"), JOB_DONE,
                              poll=config.poll_seconds, timeout=config.batch_timeout_minutes * 60, sleep=sleep)
            log(f"  indexação: {done.get('state')}" + (f" ({done['error']})" if done.get("error") else ""))
        except ServiceError as exc:
            log(f"  indexação não iniciada: {exc}. Use 'Indexar documentos no RAG' na UI depois.")
    return totals
