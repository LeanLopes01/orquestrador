"""Chroma embutido: uma coleção por assinatura de embedding, filtros por projeto/kind.

Vetores vão em `embeddings`, o resumo/chunk em `documents` e a proveniência em
`metadatas`. A embedding function automática fica desligada: toda consulta usa
`query_embeddings` calculados pelo mesmo encoder da indexação.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .embeddings import collection_name


def clean_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Omite ausentes (Chroma não aceita None) e converte tipos não suportados."""
    out: dict[str, Any] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            out[key] = value
        else:
            out[key] = str(value)
    return out


class VectorStore:
    def __init__(self, path: Path, signature: dict[str, object]) -> None:
        import chromadb
        from chromadb.config import Settings

        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(path), settings=Settings(anonymized_telemetry=False, allow_reset=False)
        )
        self.name = collection_name(signature)
        self._collection = self._client.get_or_create_collection(
            self.name,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"signature": str(sorted(signature.items()))},
        )
        # Repositório: substituições e limpezas acontecem sob este lock.
        self.lock = threading.RLock()

    @staticmethod
    def where(project_id: str, kind: str, **extra: Any) -> dict[str, Any]:
        clauses = [{"project_id": project_id}, {"kind": kind}, *({k: v} for k, v in extra.items())]
        return {"$and": clauses}

    def upsert(self, ids: list[str], embeddings: list[list[float]], documents: list[str],
               metadatas: list[dict[str, Any]]) -> None:
        if not ids:
            return
        cleaned = [clean_metadata(m) for m in metadatas]
        batch_size = 1000
        with self.lock:
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                batch_emb = embeddings[i:i + batch_size]
                batch_doc = documents[i:i + batch_size]
                batch_meta = cleaned[i:i + batch_size]
                self._collection.upsert(ids=batch_ids, embeddings=batch_emb, documents=batch_doc,
                                        metadatas=batch_meta)

    def update_metadata(self, ids: list[str], metadatas: list[dict[str, Any]]) -> None:
        if ids:
            cleaned = [clean_metadata(m) for m in metadatas]
            batch_size = 1000
            with self.lock:
                for i in range(0, len(ids), batch_size):
                    self._collection.update(ids=ids[i:i + batch_size],
                                            metadatas=cleaned[i:i + batch_size])

    def delete(self, ids: list[str]) -> None:
        if ids:
            batch_size = 1000
            with self.lock:
                for i in range(0, len(ids), batch_size):
                    self._collection.delete(ids=ids[i:i + batch_size])

    def get(self, ids: list[str] | None = None, where: dict[str, Any] | None = None,
            include: list[str] | None = None) -> dict[str, Any]:
        with self.lock:
            if include is None:
                include = ["metadatas", "documents"]
            batch_size = 1000
            if ids is not None and len(ids) > batch_size:
                merged: dict[str, list[Any]] = {k: [] for k in include if k in {"metadatas", "documents", "embeddings"}}
                merged["ids"] = []
                for i in range(0, len(ids), batch_size):
                    batch = self._collection.get(ids=ids[i:i + batch_size], where=where, include=include)
                    for k in batch:
                        if batch[k] is not None:
                            merged.setdefault(k, []).extend(batch[k])
                return merged
            return self._collection.get(ids=ids, where=where, include=include)

    def ids(self, where: dict[str, Any]) -> list[str]:
        return list(self.get(where=where, include=[])["ids"])

    def count(self, project_id: str, kind: str) -> int:
        return len(self.ids(self.where(project_id, kind)))

    def query(self, embedding: list[float], where: dict[str, Any], n_results: int) -> list[dict[str, Any]]:
        if n_results <= 0:
            return []
        with self.lock:
            result = self._collection.query(
                query_embeddings=[embedding], n_results=n_results, where=where,
                include=["distances", "metadatas", "documents"],
            )
        rows = []
        for i, record_id in enumerate(result["ids"][0]):
            rows.append({
                "id": record_id,
                "distance": float(result["distances"][0][i]),
                "metadata": result["metadatas"][0][i] or {},
                "document": result["documents"][0][i] or "",
            })
        return rows
