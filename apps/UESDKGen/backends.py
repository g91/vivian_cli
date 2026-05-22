"""backends.py — Windows process API + memory-read back-ends for UESDKGen.

Three back-ends, all implementing MemoryBackend:
  NativeBackend     — ReadProcessMemory  (local process, admin required)
  VmmBackend        — dma_memory.DMADevice (memprocfs / PCILeech)
  SocketDMABackend  — HTTP JSON API  (MemEdit server.py — pip install fastapi uvicorn)
"""
from __future__ import annotations

import abc
import ctypes
import ctypes.wintypes as _wt
import json
import struct
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

# ── dma_memory tool path bootstrap (same as MemEdit) ─────────────────────────
_TOOL_DIR = str(Path(__file__).resolve().parent.parent.parent
                / "tools" / "DMAMemoryTool")
if _TOOL_DIR not in sys.path:
    sys.path.insert(0, _TOOL_DIR)

# ─────────────────────────────────────────────────────────────────────────────
# Windows API bootstrap
# ─────────────────────────────────────────────────────────────────────────────
_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    PROCESS_VM_READ           = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    TH32CS_SNAPPROCESS        = 0x00000002

    class _PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize",              _wt.DWORD),
            ("cntUsage",            _wt.DWORD),
            ("th32ProcessID",       _wt.DWORD),
            ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID",        _wt.DWORD),
            ("cntThreads",          _wt.DWORD),
            ("th32ParentProcessID", _wt.DWORD),
            ("pcPriClassBase",      ctypes.c_long),
            ("dwFlags",             _wt.DWORD),
            ("szExeFile",           ctypes.c_char * 260),
        ]
else:
    _k32 = None  # type: ignore[assignment]


def list_procs() -> List[Tuple[int, str]]:
    """Return [(pid, exe_name), ...] for all running processes (Windows only)."""
    if not _IS_WIN or _k32 is None:
        return []
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == ctypes.c_void_p(-1).value:
        return []
    entry = _PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(entry)
    results: List[Tuple[int, str]] = []
    if _k32.Process32First(snap, ctypes.byref(entry)):
        while True:
            results.append((entry.th32ProcessID,
                            entry.szExeFile.decode("utf-8", errors="replace")))
            if not _k32.Process32Next(snap, ctypes.byref(entry)):
                break
    _k32.CloseHandle(snap)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Abstract base
# ─────────────────────────────────────────────────────────────────────────────

class MemoryBackend(abc.ABC):
    @abc.abstractmethod
    def read(self, address: int, size: int) -> Optional[bytes]: ...

    @abc.abstractmethod
    def close(self) -> None: ...

    @property
    @abc.abstractmethod
    def description(self) -> str: ...

    def ru32(self, a: int) -> Optional[int]:
        d = self.read(a, 4)
        return struct.unpack_from("<I", d)[0] if d and len(d) >= 4 else None

    def ru64(self, a: int) -> Optional[int]:
        d = self.read(a, 8)
        return struct.unpack_from("<Q", d)[0] if d and len(d) >= 8 else None

    def rptr(self, a: int, is64: bool) -> Optional[int]:
        return self.ru64(a) if is64 else self.ru32(a)

    def get_processes(self) -> List[Tuple[int, str]]:
        """Return [(pid, exe_name), ...] for all processes visible through this backend.
        Subclasses that can enumerate remote processes should override this."""
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Native back-end  (ReadProcessMemory)
# ─────────────────────────────────────────────────────────────────────────────

class NativeBackend(MemoryBackend):
    def __init__(self, pid: int) -> None:
        if not _IS_WIN or _k32 is None:
            raise RuntimeError("NativeBackend requires Windows.")
        h = _k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not h:
            raise RuntimeError(
                f"OpenProcess({pid}) failed — error {ctypes.get_last_error()}.\n"
                "Run as Administrator.")
        self._h   = h
        self._pid = pid

    @property
    def description(self) -> str:
        return f"Native  PID {self._pid}"

    def read(self, address: int, size: int) -> Optional[bytes]:
        buf  = (ctypes.c_byte * size)()
        read = ctypes.c_size_t(0)
        ok   = _k32.ReadProcessMemory(
            self._h, ctypes.c_void_p(address), buf, size, ctypes.byref(read))
        return bytes(buf[:read.value]) if ok else None

    def close(self) -> None:
        if self._h:
            _k32.CloseHandle(self._h)
            self._h = None

    def get_processes(self) -> List[Tuple[int, str]]:
        return list_procs()


# ─────────────────────────────────────────────────────────────────────────────
# DMA back-end — dma_memory.DMADevice  (memprocfs / PCILeech)
# ─────────────────────────────────────────────────────────────────────────────

class VmmBackend(MemoryBackend):
    """DMA via dma_memory.DMADevice (memprocfs / PCILeech).

    Install:  pip install memprocfs
    Also download MemProcFS native binaries:
      https://github.com/ufrisk/MemProcFS/releases
    """

    def __init__(self, device: str, process_name: str) -> None:
        try:
            from dma_memory import DMADevice  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "memprocfs is not installed.\n"
                "  pip install memprocfs\n"
                "Also download MemProcFS native binaries:\n"
                "  https://github.com/ufrisk/MemProcFS/releases") from exc

        dma = DMADevice(device)
        dma.connect()
        self._dma    = dma
        self._proc   = dma.get_process(process_name)
        self._name   = process_name
        self._device = device

    @property
    def description(self) -> str:
        return f"DMA/{self._device}  {self._name}  PID {self._proc.pid}"

    def read(self, address: int, size: int) -> Optional[bytes]:
        try:
            data = self._proc.read(address, size)
            return data if data else None
        except Exception:
            return None

    def close(self) -> None:
        try:
            self._dma.disconnect()
        except Exception:
            pass

    def get_processes(self) -> List[Tuple[int, str]]:
        """Enumerate processes via memprocfs DMA device."""
        try:
            return [(p.pid, p.name) for p in self._dma.enumerate_processes()]
        except Exception:
            return []


# ─────────────────────────────────────────────────────────────────────────────
# DMA back-end — TCP bridge
# ─────────────────────────────────────────────────────────────────────────────

class SocketDMABackend(MemoryBackend):
    """DMA via MemEdit HTTP server (server.py).

    Compatible with MemEdit's server.py — start it with:
        python apps/MemEdit/server.py --device fpga --host 0.0.0.0 --port 8765 --token <secret>

    Default port: 8765
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 process_name: str = "", token: str = "") -> None:
        self._host  = host
        self._port  = port
        self._name  = process_name
        self._base  = f"http://{host}:{port}"
        self._hdrs  = {"Content-Type": "application/json",
                       "Accept":       "application/json"}
        if token:
            self._hdrs["Authorization"] = f"Bearer {token}"

        # Ensure the server's device is connected
        status = self._get("/api/status")
        if not status.get("connected"):
            dtype = status.get("device_type", "fpga")
            self._post("/api/connect", {"device_type": dtype})

        # Find and attach the target process
        procs = self._get("/api/processes").get("processes", [])
        target = next(
            (p for p in procs
             if p["name"].lower() == process_name.lower()), None)
        if target is None:
            names = [p["name"] for p in procs[:12]]
            raise RuntimeError(
                f"Process '{process_name}' not found on server.\n"
                f"Running: {names}")
        self._pid = target["pid"]
        self._post("/api/attach", {"pid": self._pid})

    # ── HTTP helpers ──────────────────────────────────────────────────────

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(self._base + path, headers=self._hdrs)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode()).get("detail", "")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e

    def _post(self, path: str, body: dict) -> dict:
        data = json.dumps(body).encode()
        req  = urllib.request.Request(self._base + path, data=data,
                                      headers=self._hdrs)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode()).get("detail", "")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e

    @property
    def description(self) -> str:
        return f"DMA/HTTP  {self._host}:{self._port}  {self._name}  PID {self._pid}"

    def read(self, address: int, size: int) -> Optional[bytes]:
        try:
            d = self._post("/api/memory/read",
                           {"address": f"0x{address:016X}", "size": size})
            h = d.get("data", "")
            return bytes.fromhex(h) if h else None
        except Exception:
            return None

    def close(self) -> None:
        pass  # server stays up; session cleanup handled server-side

    def get_processes(self) -> List[Tuple[int, str]]:
        """Enumerate processes from the MemEdit TCP server."""
        try:
            data = self._get("/api/processes").get("processes", [])
            return [(int(p.get("pid", 0)), str(p.get("name", ""))) for p in data]
        except Exception:
            return []
