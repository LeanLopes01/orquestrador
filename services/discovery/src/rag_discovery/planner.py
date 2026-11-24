"""Estratégias de descoberta. Nenhuma acessa a rede: trabalham sobre índices já baixados.

code_api  símbolo usado nos scripts C# ↔ página de API com o mesmo nome, filtrada pelos
          `using` do projeto (UnityEngine.UI.Button não casa com UIElements.Button).
topic     tópico (AirLLM, pergunta recente ou lista fixa) ↔ título/breadcrumb do manual,
          por similaridade de embeddings (o mesmo encoder do RAG).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from rag_ingestion.urls import UrlError, classify

from .catalogs import Entry
from .code_scan import CodeProfile, files_using

MEMBER_WEIGHT = 0.8  # página de membro vale um pouco menos que a do tipo


@dataclass(frozen=True)
class Candidate:
    url: str
    source_id: str
    title: str
    catalog: str
    strategy: str
    score: float
    reason: str


def source_id_of(url: str) -> str | None:
    try:
        return classify(url).source_id
    except UrlError:
        return None


def api_candidates(entries: list[Entry], profile: CodeProfile, known: set[str], *, limit: int,
                   min_files: int = 1, include_members: bool = True) -> list[Candidate]:
    best: dict[str, Candidate] = {}
    for entry in entries:
        if not entry.api or not entry.symbol:
            continue
        if entry.symbol.split(".")[0] in profile.declared:
            continue  # tipo do próprio projeto com o mesmo nome de um tipo da Unity
        member = "." in entry.symbol
        if member and not include_members:
            continue
        files, namespace = files_using(profile, entry.symbol, entry.namespaces)
        weight = MEMBER_WEIGHT if member else 1.0
        if files < min_files:
            continue
        source_id = source_id_of(entry.url)
        if source_id is None or source_id in known:
            continue
        candidate = Candidate(
            url=entry.url, source_id=source_id, title=entry.title, catalog=entry.catalog, strategy="code_api",
            score=round(files * weight, 2),
            reason=f"{entry.symbol} usado em {files} script(s)" + (f" ({namespace})" if namespace else ""),
        )
        if source_id not in best or candidate.score > best[source_id].score:
            best[source_id] = candidate
    ranked = sorted(best.values(), key=lambda c: (-c.score, c.title))
    return ranked[:limit]


def _vectors(embedder, labels: list[str], cache_dir: Path | None):
    import numpy as np

    key = hashlib.sha256(
        (repr(sorted(embedder.signature.items())) + "\n" + "\n".join(labels)).encode("utf-8")
    ).hexdigest()[:20]
    path = cache_dir / f"{key}.npy" if cache_dir else None
    if path is not None and path.exists():
        cached = np.load(path)
        if cached.shape[0] == len(labels):
            return cached
    matrix = np.asarray(embedder.encode(labels), dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.where(norms == 0, 1, norms)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, matrix)
    return matrix


def topic_candidates(entries: list[Entry], topics: list[tuple[str, str]], embedder, known: set[str], *,
                     limit: int, min_score: float, per_topic: int,
                     cache_dir: Path | None = None) -> list[Candidate]:
    """topics: (texto, origem). Cada tópico contribui com até `per_topic` páginas."""
    import numpy as np

    pool = [e for e in entries if e.topic]
    if not pool or not topics or limit <= 0:
        return []
    matrix = _vectors(embedder, [e.label for e in pool], cache_dir)
    queries = _vectors(embedder, [t for t, _ in topics], None)
    scores = queries @ matrix.T
    best: dict[str, Candidate] = {}
    for row, (topic, origin) in enumerate(topics):
        taken = 0
        for col in np.argsort(-scores[row]):
            score = float(scores[row, col])
            if score < min_score or taken >= per_topic:
                break
            entry = pool[int(col)]
            source_id = source_id_of(entry.url)
            if source_id is None or source_id in known:
                continue
            taken += 1
            candidate = Candidate(
                url=entry.url, source_id=source_id, title=entry.label, catalog=entry.catalog, strategy="topic",
                score=round(score, 3), reason=f"tópico “{topic}” ({origin}), similaridade {score:.2f}",
            )
            if source_id not in best or candidate.score > best[source_id].score:
                best[source_id] = candidate
    ranked = sorted(best.values(), key=lambda c: (-c.score, c.title))
    return ranked[:limit]
