"""Identidade canônica de caminhos, limites das raízes e leitura estável de arquivos."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

IGNORED_DIRS = {"library", "temp", "obj", "bin", "build", "builds", "logs", "usersettings", ".git", ".vs", ".idea"}


class ReadError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_key(path: str | Path) -> str:
    """Chave de identidade: realpath; caixa normalizada só onde o FS é insensível (Windows)."""
    return os.path.normcase(os.path.realpath(path))


def record_id(prefix: str, project_id: str, path: str | Path, suffix: str = "") -> str:
    digest = hashlib.sha256(f"{project_id}\0{canonical_key(path)}{suffix}".encode()).hexdigest()
    return f"{prefix}:{digest}"


def within(root: Path, path: str | Path) -> bool:
    """O alvo real (symlinks/junctions resolvidos) fica dentro da raiz real?"""
    try:
        real_root = os.path.normcase(os.path.realpath(root))
        real = os.path.normcase(os.path.realpath(path))
        return os.path.commonpath([real_root, real]) == real_root
    except ValueError:  # unidades diferentes no Windows
        return False


def relative_to(root: Path, path: str | Path) -> str:
    try:
        return Path(os.path.realpath(path)).relative_to(Path(os.path.realpath(root))).as_posix()
    except ValueError:
        return Path(path).name


def ignored_part(parts: tuple[str, ...]) -> bool:
    return any(p.lower() in IGNORED_DIRS or p.startswith(".") for p in parts)


def is_temporary(name: str) -> bool:
    lower = name.lower()
    return (lower.startswith((".tmp-", "~", "#", ".#")) or lower.endswith(("~", ".tmp", ".bak", ".swp", ".meta")))


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class StableRead:
    data: bytes
    sha256: str
    size: int
    mtime_ns: int
    read_at: str


def stable_read(path: Path, *, max_bytes: int, attempts: int = 3, pause: float = 0.05) -> StableRead:
    """Lê os bytes com stat antes/depois; repete se tamanho/mtime mudarem durante a leitura."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            before = path.stat()
            if before.st_size > max_bytes:
                raise ReadError("too_large", f"{path.name} excede {max_bytes} bytes.")
            with open(path, "rb") as handle:
                data = handle.read(max_bytes + 1)
            after = path.stat()
            if len(data) > max_bytes:
                raise ReadError("too_large", f"{path.name} excede {max_bytes} bytes.")
            if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and len(data) == after.st_size:
                return StableRead(data, hashlib.sha256(data).hexdigest(), len(data), after.st_mtime_ns, now_iso())
            last_error = ReadError("unstable", f"{path.name} mudou durante a leitura.")
        except FileNotFoundError:
            raise ReadError("missing", f"{path.name} não existe mais.") from None
        except PermissionError as exc:
            last_error = ReadError("locked", f"{path.name} está bloqueado ou sem permissão ({exc.strerror}).")
        except ReadError:
            raise
        except OSError as exc:
            last_error = ReadError("io_error", f"Falha ao ler {path.name}: {exc.strerror or exc}.")
        time.sleep(pause * (attempt + 1))
    assert last_error is not None
    raise last_error


def decode_text(data: bytes, fallback: str | None = None) -> str:
    """UTF-8 (com ou sem BOM); fallback explícito; erro claro sem descartar caracteres."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        if fallback:
            try:
                return data.decode(fallback)
            except UnicodeDecodeError:
                pass
        raise ReadError("encoding", f"Arquivo não está em UTF-8 (byte {exc.start}); ajuste fallback_encoding.") from None
