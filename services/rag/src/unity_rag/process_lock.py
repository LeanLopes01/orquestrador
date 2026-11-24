"""Lock de processo liberado pelo sistema operacional (sobrevive a crashes sem travar)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


class LockBusy(Exception):
    pass


class ProcessLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle = None

    def acquire(self) -> ProcessLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+")  # noqa: SIM115 - mantido até release()
        try:
            if sys.platform == "win32":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise LockBusy(str(self.path)) from None
        self.path.with_suffix(".pid").write_text(str(os.getpid()), encoding="ascii")
        self._handle = handle
        return self

    def release(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> ProcessLock:
        return self if self._handle is not None else self.acquire()

    def __exit__(self, *_: object) -> None:
        self.release()
