"""Referências de assets sem abrir a Unity: cada guid citado num YAML (cena, prefab, asset…)
precisa existir num .meta de Assets, de Packages, do PackageCache ou dos pacotes embutidos da Unity.
Só lê arquivos.

Só se confere o que é verificável por .meta: assets (type 2) e scripts-fonte (fileID 11500000).
Referências a classes dentro de DLLs (type 3 com outro fileID) usam guids internos da Unity, que ela
remapeia sozinha; ficam contadas como não verificáveis, nunca como faltando.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

from .base import CheckResult, Context, Finding

YAML_SUFFIXES = {".prefab", ".unity", ".asset", ".mat", ".controller", ".overridecontroller", ".anim", ".playable",
                 ".spriteatlas", ".mask", ".physicsmaterial2d", ".physicmaterial", ".guiskin", ".fontsettings",
                 ".mixer", ".rendertexture", ".flare", ".brush", ".terrainlayer", ".signal", ".lighting"}
_META_GUID = re.compile(rb"^guid:\s*([0-9a-f]{32})", re.M)
_REF = re.compile(rb"(m_Script:\s*)?\{fileID:\s*(-?\d+),\s*guid:\s*([0-9a-f]{32}),\s*type:\s*(\d+)\}")
SOURCE_SCRIPT = b"11500000"
_BUILTIN = re.compile(rb"^0{16}[0-9a-f]0{15}$")  # unity default resources / builtin extra


def known_guids(roots: list[Path], ctx: Context | None = None) -> tuple[set[bytes], int]:
    guids: set[bytes] = set()
    metas = 0
    for root in roots:
        if not root.is_dir():
            continue
        for current, _dirs, files in os.walk(root):
            if ctx is not None:
                ctx.check_cancel()
            for name in files:
                if not name.endswith(".meta"):
                    continue
                metas += 1
                try:
                    with open(os.path.join(current, name), "rb") as handle:
                        match = _META_GUID.search(handle.read(512))
                except OSError:
                    continue
                if match:
                    guids.add(match.group(1))
    return guids, metas


def scan(project: Path, package_roots: list[Path], ctx: Context | None = None, limit_bytes: int = 64 * 1024 * 1024):
    """Devolve {arquivo: (faltando, scripts_faltando)} e estatísticas da varredura."""
    guids, metas = known_guids([project / "Assets", project / "Packages", *package_roots], ctx)
    broken: dict[str, tuple[Counter[bytes], int]] = {}
    stats = Counter()
    for current, dirs, files in os.walk(project / "Assets"):
        dirs[:] = [d for d in dirs if not d.endswith("~") and not d.startswith(".")]
        if ctx is not None:
            ctx.check_cancel()
        for name in files:
            if Path(name).suffix.lower() not in YAML_SUFFIXES:
                continue
            path = Path(current, name)
            try:
                if path.stat().st_size > limit_bytes:
                    stats["too_large"] += 1
                    continue
                data = path.read_bytes()
            except OSError:
                stats["unreadable"] += 1
                continue
            if not data.startswith(b"%YAML"):
                stats["binary"] += 1  # serialização binária: fora do alcance desta leitura
                continue
            stats["yaml"] += 1
            missing: Counter[bytes] = Counter()
            scripts = 0
            for is_script, file_id, guid, kind in _REF.findall(data):
                if guid in guids or _BUILTIN.match(guid):
                    continue
                if kind != b"2" and file_id != SOURCE_SCRIPT:
                    stats["unverifiable"] += 1  # classe dentro de DLL: guid interno da Unity
                    continue
                missing[guid] += 1
                scripts += 1 if is_script else 0
            if missing:
                broken[path.relative_to(project).as_posix()] = (missing, scripts)
    stats["metas"] = metas
    stats["guids"] = len(guids)
    return broken, stats


def collect_refs(ctx: Context, check: CheckResult, project: Path, package_roots: list[Path]) -> None:
    for root in package_roots:
        if not root.is_dir():
            check.degrade("partial", f"{root} ausente: referências a esses pacotes não puderam ser conferidas.")
    broken, stats = scan(project, package_roots, ctx)
    check.data.update(yaml_files=stats["yaml"], binary_files=stats["binary"], metas=stats["metas"],
                      guids=stats["guids"], unverifiable_refs=stats["unverifiable"], files_with_broken_refs=len(broken))
    evidence = check.add_evidence("file", (project / "Assets").as_posix(),
                                  f"{stats['yaml']} YAML lidos, {stats['guids']} guids conhecidos "
                                  f"({stats['metas']} .meta), {stats['unverifiable']} refs a DLLs não verificáveis, "
                                  f"{stats['binary']} binários fora do alcance")
    ranked = sorted(broken.items(), key=lambda item: (-item[1][1], -sum(item[1][0].values())))
    limit = ctx.config.max_findings_per_check
    for rel, (missing, scripts) in ranked[:limit]:
        scene_or_prefab = rel.endswith((".unity", ".prefab"))
        total = sum(missing.values())
        sample = ", ".join(g.decode() for g, _ in missing.most_common(3))
        if scripts:
            check.findings.append(Finding(
                rule="assets.missing-script", severity="high" if scene_or_prefab else "medium", state="confirmed",
                key=rel, file=rel, occurrences=scripts, evidence=[evidence],
                summary=f"{scripts} componente(s) com script ausente em {rel}",
                recommendation=f"O guid do script não existe em nenhum .meta (ex.: {sample}). Na Unity aparece "
                               "'The referenced script is missing'. Restaure o script ou remova o componente.",
            ))
        if total > scripts:
            check.findings.append(Finding(
                rule="assets.missing-reference", severity="medium", state="confirmed", key=rel, file=rel,
                occurrences=total - scripts, evidence=[evidence],
                summary=f"{total - scripts} referência(s) a assets inexistentes em {rel}",
                recommendation=f"Guids sem .meta correspondente: {sample}. Na Unity aparecem como 'Missing'.",
            ))
    if len(ranked) > limit:
        check.problems.append(f"Mais {len(ranked) - limit} arquivo(s) com referências quebradas não detalhados.")
    check.note = (f"{stats['yaml']} assets YAML conferidos · {len(broken)} com referência quebrada · "
                  f"{stats['binary']} binário(s) fora do alcance")
