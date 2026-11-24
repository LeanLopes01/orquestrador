"""Hook de início de turno (Claude Code, Codex e Antigravity): injeta fontes do RAG do DiceVTT no início da sessão.

Uso: python rag_hook.py claude|codex|antigravity   (JSON do hook no stdin)

Só age na primeira mensagem de cada sessão e só em pastas ligadas ao DiceVTT; depois disso
o agente consulta o RAG sob demanda pelo servidor MCP (rag_mcp.py). Qualquer falha sai com
código 0 sem bloquear o prompt (no Antigravity sempre devolve JSON válido no stdout).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rag_client  # noqa: E402

DEFAULT_DIRS = (r"C:\ProjetoTablepRPG", str(rag_client.ROOT))
STATE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DiceVTT-RAG" / "agent-hook"
CONTEXT_BUDGET = 8000  # Claude Code guarda em arquivo o que passa de 10 mil caracteres
SNIPPET_CHARS = 900
STATE_TTL_S = 14 * 86400


def _norm(path: str) -> str:
    return os.path.normcase(os.path.abspath(path)).rstrip("\\/")


def watched(cwd: str) -> bool:
    raw = os.environ.get("DICEVTT_RAG_HOOK_DIRS")
    dirs = [d for d in raw.split(";") if d.strip()] if raw else DEFAULT_DIRS
    here = _norm(cwd)
    return any(here == _norm(d) or here.startswith(_norm(d) + os.sep) for d in dirs)


def first_prompt(agent: str, session_id: str) -> bool:
    """Marca a sessão; True só na primeira vez. Sem session_id, trata toda mensagem como primeira."""
    session = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:100]
    if not session:
        return True
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    marker = STATE_DIR / f"{agent}-{session}"
    try:
        marker.open("x").close()
    except FileExistsError:
        return False
    now = time.time()
    for old in STATE_DIR.iterdir():
        try:
            if now - old.stat().st_mtime > STATE_TTL_S:
                old.unlink()
        except OSError:
            pass
    return True


def build_context(prompt: str) -> str:
    footer = ("Para mais detalhes durante a sessão, use a ferramenta MCP `rag_buscar` (servidor dicevtt-rag) "
              "com uma consulta específica (nome de classe/arquivo .cs, sistema ou pergunta). Fontes de código "
              "são lidas do disco na hora; confira o arquivo antes de editar.")
    try:
        result = rag_client.retrieve(prompt, text_limit=SNIPPET_CHARS, timeout=15)
    except rag_client.RagUnavailable as exc:
        return f"[RAG DiceVTT] Sem fontes nesta mensagem: {exc}\n{footer}"
    parts = ["[RAG DiceVTT — fontes recuperadas para a primeira mensagem da sessão]"]
    used = len(parts[0]) + len(footer) + 40
    for source in result["sources"]:
        summary = (source.get("provenance") or {}).get("summary")
        if source.get("kind") == "code_pointer" and summary:
            # O arquivo vem inteiro; no início da sessão basta o resumo (classe + comentário de cabeçalho).
            block = f"{rag_client.describe(source)}\n{summary[:SNIPPET_CHARS]}"
        else:
            block = f"{rag_client.describe(source)}\n{source.get('text', '').strip()}"
            if source.get("text_truncated"):
                block += "\n…(trecho cortado; use rag_buscar ou leia o arquivo)"
        if used + len(block) > CONTEXT_BUDGET:
            parts.append(f"{rag_client.describe(source)} (sem trecho: limite de contexto)")
            continue
        parts.append(block)
        used += len(block) + 2
    if result.get("warnings"):
        parts.append("Avisos do RAG: " + " | ".join(result["warnings"])[:600])
    if not result["sources"]:
        parts.append("Nenhuma fonte encontrada para esta mensagem.")
    parts.append(footer)
    return "\n\n".join(parts)[:CONTEXT_BUDGET + 1500]


def _antigravity_prompt(transcript_path: str | None) -> str:
    if not transcript_path:
        return ""
    path = Path(transcript_path)
    if not path.is_file():
        return ""
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - 65536))
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    lines = raw.splitlines()
    if size > 65536 and lines:
        lines = lines[1:]
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and record.get("type") == "USER_INPUT":
            content = str(record.get("content") or "")
            matches = re.findall(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, re.DOTALL)
            if matches:
                return matches[-1].strip()
            cleaned = re.sub(
                r"<(?:CONTEXT_SUMMARY|ADDITIONAL_METADATA|USER_SETTINGS_CHANGE)>.*?</(?:CONTEXT_SUMMARY|ADDITIONAL_METADATA|USER_SETTINGS_CHANGE)>",
                "",
                content,
                flags=re.DOTALL,
            ).strip()
            return "" if cleaned.startswith("<") else cleaned
    return ""


def main() -> int:
    agent = re.sub(r"[^a-z]", "", (sys.argv[1] if len(sys.argv) > 1 else "agent").lower()) or "agent"
    is_agy = agent == "antigravity"
    wrote = False
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
        workspaces = data.get("workspacePaths") if isinstance(data.get("workspacePaths"), list) else []
        cwd = str(data.get("cwd") or (workspaces[0] if workspaces else "") or os.getcwd())
        session_id = str(data.get("session_id") or data.get("conversationId") or "")
        prompt = str(data.get("prompt") or "").strip()
        if not prompt and is_agy:
            prompt = _antigravity_prompt(data.get("transcriptPath") or data.get("transcript_path"))
        if not prompt or not watched(cwd):
            return 0
        if not first_prompt(agent, session_id):
            return 0
        context = build_context(prompt)
        if is_agy:
            output: dict = {"injectSteps": [{"ephemeralMessage": context}]}
        else:
            output = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": context}}
        sys.stdout.write(json.dumps(output, ensure_ascii=True) + ("\n" if is_agy else ""))
        wrote = True
    except Exception:
        pass  # o hook nunca bloqueia o agente
    finally:
        if is_agy and not wrote:
            sys.stdout.write("{}\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
