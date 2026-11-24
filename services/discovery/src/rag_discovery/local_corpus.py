"""Importação de corpus local (SRD 5e em XML + notas Markdown do vault) para o RAG.

Converte arquivos locais estruturados (.xml do SRD 5e e .md autorais da Janela de Contexto)
em documentos Markdown padronizados com cabeçalho de proveniência em `documentacao_rag/`
e registra cada um no SQLite da ingestão para rastreabilidade completa na UI.
"""

from __future__ import annotations

import hashlib
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rag_ingestion import FORMAT_SCHEMA, __version__
from rag_ingestion.acquisition import now_iso
from rag_ingestion.config import load_config as load_ingestion_config
from rag_ingestion.formatter import body_hash
from rag_ingestion.repository import Repository
from rag_ingestion.storage import sha256_file, write_document_atomic
from unity_rag.config import load_config as load_rag_config

from .config import DiscoveryConfig
from .services import JOB_DONE, LocalService, ServiceError, wait_until

Log = Callable[[str], None]
DEFAULT_VAULT = Path(r"C:\J.A.R.V.I.S\JanelaContextoPessoal")

CATEGORY_LABELS = {
    "antecedentes": "Antecedente (Background) D&D 5e SRD",
    "classes": "Classe de Personagem D&D 5e SRD",
    "companheiros": "Companheiro Animal / Criatura D&D 5e SRD",
    "criaturas": "Criatura D&D 5e SRD",
    "dados": "Tabela / Dados de Sistema D&D 5e SRD",
    "itens": "Item / Equipamento D&D 5e SRD",
    "linguas": "Idioma (Language) D&D 5e SRD",
    "magias": "Magia (Spell) D&D 5e SRD",
    "monstros": "Monstro (Monster) D&D 5e SRD",
    "racas": "Raça (Race) D&D 5e SRD",
    "regras": "Regra do Sistema D&D 5e SRD",
    "talentos": "Talento (Feat) D&D 5e SRD",
    "tokens": "Token de Tabuleiro D&D 5e SRD",
}

TAG_TRANSLATIONS = {
    "name": "Nome",
    "summary": "Resumo",
    "description": "Descrição",
    "meta": "Classificação",
    "prerequisite": "Pré-requisito",
    "level": "Nível",
    "school": "Escola de Magia",
    "casting-time": "Tempo de Conjuração",
    "range": "Alcance",
    "components": "Componentes",
    "duration": "Duração",
    "classes": "Classes",
    "category": "Categoria",
    "subcategory": "Subcategoria",
    "weight": "Peso",
    "cost": "Custo",
    "armor-class": "Classe de Armadura (CA)",
    "armor-class-formula": "Fórmula de CA",
    "hit-points": "Pontos de Vida (PV)",
    "speed": "Deslocamento",
    "size": "Tamanho",
    "type": "Tipo",
    "alignment": "Tendência",
    "challenge": "Nível de Desafio (ND)",
    "senses": "Sentidos",
    "languages": "Idiomas",
    "saving-throws": "Testes de Resistência",
    "skills": "Perícias",
    "damage-resistances": "Resistências a Dano",
    "damage-immunities": "Imunidades a Dano",
    "condition-immunities": "Imunidades a Condição",
}


@dataclass(frozen=True)
class LocalDocSpec:
    canonical_url: str
    source_id: str
    title: str
    body: str
    language: str = "pt-BR"


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[ \t]+", " ", value).strip()


def _render_element(elem: ET.Element, depth: int = 0) -> list[str]:
    lines: list[str] = []
    tag = elem.tag.split("}")[-1]
    label = TAG_TRANSLATIONS.get(tag.lower(), tag.replace("-", " ").replace("_", " ").title())
    attribs = {k: v for k, v in elem.attrib.items() if k not in {"id"}}
    attr_str = " · ".join(f"{k}: {v}" for k, v in attribs.items())

    children = list(elem)
    text = _clean_text(elem.text)

    if not children:
        if text:
            if tag.lower() in {"item", "p", "paragraph", "line"}:
                lines.append(f"- {text}" if len(text) < 180 else text)
            elif attr_str:
                lines.append(f"- **{label} ({attr_str}):** {text}")
            else:
                lines.append(f"- **{label}:** {text}")
        elif attr_str:
            lines.append(f"- **{label}:** {attr_str}")
        return lines

    # Element with children
    leaf_children = all(len(list(c)) == 0 for c in children)
    if leaf_children and len(children) <= 12 and all(len(_clean_text(c.text)) < 120 for c in children):
        if depth == 1:
            lines.append(f"\n## {label}" + (f" ({attr_str})" if attr_str else ""))
        elif depth >= 2:
            lines.append(f"\n### {label}" + (f" ({attr_str})" if attr_str else ""))
        if text:
            lines.append(text)
        for child in children:
            lines.extend(_render_element(child, depth + 1))
        return lines

    if depth == 1:
        lines.append(f"\n## {label}" + (f" ({attr_str})" if attr_str else ""))
    elif depth == 2:
        lines.append(f"\n### {label}" + (f" ({attr_str})" if attr_str else ""))
    elif depth >= 3 and (attr_str or label.lower() not in {"content", "items", "list"}):
        lines.append(f"\n**{label}**" + (f" ({attr_str})" if attr_str else ""))

    if text:
        lines.append(text)
    for child in children:
        lines.extend(_render_element(child, depth + 1))
    return lines


def xml_to_spec(path: Path, srd_root: Path) -> LocalDocSpec | None:
    try:
        raw = path.read_text(encoding="utf-8-sig", errors="replace").lstrip()
        root = ET.fromstring(raw)
    except (OSError, ET.ParseError):
        return None

    rel = path.relative_to(srd_root).as_posix()
    parts = rel.split("/")
    category = parts[0] if len(parts) > 1 else "geral"
    cat_label = CATEGORY_LABELS.get(category, f"D&D 5e SRD ({category})")

    name_el = root.find("name")
    if name_el is None:
        name_el = root.find("Name")
    if name_el is None:
        name_el = root.find("titulo")
    entity_name = _clean_text(name_el.text if name_el is not None else "") or path.stem
    entity_id = root.attrib.get("id") or path.stem
    source_book = root.attrib.get("source") or "SRD 5e"

    title = f"{entity_name} — {cat_label}"
    header_lines = [
        f"**Entidade:** {entity_name} (`{entity_id}`)",
        f"**Categoria:** {cat_label}",
        f"** Caminho SRD:** `{rel}`",
        f"**Fonte Base:** {source_book}",
        "",
    ]
    body_lines: list[str] = []
    for child in list(root):
        if child.tag.lower() in {"name", "titulo"} and _clean_text(child.text) == entity_name:
            continue
        body_lines.extend(_render_element(child, depth=1))

    body = "\n".join(header_lines + body_lines).strip()
    if len(body) < 120:
        body += f"\n\nReferência oficial do SRD 5e utilizada no sistema de regras e fichas do DiceVTT ({cat_label})."

    canonical_url = f"https://srd.dicevtt.local/5e/{rel}"
    source_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return LocalDocSpec(canonical_url=canonical_url, source_id=source_id, title=title, body=body)


def markdown_to_spec(path: Path, vault_root: Path) -> LocalDocSpec | None:
    try:
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    except OSError:
        return None
    if len(raw) < 60:
        return None
    rel = path.relative_to(vault_root).as_posix()
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", raw, flags=re.DOTALL).strip()
    heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = heading.group(1).strip() if heading else f"{path.stem} ({rel.split('/')[0]})"
    if heading:
        body = body[heading.end():].strip()
    if len(body) < 120:
        body += f"\n\nNota local do vault ({rel}) integrada à base de conhecimento do DiceVTT."
    canonical_url = f"https://vault.dicevtt.local/{rel.replace(' ', '%20')}"
    source_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
    return LocalDocSpec(canonical_url=canonical_url, source_id=source_id, title=title, body=body)


def collect_local_specs(vault_root: Path = DEFAULT_VAULT) -> list[LocalDocSpec]:
    specs: list[LocalDocSpec] = []
    if not vault_root.is_dir():
        return specs

    srd_root = vault_root / "Projeto VTT RPG" / "DadosVariaveisSistema" / "sistemas" / "quinta-edicao-srd"
    if srd_root.is_dir():
        for xml_path in sorted(srd_root.rglob("*.xml")):
            spec = xml_to_spec(xml_path, srd_root)
            if spec is not None:
                specs.append(spec)

    # Notas autorais relevantes (raiz, informacoes, Projeto VTT RPG, RPG)
    ignored_md = {"license.md", "changelog.md", "contributing.md", "code_of_conduct.md", "issue_template.md"}
    for md_path in sorted(vault_root.rglob("*.md")):
        rel_parts = [p.lower() for p in md_path.relative_to(vault_root).parts]
        if any(p.startswith(".") or p in {"library", "packagecache", "node_modules", "interface", "lightrag_storage",
                                          "vision-ui-dashboard-react-main"} for p in rel_parts):
            continue
        if md_path.name.lower() in ignored_md:
            continue
        spec = markdown_to_spec(md_path, vault_root)
        if spec is not None:
            specs.append(spec)

    return specs


def import_local_corpus(
    config: DiscoveryConfig,
    *,
    vault_root: Path = DEFAULT_VAULT,
    index: bool = True,
    log: Log = print,
) -> dict[str, int]:
    ingestion_cfg = load_ingestion_config(config.ingestion_config)
    rag_cfg = load_rag_config(config.rag_config)
    repo = Repository(ingestion_cfg.state_path)
    repo._db.execute("PRAGMA synchronous=NORMAL")
    output_root = ingestion_cfg.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    log(f"Varrendo corpus local em {vault_root}...")
    specs = collect_local_specs(vault_root)
    log(f"  {len(specs)} documentos locais encontrados (SRD 5e XML + Notas Markdown).")

    options_hash = hashlib.sha256(f"{FORMAT_SCHEMA}:{__version__}:local-v1".encode()).hexdigest()
    added = skipped = 0
    stamp = now_iso()

    try:
        for spec in specs:
            name = f"artigo-{spec.source_id}.md"
            target = output_root / name
            b_hash = body_hash(spec.body)
            existing = repo.document(spec.source_id)
            if (
                existing
                and existing.get("body_sha256") == b_hash
                and existing.get("options_hash") == options_hash
                and target.exists()
            ):
                skipped += 1
                continue

            markdown = (
                f"Fonte: {spec.canonical_url}\n"
                f"Tipo: Artigo\n"
                f"Data de Extração: {stamp}\n"
                f"Source ID: {spec.source_id}\n"
                f"URL Canônica: {spec.canonical_url}\n"
                f"Aquisição Original: {stamp}\n"
                f"Idioma: {spec.language}\n"
                f"\n---\n\n"
                f"# {spec.title}\n\n"
                f"{spec.body.strip()}\n"
            )
            expected = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
            repo.begin_write(spec.source_id, str(target), expected, None, None)
            stored = write_document_atomic(markdown, name, output_root)
            repo.finish_write(spec.source_id, {
                "source_id": spec.source_id,
                "path": stored.path,
                "sha256": stored.sha256,
                "kind": "article",
                "original_url": spec.canonical_url,
                "canonical_url": spec.canonical_url,
                "final_url": spec.canonical_url,
                "extracted_at": stamp,
                "acquired_at": stamp,
                "cache_revision": b_hash[:16],
                "options_hash": options_hash,
                "language": spec.language,
                "body_sha256": b_hash,
            })
            added += 1
    finally:
        repo.close()

    log(f"  Importação concluída: {added} publicados/atualizados, {skipped} inalterados.")

    if index and added > 0:
        rag = LocalService("RAG", rag_cfg.host, rag_cfg.port, rag_cfg.token_path)
        try:
            job = rag.call("POST", "/v1/rag/index-jobs", {"scope": "documents"})
            log(f"Indexando documentos no RAG (job {job['job_id']})...")
            done = wait_until(lambda: rag.call("GET", f"/v1/rag/index-jobs/{job['job_id']}"), JOB_DONE,
                              poll=config.poll_seconds, timeout=config.batch_timeout_minutes * 60)
            log(f"  indexação: {done.get('state')}")
        except ServiceError as exc:
            log(f"  serviço RAG offline ou ocupado ({exc}); rode 'unity_rag index-docs' ou indexe pela UI.")

    return {"added": added, "skipped": skipped, "total": len(specs)}
