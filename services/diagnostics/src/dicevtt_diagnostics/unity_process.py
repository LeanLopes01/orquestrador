"""Execução controlada da Unity em lote para a auditoria completa.

Cada execução fica num job object próprio do Windows: cancelar ou estourar o tempo encerra
exatamente esse processo e os filhos dele — nunca outra instância da Unity "pelo nome", nem o
editor que a pessoa tem aberto. Prioridade abaixo do normal para não disputar com o uso do PC.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .collectors.base import NO_WINDOW, Cancelled

BELOW_NORMAL = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)


class _Job:
    """Job object com KILL_ON_JOB_CLOSE; terminate() derruba a árvore inteira da execução."""

    def __init__(self) -> None:
        self.handle = None
        if sys.platform != "win32":
            return
        import ctypes
        from ctypes import wintypes

        class Basic(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class Io(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("ReadOperationCount", "WriteOperationCount",
                                                      "OtherOperationCount", "ReadTransferCount",
                                                      "WriteTransferCount", "OtherTransferCount")]

        class Extended(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", Io), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return
        info = Extended()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if kernel32.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.handle, self._k = handle, kernel32

    def assign(self, process: subprocess.Popen) -> bool:
        if self.handle is None:
            return False
        return bool(self._k.AssignProcessToJobObject(self.handle, int(process._handle)))  # type: ignore[attr-defined]

    def terminate(self) -> None:
        if self.handle is not None:
            self._k.TerminateJobObject(self.handle, 1)

    def close(self) -> None:
        if self.handle is not None:
            self._k.CloseHandle(self.handle)
            self.handle = None


@dataclass
class UnityRun:
    code: int | None
    timed_out: bool
    duration_ms: int
    log: Path
    contained: bool  # dentro do job object (cancelamento preciso)


def run_unity(command: list[str], log: Path, timeout: float, cancel: threading.Event, cwd: Path) -> UnityRun:
    """Roda e espera; cancelamento é verificado a cada segundo. Levanta Cancelled se pedido."""
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    job = _Job()
    process = subprocess.Popen(command, cwd=str(cwd), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, creationflags=NO_WINDOW | BELOW_NORMAL)
    contained = job.assign(process)
    try:
        while True:
            try:
                code = process.wait(timeout=1)
                return UnityRun(code, False, int((time.monotonic() - started) * 1000), log, contained)
            except subprocess.TimeoutExpired:
                pass
            if cancel.is_set():
                _stop(job, process)
                raise Cancelled()
            if time.monotonic() - started > timeout:
                _stop(job, process)
                return UnityRun(None, True, int((time.monotonic() - started) * 1000), log, contained)
    finally:
        job.close()  # KILL_ON_JOB_CLOSE: nada da execução sobrevive ao fim desta função


def _stop(job: _Job, process: subprocess.Popen) -> None:
    job.terminate()
    if process.poll() is None:  # sem job object (fora do Windows): ao menos o processo direto
        process.kill()
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass
