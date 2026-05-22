"""
MemEdit — Cheat Engine / T-Search style DMA memory editor GUI.

Attaches to any Windows process via PCILeech FPGA DMA (or native/file mode)
and provides:
  - Process browser with filter
  - Memory scanning: exact, range, unknown, changed/unchanged/increased/decreased
  - String and Array-of-Bytes (AoB) pattern search
  - Live-editable results table
  - Address list with freeze / thaw / label
  - Module and memory region browsers
  - Pointer chain resolver

Requirements:
    pip install memprocfs
    MemProcFS native binaries: https://github.com/ufrisk/MemProcFS/releases

Launch:
    python apps/MemEdit/MemEdit.py     (from vivian_cli/ root)
    -- or --
    double-click  apps/MemEdit/launch.bat
"""
from __future__ import annotations

import sys
import os
import json
import struct
import threading
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# ── path bootstrap ─────────────────────────────────────────────────────────────
_HERE     = Path(__file__).resolve().parent
_TOOL_DIR = _HERE.parent.parent / "tools" / "DMAMemoryTool"

if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

# ── dma_memory import ──────────────────────────────────────────────────────────
try:
    from dma_memory import (               # type: ignore
        DMADevice, DataType, ScanType, MemoryScanner,
        DEVICE_FPGA, DEVICE_NATIVE, DEVICE_FILE,
    )
    from dma_memory.types import encode, decode, type_size  # type: ignore
    HAS_DMA  = True
    _DMA_ERR = ""
except ImportError as _e:
    HAS_DMA  = False
    _DMA_ERR = str(_e)

    # ── Fallback type stubs so the GUI works in remote-only mode ───────────────
    import struct as _struct

    class DataType:  # type: ignore
        INT8   = "int8";  INT16  = "int16";  INT32  = "int32";  INT64  = "int64"
        UINT8  = "uint8"; UINT16 = "uint16"; UINT32 = "uint32"; UINT64 = "uint64"
        FLOAT  = "float"; DOUBLE = "double"
        STRING_UTF8  = "string_utf8";  STRING_UTF16 = "string_utf16"
        BYTES  = "bytes"
        def __init__(self, s: str) -> None:
            self.value = s
        def __eq__(self, other: object) -> bool:
            o = other.value if isinstance(other, DataType) else other
            return self.value == o
        def __hash__(self) -> int:
            return hash(self.value)

    class ScanType:  # type: ignore
        EXACT     = "Exact";     RANGE    = "Range"
        UNKNOWN   = "Unknown / First Scan"
        INCREASED = "Increased"; DECREASED = "Decreased"
        CHANGED   = "Changed";   UNCHANGED = "Unchanged"

    _STRUCT_FMTS = {
        "int8":   ("<b", 1), "int16":  ("<h", 2),
        "int32":  ("<i", 4), "int64":  ("<q", 8),
        "uint8":  ("<B", 1), "uint16": ("<H", 2),
        "uint32": ("<I", 4), "uint64": ("<Q", 8),
        "float":  ("<f", 4), "double": ("<d", 8),
    }

    def encode(val: Any, dt: Any) -> bytes:  # type: ignore
        s = dt.value if hasattr(dt, "value") else str(dt)
        if s in _STRUCT_FMTS:
            return _struct.pack(_STRUCT_FMTS[s][0], val)
        if s == "string_utf8":  return str(val).encode("utf-8")
        if s == "string_utf16": return str(val).encode("utf-16-le")
        if s == "bytes":        return val
        raise ValueError(s)

    def decode(raw: bytes, dt: Any) -> Any:  # type: ignore
        s = dt.value if hasattr(dt, "value") else str(dt)
        if s in _STRUCT_FMTS:
            fmt, sz = _STRUCT_FMTS[s]
            return _struct.unpack(fmt, raw[:sz])[0] if len(raw) >= sz else None
        if s == "string_utf8":  return raw.decode("utf-8",    errors="replace").rstrip("\x00")
        if s == "string_utf16": return raw.decode("utf-16-le", errors="replace").rstrip("\x00")
        if s == "bytes":        return raw
        return None

    def type_size(dt: Any) -> int:  # type: ignore
        s = dt.value if hasattr(dt, "value") else str(dt)
        return _STRUCT_FMTS.get(s, ("<i", 4))[1]

# ── colour palette (Catppuccin Mocha dark) ─────────────────────────────────────
C = dict(
    base    = "#1e1e2e",
    mantle  = "#181825",
    crust   = "#11111b",
    srf0    = "#313244",
    srf1    = "#45475a",
    srf2    = "#585b70",
    text    = "#cdd6f4",
    sub     = "#a6adc8",
    blue    = "#89b4fa",
    green   = "#a6e3a1",
    red     = "#f38ba8",
    yellow  = "#f9e2af",
    mauve   = "#cba6f7",
    teal    = "#94e2d5",
    peach   = "#fab387",
    sky     = "#89dceb",
)

_DATA_TYPES  = ["int8","int16","int32","int64",
                "uint8","uint16","uint32","uint64",
                "float","double","string_utf8","string_utf16","bytes"]
_SCAN_MODES  = ["Exact","Range","Unknown / First Scan",
                "Increased","Decreased","Changed","Unchanged"]
_DEVICES     = ["fpga","usb3380","native","file","local","remote"]
_LIVE_DELAY  = 0.5   # seconds between live address-list refreshes


# ── Remote proxy classes ──────────────────────────────────────────────────────

class _RemoteHTTP:
    """Minimal stdlib HTTP client for talking to the MemEdit API server."""

    def __init__(self, host: str, port: int, token: str = "") -> None:
        self._base  = f"http://{host}:{port}"
        self._hdrs  = {"Content-Type": "application/json",
                       "Accept":       "application/json"}
        if token:
            self._hdrs["Authorization"] = f"Bearer {token}"

    def _raise(self, e: urllib.error.HTTPError) -> None:
        try:
            detail = json.loads(e.read().decode()).get("detail", "")
        except Exception:
            detail = str(e)
        raise RuntimeError(f"HTTP {e.code}: {detail}")

    def get(self, path: str) -> dict:
        req = urllib.request.Request(self._base + path, headers=self._hdrs)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            self._raise(e)

    def post(self, path: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body or {}).encode()
        req  = urllib.request.Request(self._base + path, data=data,
                                      headers=self._hdrs)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            self._raise(e)


class _RMatch:
    __slots__ = ("address",)
    def __init__(self, address: int) -> None:
        self.address = address


class RemoteScanResults:
    """Scan results returned by the remote server."""

    def __init__(self, data: dict) -> None:
        self._token   = data.get("token", "")
        self._count   = data.get("count", 0)
        self._matches = [_RMatch(int(m["address"], 16))
                         for m in data.get("matches", [])]

    def __len__(self) -> int:
        return self._count


def _dtype_str(dt: Any) -> str:
    if isinstance(dt, str): return dt
    return getattr(dt, "value", str(dt))


def _stype_str(st: Any) -> str:
    """Convert any ScanType-like value to the string the server expects."""
    if isinstance(st, str):
        return st
    v = getattr(st, "value", None)
    if isinstance(v, str):
        return v
    n = getattr(st, "name", None)
    if n:
        return {"EXACT": "Exact", "RANGE": "Range",
                "UNKNOWN": "Unknown / First Scan",
                "INCREASED": "Increased", "DECREASED": "Decreased",
                "CHANGED": "Changed", "UNCHANGED": "Unchanged"
                }.get(n.upper(), n)
    return str(st)


class RemoteScannerProxy:
    def __init__(self, http: _RemoteHTTP) -> None:
        self._http = http

    def scan(self, val: Any, dt: Any, st: Any,
             value2: Any = None) -> RemoteScanResults:
        payload: dict = {
            "value":     str(val),
            "dtype":     _dtype_str(dt),
            "scan_type": _stype_str(st),
        }
        if value2 is not None:
            payload["value2"] = str(value2)
        return RemoteScanResults(self._http.post("/api/scan/first", payload))

    def next_scan(self, prev: RemoteScanResults,
                  val: Any, st: Any) -> RemoteScanResults:
        payload: dict = {
            "token":     prev._token,
            "scan_type": _stype_str(st),
        }
        if val is not None:
            payload["value"] = str(val)
        return RemoteScanResults(self._http.post("/api/scan/next", payload))

    def search_string(self, text: str, dt: Any) -> RemoteScanResults:
        enc = "utf8" if "utf8" in _dtype_str(dt) else "utf16"
        return RemoteScanResults(
            self._http.post("/api/scan/string",
                            {"text": text, "encoding": enc}))

    def search_aob(self, pattern: str) -> RemoteScanResults:
        return RemoteScanResults(
            self._http.post("/api/scan/aob", {"pattern": pattern}))


class _RModule:
    __slots__ = ("base", "size", "name", "path")
    def __init__(self, d: dict) -> None:
        self.base = int(d["base"], 16)
        self.size = d["size"]
        self.name = d["name"]
        self.path = d["path"]


class RemoteProcessProxy:
    def __init__(self, http: _RemoteHTTP, name: str, pid: int) -> None:
        self._http = http
        self.name  = name
        self.pid   = pid

    def read(self, address: int, size: int) -> Optional[bytes]:
        try:
            d = self._http.post("/api/memory/read",
                                {"address": f"0x{address:016X}", "size": size})
            h = d.get("data", "")
            return bytes.fromhex(h) if h else None
        except Exception:
            return None

    def write(self, address: int, data: bytes) -> bool:
        try:
            r = self._http.post("/api/memory/write",
                                {"address": f"0x{address:016X}",
                                 "data":    data.hex()})
            return bool(r.get("ok", False))
        except Exception:
            return False

    def modules(self) -> List[_RModule]:
        try:
            return [_RModule(m)
                    for m in self._http.get("/api/modules").get("modules", [])]
        except Exception:
            return []

    def memory_regions(self) -> List[dict]:
        try:
            out = []
            for r in self._http.get("/api/regions").get("regions", []):
                out.append({
                    "va_start":   int(r["va_start"],   16),
                    "va_end":     int(r["va_end"],     16),
                    "size":       r["size"],
                    "protection": r.get("protection", ""),
                    "type":       r.get("type", ""),
                    "tag":        r.get("tag",  ""),
                })
            return out
        except Exception:
            return []

    def scanner(self) -> RemoteScannerProxy:
        return RemoteScannerProxy(self._http)

    def resolve_pointer_chain(self, base: int,
                               offsets: List[int]) -> Optional[int]:
        try:
            r = self._http.post("/api/pointer/resolve", {
                "base":    f"0x{base:016X}",
                "offsets": [f"0x{o:X}" for o in offsets],
            })
            v = r.get("result")
            return int(v, 16) if v else None
        except Exception:
            return None


class RemoteDMAProxy:
    """Drop-in replacement for DMADevice that forwards all calls to the API server."""

    def __init__(self, host: str, port: int, token: str = "") -> None:
        self._http        = _RemoteHTTP(host, port, token)
        self._device_type = "remote"

    def connect(self) -> None:
        # Verify connectivity and optionally trigger server-side connect
        status = self._http.get("/api/status")
        if not status.get("connected"):
            # Attempt to connect the server's device using whatever type it was
            # started with (the server stores its device_type).
            dtype = status.get("device_type", "fpga")
            self._http.post("/api/connect", {"device_type": dtype})

    def disconnect(self) -> None:
        try:
            self._http.post("/api/disconnect")
        except Exception:
            pass

    def list_processes(self) -> List[dict]:
        return self._http.get("/api/processes").get("processes", [])

    def get_process(self, pid: int) -> RemoteProcessProxy:
        d = self._http.post("/api/attach", {"pid": pid})
        return RemoteProcessProxy(self._http, d["name"], d["pid"])


# ══════════════════════════════════════════════════════════════════════════════
# Windows local-memory backend  (ctypes — no DMA hardware required)
# ══════════════════════════════════════════════════════════════════════════════

_IS_WIN = sys.platform == "win32"

if _IS_WIN:
    import ctypes as _ct
    import ctypes.wintypes as _wt

    _k32  = _ct.WinDLL("kernel32", use_last_error=True)
    _papi = _ct.WinDLL("psapi",    use_last_error=True)

    PROCESS_ALL_ACCESS   = 0x1F0FFF
    TH32CS_SNAPPROCESS   = 0x00000002
    MEM_COMMIT           = 0x00001000
    PAGE_NOACCESS        = 0x01
    PAGE_GUARD           = 0x100

    class _PROCESSENTRY32(_ct.Structure):
        _fields_ = [
            ("dwSize",              _ct.c_uint32),
            ("cntUsage",            _ct.c_uint32),
            ("th32ProcessID",       _ct.c_uint32),
            ("th32DefaultHeapID",   _ct.c_void_p),   # ULONG_PTR
            ("th32ModuleID",        _ct.c_uint32),
            ("cntThreads",          _ct.c_uint32),
            ("th32ParentProcessID", _ct.c_uint32),
            ("pcPriClassBase",      _ct.c_int32),
            ("dwFlags",             _ct.c_uint32),
            ("szExeFile",           _ct.c_char * 260),
        ]

    class _MBI(_ct.Structure):            # MEMORY_BASIC_INFORMATION (64-bit)
        _fields_ = [
            ("BaseAddress",       _ct.c_uint64),
            ("AllocationBase",    _ct.c_uint64),
            ("AllocationProtect", _ct.c_uint32),
            ("__align1",          _ct.c_uint32),
            ("RegionSize",        _ct.c_uint64),
            ("State",             _ct.c_uint32),
            ("Protect",           _ct.c_uint32),
            ("Type",              _ct.c_uint32),
            ("__align2",          _ct.c_uint32),
        ]

    class _MODINFO(_ct.Structure):        # MODULEINFO
        _fields_ = [
            ("lpBaseOfDll", _ct.c_uint64),
            ("SizeOfImage", _ct.c_uint32),
            ("EntryPoint",  _ct.c_uint64),
        ]

    def _local_open(pid: int) -> int:
        h = _k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not h:
            err = _ct.get_last_error()
            msg = "Access denied — run MemEdit as Administrator." \
                  if err == 5 else f"OpenProcess error {err}"
            raise RuntimeError(msg)
        return h

    def _local_read(handle: int, addr: int, size: int) -> Optional[bytes]:
        buf    = (_ct.c_char * size)()
        n_read = _ct.c_size_t(0)
        ok = _k32.ReadProcessMemory(
            handle, _ct.c_void_p(addr), buf, size, _ct.byref(n_read))
        return bytes(buf[:n_read.value]) if ok else None

    def _local_write(handle: int, addr: int, data: bytes) -> bool:
        buf = (_ct.c_char * len(data))(*data)
        n   = _ct.c_size_t(0)
        return bool(_k32.WriteProcessMemory(
            handle, _ct.c_void_p(addr), buf, len(data), _ct.byref(n)))

    def _local_regions(handle: int):
        """Yield (base, size, protect) for every committed, accessible region."""
        mbi  = _MBI()
        addr = 0
        sz   = _ct.sizeof(mbi)
        while True:
            if _k32.VirtualQueryEx(handle, _ct.c_void_p(addr),
                                   _ct.byref(mbi), sz) != sz:
                break
            if (mbi.State == MEM_COMMIT
                    and mbi.Protect != PAGE_NOACCESS
                    and not (mbi.Protect & PAGE_GUARD)):
                yield int(mbi.BaseAddress), int(mbi.RegionSize), int(mbi.Protect)
            addr = int(mbi.BaseAddress) + int(mbi.RegionSize)
            if addr >= 0x7FFFFFFFFFFF:
                break

else:
    def _local_open(pid):   raise RuntimeError("Local mode requires Windows.")
    def _local_read(*_):    return None
    def _local_write(*_):   return False
    def _local_regions(_):  return iter([])


_PROT_STR: Dict[int, str] = {
    0x01: "---", 0x02: "R--", 0x04: "R-X", 0x08: "RC-",
    0x10: "-W-", 0x20: "RW-", 0x40: "RWX", 0x80: "RWC",
}


class _LMatch:
    __slots__ = ("address",)
    def __init__(self, a: int) -> None:
        self.address = a


class LocalScanResults:
    def __init__(self, matches: List[_LMatch],
                 snap: Optional[Dict[int, bytes]] = None,
                 dt: Any = None) -> None:
        self._matches = matches
        self._snap    = snap or {}   # addr → bytes at scan time
        self._dt      = dt

    def __len__(self) -> int:
        return len(self._matches)


class LocalScannerProxy:
    _CHUNK     = 4 * 1024 * 1024   # 4 MiB per read
    _MAX_ADDRS = 5_000_000

    def __init__(self, handle: int) -> None:
        self._h = handle

    @staticmethod
    def _hit(cur: bytes, target: Optional[bytes], prev: Optional[bytes],
              sn: str, v2: Optional[bytes]) -> bool:
        if sn == "Exact":
            return cur == target
        if sn == "Range" and target and v2:
            return target <= cur <= v2
        if sn in ("Unknown / First Scan",):
            return True
        if sn == "Changed":
            return cur != (prev or b"")
        if sn == "Unchanged":
            return cur == (prev or b"")
        if sn == "Increased":
            return cur > (prev or b"")
        if sn == "Decreased":
            return cur < (prev or b"")
        return cur == target

    def scan(self, val: Any, dt: Any, st: Any,
             value2: Any = None) -> LocalScanResults:
        sn     = _stype_str(st)
        sz     = type_size(dt)
        target = encode(val, dt) if sn != "Unknown / First Scan" else None
        v2     = encode(value2, dt) if value2 is not None else None
        matches: List[_LMatch]   = []
        snap:    Dict[int, bytes] = {}
        for base, size, _ in _local_regions(self._h):
            if len(matches) >= self._MAX_ADDRS:
                break
            off = 0
            while off < size:
                chunk = min(self._CHUNK, size - off)
                raw   = _local_read(self._h, base + off, chunk)
                if not raw:
                    off += chunk
                    continue
                i = 0
                while i <= len(raw) - sz:
                    if len(matches) >= self._MAX_ADDRS:
                        break
                    vraw = raw[i:i + sz]
                    if self._hit(vraw, target, None, sn, v2):
                        addr = base + off + i
                        matches.append(_LMatch(addr))
                        snap[addr] = vraw
                    i += sz
                off += chunk
        return LocalScanResults(matches, snap, dt)

    def next_scan(self, prev: LocalScanResults,
                  val: Any, st: Any) -> LocalScanResults:
        dt     = prev._dt
        sz     = type_size(dt) if dt else 4
        sn     = _stype_str(st)
        target = (encode(val, dt)
                  if val is not None and dt is not None and sn == "Exact"
                  else None)
        matches: List[_LMatch]   = []
        snap:    Dict[int, bytes] = {}
        for m in prev._matches:
            addr     = m.address
            prev_raw = prev._snap.get(addr, b"\x00" * sz)
            cur_raw  = _local_read(self._h, addr, sz)
            if not cur_raw or len(cur_raw) < sz:
                continue
            cur_raw = cur_raw[:sz]
            if self._hit(cur_raw, target, prev_raw, sn, None):
                matches.append(_LMatch(addr))
                snap[addr] = cur_raw
        return LocalScanResults(matches, snap, dt)

    def search_string(self, text: str, dt: Any) -> LocalScanResults:
        enc     = "utf-8" if "utf8" in _dtype_str(dt) else "utf-16-le"
        pattern = text.encode(enc)
        matches: List[_LMatch] = []
        for base, size, _ in _local_regions(self._h):
            off = 0
            while off < size:
                chunk = min(self._CHUNK, size - off)
                raw   = _local_read(self._h, base + off, chunk)
                if not raw:
                    off += chunk
                    continue
                i = 0
                while True:
                    idx = raw.find(pattern, i)
                    if idx == -1:
                        break
                    matches.append(_LMatch(base + off + idx))
                    i = idx + len(pattern)
                off += chunk
        return LocalScanResults(matches)

    def search_aob(self, pattern_str: str) -> LocalScanResults:
        parts = pattern_str.split()
        pat   = [None if p in ("?", "??") else int(p, 16) for p in parts]
        sz    = len(pat)
        matches: List[_LMatch] = []
        for base, size, _ in _local_regions(self._h):
            off = 0
            while off < size:
                chunk = min(self._CHUNK, size - off)
                raw   = _local_read(self._h, base + off, chunk)
                if not raw:
                    off += chunk
                    continue
                for i in range(len(raw) - sz + 1):
                    if all(p is None or raw[i + j] == p
                           for j, p in enumerate(pat)):
                        matches.append(_LMatch(base + off + i))
                off += chunk
        return LocalScanResults(matches)


class LocalProcessProxy:
    def __init__(self, handle: int, name: str, pid: int) -> None:
        self._handle = handle
        self.name    = name
        self.pid     = pid

    def __del__(self) -> None:
        try:
            _k32.CloseHandle(self._handle)  # type: ignore[name-defined]
        except Exception:
            pass

    def read(self, address: int, size: int) -> Optional[bytes]:
        return _local_read(self._handle, address, size)

    def write(self, address: int, data: bytes) -> bool:
        return _local_write(self._handle, address, data)

    def modules(self) -> List[_RModule]:
        if not _IS_WIN:
            return []
        hmodules  = (_wt.HMODULE * 2048)()  # type: ignore[name-defined]
        cb_needed = _wt.DWORD(0)            # type: ignore[name-defined]
        out: List[_RModule] = []
        if not _papi.EnumProcessModules(                 # type: ignore[name-defined]
                self._handle, hmodules,
                _ct.sizeof(hmodules),                    # type: ignore[name-defined]
                _ct.byref(cb_needed)):                   # type: ignore[name-defined]
            return out
        count = cb_needed.value // _ct.sizeof(_wt.HMODULE)  # type: ignore[name-defined]
        mi    = _MODINFO()                                   # type: ignore[name-defined]
        for i in range(count):
            hmod    = hmodules[i]
            nbuf    = _ct.create_unicode_buffer(260)         # type: ignore[name-defined]
            pbuf    = _ct.create_unicode_buffer(1024)        # type: ignore[name-defined]
            _papi.GetModuleBaseNameW(self._handle, hmod, nbuf, 260)     # type: ignore[name-defined]
            _papi.GetModuleFileNameExW(self._handle, hmod, pbuf, 1024)  # type: ignore[name-defined]
            if _papi.GetModuleInformation(                              # type: ignore[name-defined]
                    self._handle, hmod,
                    _ct.byref(mi), _ct.sizeof(mi)):                     # type: ignore[name-defined]
                out.append(_RModule({
                    "base": hex(mi.lpBaseOfDll),
                    "size": mi.SizeOfImage,
                    "name": nbuf.value,
                    "path": pbuf.value,
                }))
        return out

    def memory_regions(self) -> List[dict]:
        return [
            {
                "va_start":   base,
                "va_end":     base + size,
                "size":       size,
                "protection": _PROT_STR.get(protect & 0xFF, hex(protect)),
                "type":       "",
                "tag":        "",
            }
            for base, size, protect in _local_regions(self._handle)
        ]

    def scanner(self) -> LocalScannerProxy:
        return LocalScannerProxy(self._handle)

    def resolve_pointer_chain(self, base: int,
                               offsets: List[int]) -> Optional[int]:
        ptr = base
        for off in offsets[:-1]:
            raw = _local_read(self._handle, ptr + off, 8)
            if not raw or len(raw) < 8:
                return None
            ptr = int.from_bytes(raw[:8], "little")
        if offsets:
            ptr += offsets[-1]
        return ptr


class LocalDMAProxy:
    """Pure-Python local memory access using Windows ReadProcessMemory — no DMA card needed."""

    def connect(self) -> None:
        if not _IS_WIN:
            raise RuntimeError("Local mode is only supported on Windows.")

    def disconnect(self) -> None:
        pass

    def list_processes(self) -> List[dict]:
        procs: List[dict] = []
        if not _IS_WIN:
            return procs
        hsnap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)  # type: ignore[name-defined]
        if hsnap == _ct.c_void_p(-1).value:                            # type: ignore[name-defined]
            return procs
        pe = _PROCESSENTRY32()                                         # type: ignore[name-defined]
        pe.dwSize = _ct.sizeof(_PROCESSENTRY32)                        # type: ignore[name-defined]
        try:
            if _k32.Process32First(hsnap, _ct.byref(pe)):              # type: ignore[name-defined]
                while True:
                    procs.append({
                        "pid":  pe.th32ProcessID,
                        "name": pe.szExeFile.decode("utf-8", errors="replace"),
                    })
                    if not _k32.Process32Next(hsnap, _ct.byref(pe)):   # type: ignore[name-defined]
                        break
        finally:
            _k32.CloseHandle(hsnap)                                    # type: ignore[name-defined]
        return procs

    def get_process(self, pid: int) -> LocalProcessProxy:
        name = next((p["name"] for p in self.list_processes()
                     if p["pid"] == pid), f"PID {pid}")
        return LocalProcessProxy(_local_open(pid), name, pid)


# ══════════════════════════════════════════════════════════════════════════════
# PE dump & header-fix utilities
# ══════════════════════════════════════════════════════════════════════════════

import struct as _struct

# ── constants ──────────────────────────────────────────────────────────────────
_PE_DOS_MAGIC   = 0x5A4D        # "MZ"
_PE_NT_MAGIC    = 0x00004550    # "PE\0\0"
_PE_OPT32       = 0x010B
_PE_OPT64       = 0x020B
_FILE_ALIGN_DEF = 0x200         # 512-byte file alignment default


def _align(val: int, align: int) -> int:
    return (val + align - 1) & ~(align - 1)


def _read_u16(buf: bytes, off: int) -> int:
    return _struct.unpack_from("<H", buf, off)[0]


def _read_u32(buf: bytes, off: int) -> int:
    return _struct.unpack_from("<I", buf, off)[0]


def _write_u32(buf: bytearray, off: int, val: int) -> None:
    _struct.pack_into("<I", buf, off, val & 0xFFFFFFFF)


def _dump_module_bytes(proc: Any, base: int, size: int) -> bytes:
    """Read the full module region from process memory in 4 MiB chunks."""
    CHUNK = 4 * 1024 * 1024
    out   = bytearray(size)
    off   = 0
    while off < size:
        chunk = min(CHUNK, size - off)
        raw   = proc.read(base + off, chunk)
        if raw:
            out[off:off + len(raw)] = raw
        off += chunk
    return bytes(out)


def _fix_pe_headers(raw: bytes) -> bytes:
    """
    Rebuild a memory-dumped PE so it can be loaded as a DLL/EXE.

    When a PE is mapped in memory:
      • Sections are expanded to VirtualSize (page-aligned)
      • PointerToRawData / SizeOfRawData reflect *file* layout — not memory layout

    This function rewrites the section table so that:
      • PointerToRawData = VirtualAddress  (memory dump, sections already in place)
      • SizeOfRawData    = aligned VirtualSize
      • FileAlignment    = SectionAlignment  (simplest valid format for a dump)
      • Checksum         = recalculated

    Returns the patched bytes (same length as input).
    """
    data = bytearray(raw)
    size = len(data)

    # ── validate DOS header ──────────────────────────────────────────────────
    if size < 0x40 or _read_u16(data, 0) != _PE_DOS_MAGIC:
        raise ValueError("Not a valid PE (bad DOS magic).")

    pe_off = _read_u32(data, 0x3C)
    if pe_off + 4 > size or _read_u32(data, pe_off) != _PE_NT_MAGIC:
        raise ValueError("Not a valid PE (bad NT signature).")

    # ── COFF file header ─────────────────────────────────────────────────────
    coff_off    = pe_off + 4
    num_sections = _read_u16(data, coff_off + 2)
    opt_size    = _read_u16(data, coff_off + 16)
    opt_off     = coff_off + 20
    magic       = _read_u16(data, opt_off)

    if magic not in (_PE_OPT32, _PE_OPT64):
        raise ValueError(f"Unknown PE optional header magic: {magic:#x}")

    is64 = (magic == _PE_OPT64)

    # Offsets within optional header
    sect_align_off = opt_off + 32
    file_align_off = opt_off + 36
    sect_align = _read_u32(data, sect_align_off)
    file_align = _read_u32(data, file_align_off)

    # Set FileAlignment = SectionAlignment so PointerToRawData == VirtualAddress
    _write_u32(data, file_align_off, sect_align)
    file_align = sect_align

    # ── section table ─────────────────────────────────────────────────────────
    sect_tbl_off = opt_off + opt_size
    for i in range(num_sections):
        s = sect_tbl_off + i * 40
        if s + 40 > size:
            break
        v_size   = _read_u32(data, s + 8)   # VirtualSize
        v_addr   = _read_u32(data, s + 12)  # VirtualAddress (RVA)
        raw_size = _align(v_size, file_align) if v_size else 0

        # PointerToRawData → VirtualAddress  (sections sit at their RVA in the dump)
        _write_u32(data, s + 20, v_addr)
        # SizeOfRawData    → aligned VirtualSize
        _write_u32(data, s + 16, raw_size)
        # Clear characteristics that break loading
        # (strip discardable flag 0x02000000)
        chars = _read_u32(data, s + 36)
        _write_u32(data, s + 36, chars & ~0x02000000)

    # ── recalculate checksum ───────────────────────────────────────────────────
    # Checksum field offset inside optional header: +64
    chk_off = opt_off + 64
    _write_u32(data, chk_off, 0)            # zero it first
    checksum = 0
    remainder = len(data) % 4
    padded = data + b"\x00" * ((4 - remainder) % 4)
    for i in range(0, len(padded), 4):
        val = _struct.unpack_from("<I", padded, i)[0]
        checksum += val
        checksum  = (checksum & 0xFFFF) + (checksum >> 16)
    checksum  = (checksum & 0xFFFF) + (checksum >> 16)
    checksum += len(data)
    _write_u32(data, chk_off, checksum & 0xFFFFFFFF)

    return bytes(data)


def _remote_kill_module(proc_handle: int, module_base: int) -> str:
    """
    Eject a DLL from a target process via CreateRemoteThread → FreeLibrary.
    Returns a status string.  Windows-only, local mode only.
    """
    if not _IS_WIN:
        return "Module unload only supported on Windows."
    try:
        # FreeLibrary address in kernel32 is the same in every process (same DLL)
        fl_addr = _ct.cast(                                              # type: ignore
            _k32.GetProcAddress(                                         # type: ignore
                _k32.GetModuleHandleW("kernel32.dll"),                   # type: ignore
                b"FreeLibrary"),
            _ct.c_void_p).value                                          # type: ignore
        if not fl_addr:
            return "Could not resolve FreeLibrary address."
        hthread = _k32.CreateRemoteThread(                               # type: ignore
            proc_handle, None, 0,
            _ct.c_void_p(fl_addr),                                       # type: ignore
            _ct.c_void_p(module_base),                                   # type: ignore
            0, None)
        if not hthread:
            err = _ct.get_last_error()                                   # type: ignore
            return f"CreateRemoteThread failed (error {err})."
        _k32.WaitForSingleObject(hthread, 5000)                          # type: ignore
        _k32.CloseHandle(hthread)                                        # type: ignore
        return "ok"
    except Exception as exc:
        return str(exc)


# ── helpers ────────────────────────────────────────────────────────────────────

def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, (bytes, bytearray)):
        return v[:16].hex(" ").upper()
    return str(v)

def _parse_val(s: str, dt: "DataType") -> Any:
    if dt in (DataType.FLOAT, DataType.DOUBLE):
        return float(s)
    if dt in (DataType.STRING_UTF8, DataType.STRING_UTF16):
        return s
    if dt == DataType.BYTES:
        return bytes.fromhex(s.replace(" ",""))
    return int(s, 0)

def _tsz(dt: "DataType") -> int:
    try:
        return type_size(dt)
    except Exception:
        return 4


# ── AddressEntry ───────────────────────────────────────────────────────────────

class AddressEntry:
    """One row in the saved address list with optional freeze."""

    def __init__(self, address: int, value: Any, dtype: "DataType",
                 label: str = "") -> None:
        self.address = address
        self.value   = value
        self.dtype   = dtype
        self.label   = label
        self.frozen  = False
        self._fval: Any = None
        self._fstop = threading.Event()

    def freeze(self, proc: Any) -> None:
        if self.frozen:
            return
        self.frozen = True
        self._fval  = self.value
        self._fstop.clear()
        threading.Thread(target=self._loop, args=(proc,), daemon=True).start()

    def thaw(self) -> None:
        self._fstop.set()
        self.frozen = False

    def _loop(self, proc: Any) -> None:
        while not self._fstop.wait(0.05):
            try:
                proc.write(self.address, encode(self._fval, self.dtype))
            except Exception:
                pass


# ── main application ───────────────────────────────────────────────────────────

class MemEditApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("MemEdit  —  DMA Memory Editor")
        self.geometry("1280x820")
        self.minsize(960, 640)
        self.configure(bg=C["base"])

        # runtime state
        self._dev:      Optional[Any] = None
        self._proc:     Optional[Any] = None
        self._scanner:  Optional[Any] = None
        self._results:  Optional[Any] = None
        self._rdtype:   Optional[Any] = None   # dtype of last scan
        self._procs:    List[Dict]    = []
        self._addrs:    List[AddressEntry] = []
        self._live_running = False

        # player list state
        self._player_name_results: List[int] = []   # addresses found by name search
        self._player_entries:      List[Dict] = []  # {base_addr, name, fields}
        self._player_col_defs:     List[Dict] = []  # {label, offset, dtype, size}
        self._player_cur_idx:      int        = -1

        self._apply_styles()
        self._build()
        self._set_status("Not connected — pick a device and click Connect.")

    # ── styles ─────────────────────────────────────────────────────────────────

    def _apply_styles(self) -> None:
        s = ttk.Style(self)
        s.theme_use("clam")
        bg, b2, b3 = C["base"], C["srf0"], C["srf1"]
        fg, sub    = C["text"], C["sub"]
        acc        = C["blue"]
        font_n     = ("Consolas", 10)
        font_b     = ("Consolas", 10, "bold")

        s.configure(".",
            background=bg, foreground=fg, fieldbackground=b2,
            borderwidth=0, focuscolor=acc, font=font_n)
        for w in ("TFrame","TLabelframe","TLabelframe.Label"):
            s.configure(w, background=bg, foreground=acc)
        s.configure("TLabelframe.Label", font=font_b)
        s.configure("TLabel", background=bg, foreground=fg)
        s.configure("TEntry",
            fieldbackground=b2, foreground=fg, insertbackground=fg,
            borderwidth=1, relief="flat", padding=4)
        s.configure("TCombobox",
            fieldbackground=b2, foreground=fg, background=b2,
            selectbackground=acc, arrowcolor=fg, borderwidth=1)
        s.configure("TButton",
            background=b3, foreground=fg, borderwidth=0,
            padding=(8,4), relief="flat", font=font_n)
        s.map("TButton",
            background=[("active",C["srf2"]),("disabled",b2)],
            foreground=[("disabled",C["srf2"])])
        s.configure("Accent.TButton",
            background=acc, foreground=C["base"], font=font_b)
        s.map("Accent.TButton",
            background=[("active",C["teal"]),("pressed",C["sky"])])
        s.configure("Danger.TButton",
            background=C["red"], foreground=C["base"], font=font_b)
        s.map("Danger.TButton",
            background=[("active",C["peach"])])
        s.configure("TNotebook", background=C["mantle"], borderwidth=0)
        s.configure("TNotebook.Tab",
            background=b2, foreground=sub,
            padding=(12,5), font=font_n)
        s.map("TNotebook.Tab",
            background=[("selected",b3)],
            foreground=[("selected",fg)])
        s.configure("Treeview",
            background=b2, foreground=fg, fieldbackground=b2,
            rowheight=22, borderwidth=0, font=font_n)
        s.configure("Treeview.Heading",
            background=b3, foreground=acc, relief="flat", font=font_b)
        s.map("Treeview",
            background=[("selected",acc)],
            foreground=[("selected",C["base"])])
        s.configure("TScrollbar",
            background=b3, troughcolor=b2, arrowcolor=fg, borderwidth=0)
        s.configure("TSeparator", background=C["srf2"])

    # ── layout ─────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # toolbar
        tb = ttk.Frame(self, padding=(8,5))
        tb.pack(fill="x")
        self._build_toolbar(tb)

        # remote connection row — shown only when device == "remote"
        self._remote_row = ttk.Frame(self, padding=(8, 3))
        self._build_remote_row(self._remote_row)

        self._toolbar_sep = ttk.Separator(self, orient="horizontal")
        self._toolbar_sep.pack(fill="x")

        # content row
        row = ttk.Frame(self)
        row.pack(fill="both", expand=True)

        # left panel
        left = ttk.Frame(row, width=270)
        left.pack(side="left", fill="y", padx=(6,3), pady=6)
        left.pack_propagate(False)
        self._build_left(left)

        ttk.Separator(row, orient="vertical").pack(side="left", fill="y")

        # right notebook
        right = ttk.Frame(row)
        right.pack(side="left", fill="both", expand=True, padx=(3,6), pady=6)
        self._build_right(right)

        # status bar
        self._status = tk.StringVar()
        tk.Label(self, textvariable=self._status,
                 bg=C["mantle"], fg=C["sub"],
                 font=("Consolas",9), anchor="w", padx=8, pady=3
                 ).pack(fill="x", side="bottom")

    # ─ toolbar ─────────────────────────────────────────────────────────────────

    def _build_toolbar(self, p: ttk.Frame) -> None:
        tk.Label(p, text="MemEdit", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",14,"bold")).pack(side="left", padx=(0,14))

        tk.Label(p, text="Device:", bg=C["base"], fg=C["sub"],
                 font=("Consolas",10)).pack(side="left")
        self._dev_var = tk.StringVar(value="fpga")
        ttk.Combobox(p, textvariable=self._dev_var,
                     values=_DEVICES, width=10,
                     state="readonly").pack(side="left", padx=(2,10))

        self._btn_conn = ttk.Button(p, text="⚡ Connect",
                                    style="Accent.TButton",
                                    command=self._do_connect)
        self._btn_conn.pack(side="left", padx=2)

        self._btn_disc = ttk.Button(p, text="✕ Disconnect",
                                    style="Danger.TButton",
                                    command=self._do_disconnect,
                                    state="disabled")
        self._btn_disc.pack(side="left", padx=2)

        self._lbl_conn = tk.Label(p, text="●  Not connected",
                                  bg=C["base"], fg=C["red"],
                                  font=("Consolas",10,"bold"))
        self._lbl_conn.pack(side="left", padx=14)

        self._lbl_proc = tk.Label(p, text="",
                                  bg=C["base"], fg=C["green"],
                                  font=("Consolas",10))
        self._lbl_proc.pack(side="left")

        # Show/hide remote fields when device selection changes
        self._dev_var.trace_add("write", self._on_device_changed)

    # ─ remote connection row ───────────────────────────────────────────────────

    def _build_remote_row(self, p: ttk.Frame) -> None:
        def lbl(text: str) -> None:
            tk.Label(p, text=text, bg=C["base"], fg=C["sub"],
                     font=("Consolas", 10)).pack(side="left", padx=(6, 2))

        lbl("Host:")
        self._rhost = tk.StringVar(value="127.0.0.1")
        ttk.Entry(p, textvariable=self._rhost, width=16).pack(side="left")

        lbl("Port:")
        self._rport = tk.StringVar(value="8765")
        ttk.Entry(p, textvariable=self._rport, width=7).pack(side="left")

        lbl("Token:")
        self._rtoken = tk.StringVar()
        ttk.Entry(p, textvariable=self._rtoken, width=20,
                  show="●").pack(side="left")

        ttk.Separator(p, orient="vertical").pack(side="left", fill="y",
                                                  padx=8, pady=2)
        tk.Label(p,
                 text="Start server:  python apps/MemEdit/server.py --host 0.0.0.0 --token <secret>",
                 bg=C["base"], fg=C["srf2"],
                 font=("Consolas", 8)).pack(side="left")

    def _on_device_changed(self, *_) -> None:
        if self._dev_var.get() == "remote":
            self._remote_row.pack(fill="x", before=self._toolbar_sep)
        else:
            self._remote_row.pack_forget()

    # ─ left panel ──────────────────────────────────────────────────────────────

    def _build_left(self, p: ttk.Frame) -> None:
        # process browser
        pf = ttk.LabelFrame(p, text=" PROCESSES ", padding=4)
        pf.pack(fill="both", expand=True, pady=(0,4))

        fr = ttk.Frame(pf)
        fr.pack(fill="x", pady=(0,4))
        tk.Label(fr, text="🔍", bg=C["base"], fg=C["sub"],
                 font=("Consolas",10)).pack(side="left")
        self._pfilt = tk.StringVar()
        self._pfilt.trace_add("write", lambda *_: self._filter_procs())
        ttk.Entry(fr, textvariable=self._pfilt).pack(
            side="left", fill="x", expand=True, padx=2)

        cols = ("pid","name")
        self._pt = ttk.Treeview(pf, columns=cols, show="headings",
                                 height=15, selectmode="browse")
        self._pt.heading("pid",  text="PID")
        self._pt.heading("name", text="Name")
        self._pt.column("pid",  width=55, anchor="e", stretch=False)
        self._pt.column("name", width=170)
        psb = ttk.Scrollbar(pf, orient="vertical", command=self._pt.yview)
        self._pt.configure(yscrollcommand=psb.set)
        self._pt.pack(side="left", fill="both", expand=True)
        psb.pack(side="left", fill="y")
        self._pt.bind("<Double-1>", lambda _: self._do_attach())

        br = ttk.Frame(pf)
        br.pack(fill="x", pady=(4,0))
        ttk.Button(br, text="↺ Refresh",
                   command=self._refresh_procs).pack(side="left", padx=2)
        ttk.Button(br, text="⚓ Attach",
                   style="Accent.TButton",
                   command=self._do_attach).pack(side="left", padx=2)

        # frozen list
        ff = ttk.LabelFrame(p, text=" FROZEN ADDRESSES ", padding=4)
        ff.pack(fill="x")
        cols2 = ("addr","val","type")
        self._ft = ttk.Treeview(ff, columns=cols2, show="headings",
                                 height=5, selectmode="browse")
        self._ft.heading("addr", text="Address")
        self._ft.heading("val",  text="Value")
        self._ft.heading("type", text="Type")
        self._ft.column("addr", width=125)
        self._ft.column("val",  width=75)
        self._ft.column("type", width=65)
        self._ft.pack(fill="x")
        ttk.Button(ff, text="✕ Unfreeze Selected",
                   style="Danger.TButton",
                   command=self._thaw_selected).pack(fill="x", pady=(4,0))

    # ─ right notebook ──────────────────────────────────────────────────────────

    def _build_right(self, p: ttk.Frame) -> None:
        self._nb = ttk.Notebook(p)
        self._nb.pack(fill="both", expand=True)

        self._tscan    = ttk.Frame(self._nb)
        self._tresults = ttk.Frame(self._nb)
        self._tplayers = ttk.Frame(self._nb)
        self._tmodules = ttk.Frame(self._nb)
        self._tregions = ttk.Frame(self._nb)

        self._nb.add(self._tscan,    text="  🔍 Scan  ")
        self._nb.add(self._tresults, text="  📋 Results  ")
        self._nb.add(self._tplayers, text="  🎮 Players  ")
        self._nb.add(self._tmodules, text="  📦 Modules  ")
        self._nb.add(self._tregions, text="  🗺 Regions  ")

        self._build_scan_tab()
        self._build_results_tab()
        self._build_players_tab()
        self._build_modules_tab()
        self._build_regions_tab()

    # ─ scan tab ────────────────────────────────────────────────────────────────

    def _build_scan_tab(self) -> None:
        pad = ttk.Frame(self._tscan, padding=14)
        pad.pack(fill="both", expand=True)

        def lbl(parent, text, w=10):
            tk.Label(parent, text=text, bg=C["base"], fg=C["sub"],
                     font=("Consolas",10), width=w, anchor="w").pack(side="left")

        # ── numeric scan section ────────────────────────────────────────────
        tk.Label(pad, text="Numeric Scan", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",12,"bold")).pack(anchor="w", pady=(0,8))

        r1 = ttk.Frame(pad); r1.pack(fill="x", pady=3)
        lbl(r1, "Value:")
        self._sval = tk.StringVar()
        ttk.Entry(r1, textvariable=self._sval, width=22).pack(side="left", padx=(0,10))
        lbl(r1, "Type:", w=6)
        self._stype = tk.StringVar(value="int32")
        ttk.Combobox(r1, textvariable=self._stype,
                     values=_DATA_TYPES, width=14,
                     state="readonly").pack(side="left")

        r2 = ttk.Frame(pad); r2.pack(fill="x", pady=3)
        lbl(r2, "Scan mode:")
        self._smode = tk.StringVar(value="Exact")
        ttk.Combobox(r2, textvariable=self._smode,
                     values=_SCAN_MODES, width=22,
                     state="readonly").pack(side="left", padx=(0,10))
        lbl(r2, "Value 2\n(range max):", w=14)
        self._sval2 = tk.StringVar()
        ttk.Entry(r2, textvariable=self._sval2, width=14).pack(side="left")

        r3 = ttk.Frame(pad); r3.pack(fill="x", pady=(6,4))
        self._btn_first = ttk.Button(r3, text="🔍 First Scan",
                                     style="Accent.TButton",
                                     command=self._do_first_scan)
        self._btn_first.pack(side="left", padx=(0,6))
        self._btn_next = ttk.Button(r3, text="🔄 Next Scan",
                                    command=self._do_next_scan,
                                    state="disabled")
        self._btn_next.pack(side="left", padx=(0,6))
        ttk.Button(r3, text="⭮ New Scan",
                   command=self._do_new_scan).pack(side="left")

        self._scan_info = tk.Label(pad, text="", bg=C["base"],
                                   fg=C["yellow"], font=("Consolas",10))
        self._scan_info.pack(anchor="w", pady=(4,0))

        ttk.Separator(pad, orient="horizontal").pack(fill="x", pady=12)

        # ── string / AoB section ────────────────────────────────────────────
        tk.Label(pad, text="String / AoB Search", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",12,"bold")).pack(anchor="w", pady=(0,8))

        rs = ttk.Frame(pad); rs.pack(fill="x", pady=3)
        lbl(rs, "Text / AoB:")
        self._sstr = tk.StringVar()
        ttk.Entry(rs, textvariable=self._sstr, width=34).pack(side="left", padx=(0,8))
        self._senc = tk.StringVar(value="utf16")
        ttk.Combobox(rs, textvariable=self._senc,
                     values=["utf8","utf16"], width=7,
                     state="readonly").pack(side="left")

        rsb = ttk.Frame(pad); rsb.pack(fill="x", pady=3)
        ttk.Button(rsb, text="🔠 Search String",
                   command=self._do_str_search).pack(side="left", padx=(0,6))
        ttk.Button(rsb, text="🔢 AoB Scan (hex: 48 8B ? ? 00)",
                   command=self._do_aob_scan).pack(side="left")

        ttk.Separator(pad, orient="horizontal").pack(fill="x", pady=12)

        # ── pointer chain ────────────────────────────────────────────────────
        tk.Label(pad, text="Pointer Chain Resolver", bg=C["base"], fg=C["mauve"],
                 font=("Consolas",12,"bold")).pack(anchor="w", pady=(0,8))

        rp = ttk.Frame(pad); rp.pack(fill="x", pady=3)
        lbl(rp, "Base addr:")
        self._pbase = tk.StringVar()
        ttk.Entry(rp, textvariable=self._pbase, width=20).pack(side="left", padx=(0,10))
        lbl(rp, "Offsets (0x10,0x50):", w=20)
        self._poffs = tk.StringVar()
        ttk.Entry(rp, textvariable=self._poffs, width=22).pack(side="left")

        rp2 = ttk.Frame(pad); rp2.pack(fill="x", pady=3)
        ttk.Button(rp2, text="🔗 Resolve", command=self._do_resolve).pack(side="left", padx=(0,8))
        self._plbl = tk.Label(rp2, text="", bg=C["base"],
                              fg=C["green"], font=("Consolas",10))
        self._plbl.pack(side="left")

    # ─ results tab ─────────────────────────────────────────────────────────────

    def _build_results_tab(self) -> None:
        top = ttk.Frame(self._tresults, padding=(6,6,6,0))
        top.pack(fill="x")
        self._res_lbl = tk.Label(top, text="0 results", bg=C["base"],
                                 fg=C["sub"], font=("Consolas",10))
        self._res_lbl.pack(side="left")
        ttk.Button(top, text="↺ Refresh values",
                   command=self._refresh_result_vals).pack(side="left", padx=8)
        ttk.Button(top, text="📌 Add selected to list",
                   command=self._add_to_addr_list).pack(side="left", padx=2)

        # scan results tree
        sf = ttk.LabelFrame(self._tresults, text=" Scan Results ", padding=4)
        sf.pack(fill="both", expand=True, padx=6, pady=4)

        rcols = ("address","value","type")
        self._rt = ttk.Treeview(sf, columns=rcols, show="headings",
                                 height=10, selectmode="extended")
        self._rt.heading("address", text="Address")
        self._rt.heading("value",   text="Current Value")
        self._rt.heading("type",    text="Type")
        self._rt.column("address", width=165, anchor="e")
        self._rt.column("value",   width=130)
        self._rt.column("type",    width=110)
        rsb = ttk.Scrollbar(sf, orient="vertical", command=self._rt.yview)
        self._rt.configure(yscrollcommand=rsb.set)
        self._rt.pack(side="left", fill="both", expand=True)
        rsb.pack(side="left", fill="y")
        self._rt.bind("<Double-1>", lambda _: self._edit_result())

        # address list
        af = ttk.LabelFrame(self._tresults, text=" Address List ", padding=4)
        af.pack(fill="both", expand=True, padx=6, pady=(0,6))

        acols = ("address","label","value","type","frozen")
        self._at = ttk.Treeview(af, columns=acols, show="headings",
                                 height=8, selectmode="browse")
        self._at.heading("address", text="Address")
        self._at.heading("label",   text="Label")
        self._at.heading("value",   text="Value")
        self._at.heading("type",    text="Type")
        self._at.heading("frozen",  text="Frozen")
        self._at.column("address", width=155, anchor="e")
        self._at.column("label",   width=120)
        self._at.column("value",   width=110)
        self._at.column("type",    width=95)
        self._at.column("frozen",  width=55, anchor="center")
        asb = ttk.Scrollbar(af, orient="vertical", command=self._at.yview)
        self._at.configure(yscrollcommand=asb.set)
        self._at.pack(side="left", fill="both", expand=True)
        asb.pack(side="left", fill="y")
        self._at.bind("<Double-1>", lambda _: self._edit_addr())

        ab = ttk.Frame(af); ab.pack(fill="x", pady=(4,0))
        ttk.Button(ab, text="✎ Edit",
                   command=self._edit_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="❄ Freeze",
                   command=self._freeze_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="🔥 Thaw",
                   command=self._thaw_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="🏷 Label",
                   command=self._label_addr).pack(side="left", padx=2)
        ttk.Button(ab, text="✕ Remove",
                   style="Danger.TButton",
                   command=self._remove_addr).pack(side="right", padx=2)

    # ─ players tab ─────────────────────────────────────────────────────────────

    def _build_players_tab(self) -> None:
        pad = ttk.Frame(self._tplayers, padding=8)
        pad.pack(fill="both", expand=True)

        # ── top row: search | struct config ─────────────────────────────────
        top = ttk.Frame(pad)
        top.pack(fill="x", pady=(0, 6))

        # ─ player name search ────────────────────────────────────────────────
        sf = ttk.LabelFrame(top, text=" Player Name Search ", padding=8)
        sf.pack(side="left", fill="both", expand=True, padx=(0, 6))

        sr = ttk.Frame(sf); sr.pack(fill="x", pady=(0, 4))
        tk.Label(sr, text="Name:", bg=C["base"], fg=C["sub"],
                 font=("Consolas", 10), width=6, anchor="w").pack(side="left")
        self._pname_var = tk.StringVar()
        ttk.Entry(sr, textvariable=self._pname_var, width=22).pack(
            side="left", padx=(0, 6))
        self._pname_enc = tk.StringVar(value="utf16")
        ttk.Combobox(sr, textvariable=self._pname_enc,
                     values=["utf8", "utf16"], width=6,
                     state="readonly").pack(side="left", padx=(0, 6))
        ttk.Button(sr, text="🔍 Search", style="Accent.TButton",
                   command=self._do_player_name_search).pack(side="left")

        self._pname_status = tk.Label(sf, text="", bg=C["base"],
                                      fg=C["sub"], font=("Consolas", 9))
        self._pname_status.pack(anchor="w", pady=(0, 2))

        pncols = ("address", "preview")
        self._pnt = ttk.Treeview(sf, columns=pncols, show="headings",
                                  height=5, selectmode="browse")
        self._pnt.heading("address", text="Address")
        self._pnt.heading("preview", text="Context (±16 bytes)")
        self._pnt.column("address", width=155, anchor="e")
        self._pnt.column("preview", width=260)
        pnsb = ttk.Scrollbar(sf, orient="vertical", command=self._pnt.yview)
        self._pnt.configure(yscrollcommand=pnsb.set)
        self._pnt.pack(side="left", fill="both", expand=True)
        pnsb.pack(side="left", fill="y")

        # ─ struct config ──────────────────────────────────────────────────────
        cf = ttk.LabelFrame(top, text=" Struct Configuration ", padding=8)
        cf.pack(side="left", fill="y")

        def _cfg_row(parent, label, var, default):
            r = ttk.Frame(parent); r.pack(fill="x", pady=3)
            tk.Label(r, text=label, bg=C["base"], fg=C["sub"],
                     font=("Consolas", 10), width=18, anchor="w").pack(side="left")
            v = tk.StringVar(value=default)
            ttk.Entry(r, textvariable=v, width=10).pack(side="left")
            return v

        self._pcfg_stride    = _cfg_row(cf, "Struct stride (bytes):", None, "0x100")
        self._pcfg_nameoff   = _cfg_row(cf, "Name offset in struct:", None, "0x0")
        self._pcfg_namesz    = _cfg_row(cf, "Name size (bytes):",     None, "32")
        self._pcfg_maxp      = _cfg_row(cf, "Max players:",           None, "64")

        ttk.Separator(cf, orient="horizontal").pack(fill="x", pady=6)

        ttk.Button(cf, text="🎮 Build Player List",
                   style="Accent.TButton",
                   command=self._do_build_player_list).pack(fill="x", pady=2)
        ttk.Button(cf, text="🎮 Build from Selected Address",
                   command=self._do_build_from_selected).pack(fill="x", pady=2)

        tk.Label(cf,
                 text=("Select a row in the search results\n"
                       "then click 'Build from Selected'"),
                 bg=C["base"], fg=C["srf2"],
                 font=("Consolas", 8), justify="left").pack(anchor="w", pady=(4, 0))

        # ── player list ───────────────────────────────────────────────────────
        plf = ttk.LabelFrame(pad, text=" Player List ", padding=4)
        plf.pack(fill="both", expand=True)

        # toolbar
        ptb = ttk.Frame(plf); ptb.pack(fill="x", pady=(0, 4))
        ttk.Button(ptb, text="↺ Refresh",
                   command=self._do_player_refresh).pack(side="left", padx=2)
        ttk.Button(ptb, text="+ Add Column…",
                   command=self._player_add_col).pack(side="left", padx=2)
        ttk.Button(ptb, text="✕ Remove Column",
                   command=self._player_remove_col).pack(side="left", padx=2)
        ttk.Separator(ptb, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(ptb, text="◀",
                   command=lambda: self._player_nav(-1)).pack(side="left", padx=1)
        self._player_nav_lbl = tk.Label(ptb, text="  —  ",
                                         bg=C["base"], fg=C["sub"],
                                         font=("Consolas", 10))
        self._player_nav_lbl.pack(side="left")
        ttk.Button(ptb, text="▶",
                   command=lambda: self._player_nav(+1)).pack(side="left", padx=1)
        ttk.Separator(ptb, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(ptb, text="📌 Add to Address List",
                   command=self._player_add_to_addr).pack(side="left", padx=2)
        ttk.Button(ptb, text="✎ Edit Field",
                   command=self._player_edit_field).pack(side="left", padx=2)

        # player tree frame (holds tree + scrollbars)
        self._player_tree_frame = ttk.Frame(plf)
        self._player_tree_frame.pack(fill="both", expand=True)
        self._player_tree: Optional[ttk.Treeview] = None
        self._rebuild_player_tree()

    def _rebuild_player_tree(self) -> None:

        """Destroy and recreate the player treeview with current column defs."""
        for w in self._player_tree_frame.winfo_children():
            w.destroy()

        base_cols = ("idx", "address", "name")
        extra_cols = tuple(f"col{i}" for i in range(len(self._player_col_defs)))
        all_cols = base_cols + extra_cols

        self._player_tree = ttk.Treeview(
            self._player_tree_frame,
            columns=all_cols,
            show="headings",
            selectmode="browse",
        )
        self._player_tree.heading("idx",     text="#")
        self._player_tree.heading("address", text="Address")
        self._player_tree.heading("name",    text="Name")
        self._player_tree.column("idx",     width=40,  anchor="e", stretch=False)
        self._player_tree.column("address", width=155, anchor="e", stretch=False)
        self._player_tree.column("name",    width=160)

        for i, cd in enumerate(self._player_col_defs):
            cid = f"col{i}"
            self._player_tree.heading(cid, text=cd["label"])
            self._player_tree.column(cid, width=110)

        ptsb = ttk.Scrollbar(self._player_tree_frame, orient="vertical",
                              command=self._player_tree.yview)
        self._player_tree.configure(yscrollcommand=ptsb.set)
        self._player_tree.pack(side="left", fill="both", expand=True)
        ptsb.pack(side="left", fill="y")
        self._player_tree.bind("<<TreeviewSelect>>",
                               lambda _: self._on_player_select())
        self._populate_player_tree()

    def _populate_player_tree(self) -> None:
        if self._player_tree is None:
            return
        self._player_tree.delete(*self._player_tree.get_children())
        for i, entry in enumerate(self._player_entries):
            tag = "cur" if i == self._player_cur_idx else ""
            vals = [str(i + 1),
                    f"0x{entry['base_addr']:016X}",
                    entry["name"]]
            vals += [_fmt(v) for v in entry.get("fields", [])]
            iid = self._player_tree.insert("", "end", values=vals, tags=(tag,))
            if i == self._player_cur_idx:
                self._player_tree.selection_set(iid)
                self._player_tree.see(iid)
        self._player_tree.tag_configure("cur",
                                         background=C["mauve"],
                                         foreground=C["base"])
        total = len(self._player_entries)
        cur   = self._player_cur_idx + 1 if self._player_cur_idx >= 0 else 0
        self._player_nav_lbl.config(
            text=f"  {cur} / {total}  " if total else "  —  ")

    # ─ player actions ──────────────────────────────────────────────────────────

    def _do_player_name_search(self) -> None:
        if not self._need_proc():
            return
        name = self._pname_var.get().strip()
        if not name:
            messagebox.showwarning("Empty", "Enter a player name to search for.")
            return
        enc = self._pname_enc.get()
        dt  = DataType.STRING_UTF8 if enc == "utf8" else DataType.STRING_UTF16
        self._pname_status.config(text="⏳ Searching…", fg=C["yellow"])

        def _work():
            try:
                t0  = time.time()
                res = self._scanner.search_string(name, dt)
                elapsed = time.time() - t0
                addrs = [m.address for m in res._matches]
                self.after(0, lambda: self._on_player_name_found(addrs, elapsed))
            except Exception as exc:
                self.after(0, lambda:
                    self._pname_status.config(
                        text=f"✗ {exc}", fg=C["red"]))

        threading.Thread(target=_work, daemon=True).start()

    def _on_player_name_found(self, addrs: List[int], elapsed: float) -> None:
        self._player_name_results = addrs
        self._pnt.delete(*self._pnt.get_children())
        for addr in addrs[:500]:
            preview = ""
            if self._proc:
                try:
                    raw = self._proc.read(addr, 32)
                    enc = self._pname_enc.get()
                    if raw:
                        if enc == "utf16":
                            preview = raw.decode("utf-16-le", errors="replace")[:16]
                        else:
                            preview = raw.decode("utf-8",  errors="replace")[:16]
                        preview = repr(preview.rstrip("\x00"))
                except Exception:
                    preview = ""
            self._pnt.insert("", "end",
                values=(f"0x{addr:016X}", preview))
        self._pname_status.config(
            text=f"✔  {len(addrs)} location(s) found in {elapsed:.2f}s",
            fg=C["green"] if addrs else C["red"])

    def _parse_pcfg(self):
        """Return (stride, name_off, name_sz, max_p) or None on error."""
        try:
            stride  = int(self._pcfg_stride.get(),  0)
            nameoff = int(self._pcfg_nameoff.get(), 0)
            namesz  = int(self._pcfg_namesz.get(),  0)
            maxp    = int(self._pcfg_maxp.get(),    0)
            if stride <= 0:
                raise ValueError("Stride must be > 0")
            return stride, nameoff, namesz, maxp
        except ValueError as exc:
            messagebox.showerror("Config error", str(exc))
            return None

    def _read_player_name(self, base_addr: int,
                          name_off: int, name_sz: int) -> str:
        """Read a fixed-length name string from base_addr + name_off."""
        if not self._proc:
            return ""
        try:
            raw = self._proc.read(base_addr + name_off, name_sz)
            if not raw:
                return ""
            enc = self._pname_enc.get()
            if enc == "utf16":
                return raw.decode("utf-16-le", errors="replace").rstrip("\x00")
            return raw.decode("utf-8", errors="replace").rstrip("\x00")
        except Exception:
            return ""

    def _build_player_entries(self, list_base: int,
                               stride: int, name_off: int,
                               name_sz: int, max_p: int) -> List[Dict]:
        """Walk an array of player structs starting at list_base."""
        entries = []
        for i in range(max_p):
            base = list_base + i * stride
            name = self._read_player_name(base, name_off, name_sz)
            if not name:
                continue  # skip empty slots
            fields = []
            for cd in self._player_col_defs:
                try:
                    dt  = DataType(cd["dtype"])
                    raw = self._proc.read(base + cd["offset"], cd["size"])
                    fields.append(decode(raw, dt) if raw else None)
                except Exception:
                    fields.append(None)
            entries.append({"base_addr": base, "name": name,
                             "fields": fields})
        return entries

    def _do_build_player_list(self) -> None:
        """Ask user for the base address of the player array directly."""
        if not self._need_proc():
            return
        cfg = self._parse_pcfg()
        if cfg is None:
            return
        stride, name_off, name_sz, max_p = cfg
        base_str = simpledialog.askstring(
            "Player array base address",
            "Enter the base address of the player array\n"
            "(hex OK, e.g. 0x1234ABCD):",
            parent=self)
        if base_str is None:
            return
        try:
            list_base = int(base_str, 0)
        except ValueError as exc:
            messagebox.showerror("Parse error", str(exc))
            return
        self._set_status("Building player list…")
        self.after(10, lambda:
            self._finish_build(list_base, stride, name_off, name_sz, max_p))

    def _do_build_from_selected(self) -> None:
        """Use a selected name-search result as the anchor to find the array."""
        if not self._need_proc():
            return
        sel = self._pnt.selection()
        if not sel:
            messagebox.showinfo("Nothing selected",
                "Search for a name first, then select a result row.")
            return
        cfg = self._parse_pcfg()
        if cfg is None:
            return
        stride, name_off, name_sz, max_p = cfg

        addr_str = self._pnt.item(sel[0], "values")[0]
        found_addr = int(addr_str, 16)

        # The name field is at found_addr = struct_base + name_off
        # So struct_base of this player = found_addr - name_off
        player_base = found_addr - name_off

        # Align to stride boundary to guess list start
        # Walk backwards up to max_p/2 steps while names are non-empty
        list_base = player_base
        for _ in range(max_p):
            prev = list_base - stride
            test = self._read_player_name(prev, name_off, name_sz)
            if test:
                list_base = prev
            else:
                break

        self._set_status("Building player list…")
        self.after(10, lambda:
            self._finish_build(list_base, stride, name_off, name_sz, max_p))

    def _finish_build(self, list_base: int, stride: int,
                       name_off: int, name_sz: int, max_p: int) -> None:
        entries = self._build_player_entries(
            list_base, stride, name_off, name_sz, max_p)
        self._player_entries = entries
        self._player_cur_idx = 0 if entries else -1
        self._rebuild_player_tree()
        self._set_status(
            f"Player list built — {len(entries)} player(s) found "
            f"starting at 0x{list_base:016X} (stride 0x{stride:X}")
        if entries:
            self._nb.select(self._tplayers)

    def _do_player_refresh(self) -> None:
        """Re-read names and extra fields for all known player entries."""
        if not self._proc or not self._player_entries:
            return
        cfg = self._parse_pcfg()
        if cfg is None:
            return
        _, name_off, name_sz, _ = cfg
        for entry in self._player_entries:
            entry["name"] = self._read_player_name(
                entry["base_addr"], name_off, name_sz)
            fields = []
            for cd in self._player_col_defs:
                try:
                    dt  = DataType(cd["dtype"])
                    raw = self._proc.read(
                        entry["base_addr"] + cd["offset"], cd["size"])
                    fields.append(decode(raw, dt) if raw else None)
                except Exception:
                    fields.append(None)
            entry["fields"] = fields
        self._populate_player_tree()
        self._set_status(f"Player list refreshed ({len(self._player_entries)} entries).")

    def _on_player_select(self) -> None:
        if self._player_tree is None:
            return
        sel = self._player_tree.selection()
        if not sel:
            return
        idx = self._player_tree.index(sel[0])
        if 0 <= idx < len(self._player_entries):
            self._player_cur_idx = idx
            self._player_nav_lbl.config(
                text=f"  {idx + 1} / {len(self._player_entries)}  ")

    def _player_nav(self, delta: int) -> None:
        if not self._player_entries:
            return
        n = len(self._player_entries)
        self._player_cur_idx = max(0, min(n - 1,
                                           self._player_cur_idx + delta))
        self._populate_player_tree()

    def _player_add_col(self) -> None:
        """Dialog to add a monitored offset column to the player list."""
        dlg = tk.Toplevel(self)
        dlg.title("Add Column")
        dlg.configure(bg=C["base"])
        dlg.resizable(False, False)
        dlg.grab_set()

        def lbl(parent, text):
            tk.Label(parent, text=text, bg=C["base"], fg=C["sub"],
                     font=("Consolas", 10), width=14, anchor="w").pack(side="left")

        for r_text, var_name, default in [
            ("Column label:",         "_dlg_clabel", "Health"),
            ("Offset in struct (hex):","_dlg_coffset","0x10"),
        ]:
            r = ttk.Frame(dlg, padding=(12, 4)); r.pack(fill="x")
            lbl(r, r_text)
            v = tk.StringVar(value=default)
            setattr(dlg, var_name, v)
            ttk.Entry(r, textvariable=v, width=18).pack(side="left")

        r = ttk.Frame(dlg, padding=(12, 4)); r.pack(fill="x")
        lbl(r, "Data type:")
        dlg._dlg_dtype = tk.StringVar(value="float")
        ttk.Combobox(r, textvariable=dlg._dlg_dtype,
                     values=_DATA_TYPES, width=14,
                     state="readonly").pack(side="left")

        def _ok():
            try:
                label  = dlg._dlg_clabel.get().strip() or "?"
                offset = int(dlg._dlg_coffset.get(), 0)
                dtype  = dlg._dlg_dtype.get()
                size   = _tsz(DataType(dtype))
                self._player_col_defs.append(
                    {"label": label, "offset": offset,
                     "dtype": dtype, "size": size})
                dlg.destroy()
                self._rebuild_player_tree()
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=dlg)

        bf = ttk.Frame(dlg, padding=(12, 8)); bf.pack()
        ttk.Button(bf, text="Add",  style="Accent.TButton",
                   command=_ok).pack(side="left", padx=4)
        ttk.Button(bf, text="Cancel", command=dlg.destroy).pack(side="left", padx=4)

    def _player_remove_col(self) -> None:
        if not self._player_col_defs:
            return
        labels = [cd["label"] for cd in self._player_col_defs]
        choice = simpledialog.askstring(
            "Remove column",
            "Column label to remove:\n" + "\n".join(labels),
            parent=self)
        if choice is None:
            return
        self._player_col_defs = [
            cd for cd in self._player_col_defs
            if cd["label"] != choice]
        self._rebuild_player_tree()

    def _player_add_to_addr(self) -> None:
        """Add the selected player's base address (or a specific field) to the address list."""
        if self._player_tree is None:
            return
        sel = self._player_tree.selection()
        if not sel:
            if 0 <= self._player_cur_idx < len(self._player_entries):
                idx = self._player_cur_idx
            else:
                messagebox.showinfo("None selected", "Select a player first.")
                return
        else:
            idx = self._player_tree.index(sel[0])

        entry = self._player_entries[idx]

        choices = ["base struct address"]
        choices += [f"{cd['label']} (+0x{cd['offset']:X})  [{cd['dtype']}]"
                    for cd in self._player_col_defs]
        if len(choices) == 1:
            # Only base address available
            addr = entry["base_addr"]
            if not any(e.address == addr for e in self._addrs):
                self._addrs.append(
                    AddressEntry(addr, 0, DataType("uint8"),
                                 label=entry["name"]))
                self._refresh_addr_tree()
                self._set_status(f"Added {entry['name']} base @ 0x{addr:016X}")
            return

        choice = simpledialog.askinteger(
            "Add to address list",
            "Which field?\n" +
            "\n".join(f"  {i}: {c}" for i, c in enumerate(choices)) +
            "\n\nEnter number:",
            parent=self, minvalue=0, maxvalue=len(choices) - 1)
        if choice is None:
            return

        if choice == 0:
            addr  = entry["base_addr"]
            dtype = DataType("uint8")
            label = entry["name"] + " (base)"
        else:
            cd    = self._player_col_defs[choice - 1]
            addr  = entry["base_addr"] + cd["offset"]
            dtype = DataType(cd["dtype"])
            label = f"{entry['name']}.{cd['label']}"

        if not any(e.address == addr for e in self._addrs):
            self._addrs.append(AddressEntry(addr, 0, dtype, label=label))
            self._refresh_addr_tree()
            self._set_status(f"Added '{label}' @ 0x{addr:016X} to address list.")

    def _player_edit_field(self) -> None:
        """Write a new value to the selected player's selected column field."""
        if not self._proc or not self._player_col_defs:
            messagebox.showinfo("No columns",
                "Add at least one column before editing a field.")
            return
        if self._player_tree is None:
            return
        sel = self._player_tree.selection()
        if not sel:
            messagebox.showinfo("None selected", "Select a player row first.")
            return
        idx = self._player_tree.index(sel[0])
        if not (0 <= idx < len(self._player_entries)):
            return
        entry = self._player_entries[idx]

        labels = [f"{i+1}: {cd['label']} (+0x{cd['offset']:X})  [{cd['dtype']}]"
                  for i, cd in enumerate(self._player_col_defs)]
        col_str = simpledialog.askstring(
            "Select field",
            "Which column to edit?\n" + "\n".join(labels) +
            "\n\nEnter number (1…{}):" .format(len(self._player_col_defs)),
            parent=self)
        if col_str is None:
            return
        try:
            col_idx = int(col_str) - 1
            cd = self._player_col_defs[col_idx]
        except (ValueError, IndexError):
            messagebox.showerror("Error", "Invalid column number.")
            return

        addr   = entry["base_addr"] + cd["offset"]
        dt     = DataType(cd["dtype"])
        cur_v  = _fmt(entry["fields"][col_idx]) if entry["fields"] else ""
        new_s  = simpledialog.askstring(
            "Edit field",
            f"New value for {entry['name']}.{cd['label']}\n"
            f"(addr 0x{addr:016X}, type {cd['dtype']}):",
            parent=self, initialvalue=cur_v)
        if new_s is None:
            return
        try:
            val = _parse_val(new_s, dt)
            ok  = self._proc.write(addr, encode(val, dt))
            if ok:
                entry["fields"][col_idx] = val
                self._populate_player_tree()
                self._set_status(
                    f"Written {entry['name']}.{cd['label']} = {_fmt(val)}")
            else:
                messagebox.showerror("Write failed",
                    f"Could not write to 0x{addr:016X}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    # ─ modules tab ─────────────────────────────────────────────────────────────

    def _build_modules_tab(self) -> None:
        top = ttk.Frame(self._tmodules, padding=(6,6,6,0))
        top.pack(fill="x")
        ttk.Button(top, text="↺ Refresh",
                   command=self._refresh_modules).pack(side="left")
        tk.Label(top, text="  Right-click a module for options",
                 bg=C["base"], fg=C["srf2"],
                 font=("Consolas", 9)).pack(side="left", padx=8)

        f = ttk.Frame(self._tmodules, padding=6)
        f.pack(fill="both", expand=True)

        mcols = ("base","size","name","path")
        self._mt = ttk.Treeview(f, columns=mcols, show="headings")
        self._mt.heading("base", text="Base Address")
        self._mt.heading("size", text="Size")
        self._mt.heading("name", text="Name")
        self._mt.heading("path", text="Full Path")
        self._mt.column("base", width=155, anchor="e")
        self._mt.column("size", width=90,  anchor="e")
        self._mt.column("name", width=155)
        self._mt.column("path", width=370)
        msby = ttk.Scrollbar(f, orient="vertical",   command=self._mt.yview)
        msbx = ttk.Scrollbar(f, orient="horizontal", command=self._mt.xview)
        self._mt.configure(yscrollcommand=msby.set, xscrollcommand=msbx.set)
        self._mt.grid(row=0, column=0, sticky="nsew")
        msby.grid(row=0, column=1, sticky="ns")
        msbx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

        # right-click context menu
        self._mod_menu = tk.Menu(self, tearoff=0,
                                  bg=C["srf0"], fg=C["text"],
                                  activebackground=C["blue"],
                                  activeforeground=C["base"])
        self._mod_menu.add_command(label="📥  Dump module to DLL…",
                                    command=self._mod_dump)
        self._mod_menu.add_command(label="🔧  Dump + Fix PE headers…",
                                    command=self._mod_dump_fix)
        self._mod_menu.add_separator()
        self._mod_menu.add_command(label="💀  Unload module (FreeLibrary)",
                                    command=self._mod_kill)
        self._mod_menu.add_separator()
        self._mod_menu.add_command(label="✕  Remove from list",
                                    command=self._mod_remove_row)
        self._mt.bind("<Button-3>", self._mod_ctx_menu)

    def _mod_ctx_menu(self, event: tk.Event) -> None:
        row = self._mt.identify_row(event.y)
        if row:
            self._mt.selection_set(row)
            self._mod_menu.tk_popup(event.x_root, event.y_root)

    def _mod_selected(self) -> Optional[tuple]:
        """Return (base_int, size_int, name, path) for the selected module row."""
        sel = self._mt.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a module first.")
            return None
        vals = self._mt.item(sel[0], "values")
        base = int(vals[0], 16)
        size = int(vals[1], 16)
        name = vals[2]
        path = vals[3]
        return base, size, name, path

    def _mod_dump(self) -> None:
        """Dump module bytes as-is from memory to a .dll file."""
        info = self._mod_selected()
        if not info:
            return
        base, size, name, _ = info
        from tkinter.filedialog import asksaveasfilename
        dest = asksaveasfilename(
            defaultextension=".dll",
            initialfile=name,
            filetypes=[("DLL / EXE", "*.dll *.exe *.sys"), ("All files", "*.*")],
            title="Dump module to file")
        if not dest:
            return
        self._set_status(f"Dumping {name} ({size:#x} bytes)…")

        def _work():
            try:
                raw = _dump_module_bytes(self._proc, base, size)
                with open(dest, "wb") as fh:
                    fh.write(raw)
                self.after(0, lambda: self._set_status(
                    f"Dumped {name} → {dest}  ({len(raw):,} bytes)"))
            except Exception as exc:
                self.after(0, lambda e=exc: (
                    messagebox.showerror("Dump failed", str(e)),
                    self._set_status(f"Dump failed: {e}")))

        threading.Thread(target=_work, daemon=True).start()

    def _mod_dump_fix(self) -> None:
        """Dump module from memory, fix PE headers, save."""
        info = self._mod_selected()
        if not info:
            return
        base, size, name, _ = info
        from tkinter.filedialog import asksaveasfilename
        dest = asksaveasfilename(
            defaultextension=".dll",
            initialfile=f"fixed_{name}",
            filetypes=[("DLL / EXE", "*.dll *.exe *.sys"), ("All files", "*.*")],
            title="Dump + fix PE headers — save to file")
        if not dest:
            return
        self._set_status(f"Dumping & fixing PE for {name}…")

        def _work():
            try:
                raw   = _dump_module_bytes(self._proc, base, size)
                fixed = _fix_pe_headers(raw)
                with open(dest, "wb") as fh:
                    fh.write(fixed)
                self.after(0, lambda: self._set_status(
                    f"Fixed PE dump of {name} → {dest}  ({len(fixed):,} bytes)"))
            except Exception as exc:
                self.after(0, lambda e=exc: (
                    messagebox.showerror("Dump/fix failed", str(e)),
                    self._set_status(f"Dump/fix failed: {e}")))

        threading.Thread(target=_work, daemon=True).start()

    def _mod_kill(self) -> None:
        """Eject the module from the target process via FreeLibrary remote thread."""
        info = self._mod_selected()
        if not info:
            return
        base, size, name, _ = info
        if not messagebox.askyesno(
                "Unload module",
                f"Unload  {name}  (base {base:#x})  from the target process?\n\n"
                "This calls FreeLibrary via a remote thread and may crash the process."):
            return

        # Need the native process handle — only available in local mode
        handle = getattr(getattr(self._proc, "_handle", None), "value",
                         getattr(self._proc, "_handle", None))
        if handle is None:
            messagebox.showwarning(
                "Not supported",
                "Module unload via FreeLibrary is only supported in 'local' mode\n"
                "(requires a direct process handle).")
            return

        self._set_status(f"Unloading {name}…")

        def _work():
            result = _remote_kill_module(handle, base)
            if result == "ok":
                self.after(0, lambda: (
                    self._set_status(f"Unloaded {name}."),
                    self._refresh_modules()))
            else:
                self.after(0, lambda r=result: (
                    messagebox.showerror("Unload failed", r),
                    self._set_status(f"Unload failed: {r}")))

        threading.Thread(target=_work, daemon=True).start()

    def _mod_remove_row(self) -> None:
        """Remove the selected row from the list display (does not affect the process)."""
        sel = self._mt.selection()
        if sel:
            self._mt.delete(sel[0])

    # ─ regions tab ─────────────────────────────────────────────────────────────

    def _build_regions_tab(self) -> None:
        top = ttk.Frame(self._tregions, padding=(6,6,6,0))
        top.pack(fill="x")
        ttk.Button(top, text="↺ Refresh",
                   command=self._refresh_regions).pack(side="left")

        f = ttk.Frame(self._tregions, padding=6)
        f.pack(fill="both", expand=True)

        rcols = ("start","end","size","prot","type","tag")
        self._regt = ttk.Treeview(f, columns=rcols, show="headings")
        self._regt.heading("start", text="Start")
        self._regt.heading("end",   text="End")
        self._regt.heading("size",  text="Size")
        self._regt.heading("prot",  text="Protection")
        self._regt.heading("type",  text="Type")
        self._regt.heading("tag",   text="Tag / Module")
        self._regt.column("start", width=155, anchor="e")
        self._regt.column("end",   width=155, anchor="e")
        self._regt.column("size",  width=100, anchor="e")
        self._regt.column("prot",  width=80)
        self._regt.column("type",  width=80)
        self._regt.column("tag",   width=180)
        rsby = ttk.Scrollbar(f, orient="vertical", command=self._regt.yview)
        self._regt.configure(yscrollcommand=rsby.set)
        self._regt.grid(row=0, column=0, sticky="nsew")
        rsby.grid(row=0, column=1, sticky="ns")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)

    # ══════════════════════════════════════════════════════════════════════════
    # Connection
    # ══════════════════════════════════════════════════════════════════════════

    def _do_connect(self) -> None:
        dev_type = self._dev_var.get()

        # ── Local (Windows ReadProcessMemory, no DMA) ─────────────────────────
        if dev_type == "local":
            self._set_status("Connecting (local mode)\u2026")
            self._btn_conn.config(state="disabled")

            def _local_work():
                try:
                    proxy = LocalDMAProxy()
                    proxy.connect()
                    self._dev = proxy
                    self.after(0, self._on_connected)
                except Exception as exc:
                    self.after(0, lambda e=exc: self._on_conn_fail(str(e)))

            threading.Thread(target=_local_work, daemon=True).start()
            return

        # ── Remote connection ──────────────────────────────────────────────────
        if dev_type == "remote":
            host  = self._rhost.get().strip()
            port  = self._rport.get().strip()
            token = self._rtoken.get().strip()
            if not host or not port:
                messagebox.showwarning("Remote", "Enter host and port."); return
            try:
                port_int = int(port)
            except ValueError:
                messagebox.showerror("Port", "Port must be a number."); return

            self._set_status(f"Connecting to remote {host}:{port_int}…")
            self._btn_conn.config(state="disabled")

            def _remote_work():
                try:
                    proxy = RemoteDMAProxy(host, port_int, token)
                    proxy.connect()
                    self._dev = proxy
                    self.after(0, self._on_connected)
                except Exception as exc:
                    self.after(0, lambda e=exc: self._on_conn_fail(str(e)))

            threading.Thread(target=_remote_work, daemon=True).start()
            return

        # ── Local DMA connection ───────────────────────────────────────────────
        if not HAS_DMA:
            messagebox.showerror(
                "Missing dependency",
                f"dma_memory not importable:\n{_DMA_ERR}\n\npip install memprocfs\n\n"
                f"Tip: select device 'remote' to connect to a server that has it.")
            return

        self._set_status(f"Connecting to {dev_type}…")
        self._btn_conn.config(state="disabled")

        def _work():
            try:
                dev = DMADevice(dev_type)
                dev.connect()
                self._dev = dev
                self.after(0, self._on_connected)
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_conn_fail(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _on_connected(self) -> None:
        self._lbl_conn.config(text="●  Connected", fg=C["green"])
        self._btn_conn.config(state="disabled")
        self._btn_disc.config(state="normal")
        self._set_status(f"Connected to {self._dev_var.get()}")
        self._refresh_procs()

    def _on_conn_fail(self, err: str) -> None:
        self._btn_conn.config(state="normal")
        self._lbl_conn.config(text="●  Error", fg=C["red"])
        self._set_status(f"Connect failed: {err}")
        messagebox.showerror("Connection failed", err)

    def _do_disconnect(self) -> None:
        # thaw everything
        for e in self._addrs:
            e.thaw()
        if self._dev:
            try: self._dev.disconnect()
            except Exception: pass
        self._dev = self._proc = self._scanner = self._results = None
        self._lbl_conn.config(text="●  Not connected", fg=C["red"])
        self._lbl_proc.config(text="")
        self._btn_conn.config(state="normal")
        self._btn_disc.config(state="disabled")
        self._set_status("Disconnected.")

    # ══════════════════════════════════════════════════════════════════════════
    # Process list
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_procs(self) -> None:
        if not self._dev:
            return
        self._set_status("Loading process list…")

        def _work():
            try:
                procs = self._dev.list_processes()
                self.after(0, lambda: self._load_procs(procs))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Process list error: {e}"))

        threading.Thread(target=_work, daemon=True).start()

    def _load_procs(self, procs: List[Dict]) -> None:
        self._procs = procs
        self._filter_procs()
        self._set_status(f"{len(procs)} processes.")

    def _filter_procs(self) -> None:
        filt = self._pfilt.get().lower()
        self._pt.delete(*self._pt.get_children())
        for p in self._procs:
            if filt and filt not in p["name"].lower():
                continue
            self._pt.insert("", "end", values=(p["pid"], p["name"]))

    # ══════════════════════════════════════════════════════════════════════════
    # Attach
    # ══════════════════════════════════════════════════════════════════════════

    def _do_attach(self) -> None:
        if not self._dev:
            messagebox.showwarning("Not connected", "Connect first.")
            return
        sel = self._pt.selection()
        if not sel:
            return
        pid, name = self._pt.item(sel[0], "values")
        pid = int(pid)
        self._set_status(f"Attaching to {name} (PID {pid})…")

        def _work():
            try:
                proc    = self._dev.get_process(pid)
                scanner = proc.scanner()
                self.after(0, lambda: self._on_attached(proc, scanner))
            except Exception as exc:
                self.after(0, lambda e=exc: self._set_status(f"Attach failed: {e}"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_attached(self, proc: Any, scanner: Any) -> None:
        self._proc    = proc
        self._scanner = scanner
        self._results = None
        self._btn_next.config(state="disabled")
        self._lbl_proc.config(
            text=f"   ⚓  {proc.name}  PID {proc.pid}",
            fg=C["green"])
        self._set_status(f"Attached to {proc.name} (PID {proc.pid})")
        self._refresh_modules()
        self._refresh_regions()
        self._start_live_refresh()

    # ══════════════════════════════════════════════════════════════════════════
    # Scanning
    # ══════════════════════════════════════════════════════════════════════════

    def _need_proc(self) -> bool:
        if not self._proc or not self._scanner:
            messagebox.showwarning("No process", "Attach to a process first.")
            return False
        return True

    def _do_first_scan(self) -> None:
        if not self._need_proc():
            return
        val_str  = self._sval.get().strip()
        type_str = self._stype.get()
        mode_str = self._smode.get()
        val2_str = self._sval2.get().strip()

        try:
            dt = DataType(type_str)
        except ValueError:
            messagebox.showerror("Type", f"Unknown type: {type_str}"); return

        mode_map = {
            "Exact":              ScanType.EXACT,
            "Range":              ScanType.RANGE,
            "Unknown / First Scan": ScanType.UNKNOWN,
            "Increased":          ScanType.INCREASED,
            "Decreased":          ScanType.DECREASED,
            "Changed":            ScanType.CHANGED,
            "Unchanged":          ScanType.UNCHANGED,
        }
        st = mode_map.get(mode_str, ScanType.EXACT)

        if st != ScanType.UNKNOWN and not val_str:
            messagebox.showwarning("Value", "Enter a value to scan for."); return

        try:
            val  = _parse_val(val_str,  dt) if val_str  else 0
            val2 = _parse_val(val2_str, dt) if val2_str else None
        except Exception as exc:
            messagebox.showerror("Parse error", str(exc)); return

        self._rdtype = dt
        self._run_scan(val, dt, st, val2, first=True)

    def _do_next_scan(self) -> None:
        if not self._need_proc() or self._results is None:
            return
        val_str  = self._sval.get().strip()
        mode_str = self._smode.get()
        dt       = self._rdtype

        mode_map = {
            "Exact":     ScanType.EXACT,
            "Range":     ScanType.RANGE,
            "Increased": ScanType.INCREASED,
            "Decreased": ScanType.DECREASED,
            "Changed":   ScanType.CHANGED,
            "Unchanged": ScanType.UNCHANGED,
        }
        st = mode_map.get(mode_str, ScanType.EXACT)

        val = None
        if st in (ScanType.EXACT, ScanType.RANGE):
            if not val_str:
                messagebox.showwarning("Value", "Enter a value."); return
            try:
                val = _parse_val(val_str, dt)
            except Exception as exc:
                messagebox.showerror("Parse error", str(exc)); return

        prev = self._results
        self._btn_first.config(state="disabled")
        self._btn_next.config(state="disabled")
        self._scan_info.config(text="⏳ Filtering…", fg=C["yellow"])

        def _work():
            try:
                t0 = time.time()
                res = self._scanner.next_scan(prev, val, st)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_scan_err(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _do_new_scan(self) -> None:
        self._results = None
        self._btn_next.config(state="disabled")
        self._scan_info.config(text="", fg=C["yellow"])
        self._rt.delete(*self._rt.get_children())
        self._res_lbl.config(text="0 results")

    def _run_scan(self, val: Any, dt: "DataType", st: "ScanType",
                  val2: Any, first: bool) -> None:
        self._btn_first.config(state="disabled")
        self._btn_next.config(state="disabled")
        self._scan_info.config(text="⏳ Scanning…", fg=C["yellow"])

        def _work():
            try:
                t0 = time.time()
                res = self._scanner.scan(val, dt, st, value2=val2)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_scan_err(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _on_scan_done(self, results: Any, elapsed: float) -> None:
        self._results = results
        n = len(results)
        self._scan_info.config(
            text=f"✔  {n:,} results in {elapsed:.2f}s", fg=C["green"])
        self._res_lbl.config(text=f"{n:,} results")
        self._btn_first.config(state="normal")
        self._btn_next.config(state="normal" if n > 0 else "disabled")
        self._populate_results(results)
        self._nb.select(self._tresults)

    def _on_scan_err(self, err: str) -> None:
        self._scan_info.config(text=f"✗  {err}", fg=C["red"])
        self._btn_first.config(state="normal")
        self._btn_next.config(state="normal" if self._results else "disabled")

    def _do_str_search(self) -> None:
        if not self._need_proc(): return
        text = self._sstr.get().strip()
        if not text:
            messagebox.showwarning("Empty", "Enter a string."); return
        enc = self._senc.get()
        dt  = DataType.STRING_UTF8 if enc == "utf8" else DataType.STRING_UTF16
        self._rdtype = dt
        self._scan_info.config(text="⏳ String search…", fg=C["yellow"])
        self._btn_first.config(state="disabled")

        def _work():
            try:
                t0  = time.time()
                res = self._scanner.search_string(text, dt)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_scan_err(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _do_aob_scan(self) -> None:
        if not self._need_proc(): return
        pattern = self._sstr.get().strip()
        if not pattern:
            messagebox.showwarning("Empty", "Enter hex bytes e.g. 48 8B ? ? 00"); return
        self._rdtype = DataType.BYTES
        self._scan_info.config(text="⏳ AoB scan…", fg=C["yellow"])
        self._btn_first.config(state="disabled")

        def _work():
            try:
                t0  = time.time()
                res = self._scanner.search_aob(pattern)
                elapsed = time.time() - t0
                self.after(0, lambda: self._on_scan_done(res, elapsed))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_scan_err(str(e)))

        threading.Thread(target=_work, daemon=True).start()

    def _do_resolve(self) -> None:
        if not self._need_proc(): return
        base_str = self._pbase.get().strip()
        offs_str = self._poffs.get().strip()
        if not base_str:
            messagebox.showwarning("Empty", "Enter a base address."); return
        try:
            base    = int(base_str, 0)
            offsets = [int(o.strip(), 16) for o in offs_str.split(",") if o.strip()]
        except ValueError as exc:
            messagebox.showerror("Parse error", str(exc)); return
        result = self._proc.resolve_pointer_chain(base, offsets)
        if result is None:
            self._plbl.config(text="null pointer encountered", fg=C["red"])
        else:
            self._plbl.config(text=f"→  0x{result:016X}", fg=C["green"])

    # ══════════════════════════════════════════════════════════════════════════
    # Results
    # ══════════════════════════════════════════════════════════════════════════

    def _populate_results(self, results: Any) -> None:
        self._rt.delete(*self._rt.get_children())
        if not self._proc or self._rdtype is None:
            return
        dt  = self._rdtype
        MAX = 2000
        for m in results._matches[:MAX]:
            try:
                raw = self._proc.read(m.address, _tsz(dt))
                val = _fmt(decode(raw, dt)) if raw else "?"
            except Exception:
                val = "?"
            self._rt.insert("", "end",
                values=(f"0x{m.address:016X}", val, dt.value))
        if len(results) > MAX:
            self._rt.insert("", "end",
                values=(f"… {len(results)-MAX:,} more results", "", ""))

    def _refresh_result_vals(self) -> None:
        if not self._proc or self._rdtype is None:
            return
        dt = self._rdtype
        for iid in self._rt.get_children():
            v = self._rt.item(iid, "values")
            if not v[0].startswith("0x"):
                continue
            try:
                addr = int(v[0], 16)
                raw  = self._proc.read(addr, _tsz(dt))
                val  = _fmt(decode(raw, dt)) if raw else "?"
                self._rt.item(iid, values=(v[0], val, v[2]))
            except Exception:
                pass

    def _edit_result(self) -> None:
        if not self._proc: return
        sel = self._rt.selection()
        if not sel: return
        v = self._rt.item(sel[0], "values")
        if not v[0].startswith("0x"): return
        addr = int(v[0], 16)
        dt   = self._rdtype
        new  = simpledialog.askstring(
            "Edit value", f"New value for {v[0]}:", parent=self)
        if new is None: return
        try:
            val = _parse_val(new, dt)
            ok  = self._proc.write(addr, encode(val, dt))
            if ok:
                self._rt.item(sel[0], values=(v[0], _fmt(val), dt.value))
                self._set_status(f"Written 0x{addr:016X} = {_fmt(val)}")
            else:
                messagebox.showerror("Write failed", f"Could not write to {v[0]}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _add_to_addr_list(self) -> None:
        sel = self._rt.selection()
        if not sel:
            messagebox.showinfo("None selected",
                "Select one or more rows in Scan Results first."); return
        dt  = self._rdtype
        added = 0
        for iid in sel:
            v = self._rt.item(iid, "values")
            if not v[0].startswith("0x"): continue
            addr = int(v[0], 16)
            if any(e.address == addr for e in self._addrs): continue
            try:
                raw = self._proc.read(addr, _tsz(dt)) if self._proc else b""
                val = decode(raw, dt) if raw else 0
            except Exception:
                val = 0
            self._addrs.append(AddressEntry(addr, val, dt))
            added += 1
        self._refresh_addr_tree()
        self._set_status(f"Added {added} address(es) to list.")

    # ── address list ────────────────────────────────────────────────────────────

    def _refresh_addr_tree(self) -> None:
        self._at.delete(*self._at.get_children())
        self._ft.delete(*self._ft.get_children())
        for e in self._addrs:
            if self._proc:
                try:
                    raw = self._proc.read(e.address, _tsz(e.dtype))
                    if raw:
                        e.value = decode(raw, e.dtype)
                except Exception:
                    pass
            fz = "❄" if e.frozen else ""
            self._at.insert("", "end",
                values=(f"0x{e.address:016X}", e.label,
                        _fmt(e.value), e.dtype.value, fz))
            if e.frozen:
                self._ft.insert("", "end",
                    values=(f"0x{e.address:016X}",
                            _fmt(e._fval), e.dtype.value))

    def _edit_addr(self) -> None:
        if not self._proc: return
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        e   = self._addrs[idx]
        new = simpledialog.askstring(
            "Edit value", f"New value for 0x{e.address:016X}:", parent=self)
        if new is None: return
        try:
            val = _parse_val(new, e.dtype)
            ok  = self._proc.write(e.address, encode(val, e.dtype))
            if ok:
                e.value = val
                if e.frozen: e._fval = val
                self._refresh_addr_tree()
            else:
                messagebox.showerror("Write failed",
                    f"Could not write to 0x{e.address:016X}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _freeze_addr(self) -> None:
        if not self._proc: return
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        self._addrs[idx].freeze(self._proc)
        self._refresh_addr_tree()

    def _thaw_addr(self) -> None:
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        self._addrs[idx].thaw()
        self._refresh_addr_tree()

    def _thaw_selected(self) -> None:
        sel = self._ft.selection()
        if not sel: return
        addr_str = self._ft.item(sel[0], "values")[0]
        addr = int(addr_str, 16)
        for e in self._addrs:
            if e.address == addr:
                e.thaw(); break
        self._refresh_addr_tree()

    def _label_addr(self) -> None:
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        e   = self._addrs[idx]
        lbl = simpledialog.askstring("Label", f"Label for 0x{e.address:016X}:",
                                     parent=self, initialvalue=e.label)
        if lbl is not None:
            e.label = lbl
            self._refresh_addr_tree()

    def _remove_addr(self) -> None:
        sel = self._at.selection()
        if not sel: return
        idx = self._at.index(sel[0])
        self._addrs[idx].thaw()
        self._addrs.pop(idx)
        self._refresh_addr_tree()

    # ══════════════════════════════════════════════════════════════════════════
    # Modules
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_modules(self) -> None:
        if not self._proc: return
        self._mt.delete(*self._mt.get_children())
        try:
            for m in sorted(self._proc.modules(), key=lambda x: x.name.lower()):
                self._mt.insert("", "end",
                    values=(f"0x{m.base:016X}", f"0x{m.size:08X}",
                            m.name, m.path))
        except Exception as exc:
            self._set_status(f"Modules error: {exc}")

    # ══════════════════════════════════════════════════════════════════════════
    # Regions
    # ══════════════════════════════════════════════════════════════════════════

    def _refresh_regions(self) -> None:
        if not self._proc: return
        self._regt.delete(*self._regt.get_children())
        try:
            for r in self._proc.memory_regions():
                self._regt.insert("", "end",
                    values=(f"0x{r['va_start']:016X}",
                            f"0x{r['va_end']:016X}",
                            f"0x{r['size']:X}",
                            r.get("protection",""),
                            r.get("type",""),
                            r.get("tag","")))
        except Exception as exc:
            self._set_status(f"Regions error: {exc}")

    # ══════════════════════════════════════════════════════════════════════════
    # Live address-list refresh
    # ══════════════════════════════════════════════════════════════════════════

    def _start_live_refresh(self) -> None:
        if self._live_running:
            return
        self._live_running = True

        def _loop():
            while self._live_running and self._proc:
                self.after(0, self._refresh_addr_tree)
                time.sleep(_LIVE_DELAY)

        threading.Thread(target=_loop, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, msg: str) -> None:
        self._status.set(msg)

    def destroy(self) -> None:
        self._live_running = False
        for e in self._addrs:
            e.thaw()
        super().destroy()


# ── entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    # Allow startup even without dma_memory — remote device works without it.
    # The error is shown only when a local device is selected and Connect is clicked.
    app = MemEditApp()
    app.mainloop()


if __name__ == "__main__":
    main()
