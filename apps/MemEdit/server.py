#!/usr/bin/env python3
"""
MemEdit Remote API Server
=========================
Deploy on any machine that has local DMA or native memory access.
The MemEdit GUI (or any HTTP client) connects over the network to perform
memory reads, writes, and scans remotely.

Install:
    pip install fastapi uvicorn

Run examples:
    # Local-only (safe default):
    python server.py --device native --token mysecret

    # Expose to LAN (requires a token for safety):
    python server.py --device fpga --host 0.0.0.0 --port 8765 --token mysecret

    # Auto-connect the DMA device on startup:
    python server.py --device fpga --auto-connect --token mysecret

GUI connection:
    In MemEdit select device "remote", enter host/port/token and click Connect.

API docs (Swagger UI):
    http://<host>:<port>/docs
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# ── FastAPI / uvicorn ─────────────────────────────────────────────────────────
try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Header
    from pydantic import BaseModel
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# ── dma_memory (optional — server won't connect without it) ──────────────────
try:
    from dma_memory import (          # type: ignore
        DMADevice, DataType, ScanType,
    )
    from dma_memory.types import encode, decode, type_size  # type: ignore
    HAS_DMA  = True
    _DMA_ERR = ""
except ImportError as _e:
    HAS_DMA  = False
    _DMA_ERR = str(_e)


# ═══════════════════════════════════════════════════════════════════════════════
# Server state  (single session — one operator at a time)
# ═══════════════════════════════════════════════════════════════════════════════

class _State:
    device:        Optional[Any]      = None
    process:       Optional[Any]      = None
    scanner:       Optional[Any]      = None
    device_type:   str                = "fpga"
    api_token:     str                = ""
    scan_sessions: Dict[str, dict]    = {}  # token → {results, dtype, ts}
    _MAX_SESSIONS = 32

    def store_scan(self, results: Any, dtype: Any) -> str:
        token = str(uuid.uuid4())
        self.scan_sessions[token] = {
            "results": results,
            "dtype":   dtype,
            "ts":      time.time(),
        }
        # Evict oldest sessions when over limit
        if len(self.scan_sessions) > self._MAX_SESSIONS:
            oldest = sorted(self.scan_sessions.items(),
                            key=lambda x: x[1]["ts"])
            for k, _ in oldest[:len(self.scan_sessions) - self._MAX_SESSIONS]:
                del self.scan_sessions[k]
        return token

    def get_scan(self, token: str) -> dict:
        s = self.scan_sessions.get(token)
        if not s:
            raise KeyError(token)
        return s


_S = _State()

# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MemEdit Remote API",
    version="1.0.0",
    description="Remote memory editing API for MemEdit GUI.",
    docs_url="/docs",
)

# ── Auth helper ────────────────────────────────────────────────────────────────

def _check_auth(authorization: Optional[str] = None) -> None:
    if _S.api_token and authorization != f"Bearer {_S.api_token}":
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")

def _need_device() -> None:
    if not _S.device:
        raise HTTPException(status_code=409,
                            detail="Not connected to a DMA device. POST /api/connect first.")

def _need_proc() -> None:
    if not _S.process:
        raise HTTPException(status_code=409,
                            detail="Not attached to a process. POST /api/attach first.")

# ── Address / value helpers ───────────────────────────────────────────────────

def _fa(a: int) -> str:
    return f"0x{a:016X}"

def _pa(s: str) -> int:
    return int(s, 16) if s.startswith(("0x", "0X")) else int(s, 0)

_SCAN_TYPE_MAP = {
    "Exact":                "EXACT",
    "Range":                "RANGE",
    "Unknown / First Scan": "UNKNOWN",
    "Increased":            "INCREASED",
    "Decreased":            "DECREASED",
    "Changed":              "CHANGED",
    "Unchanged":            "UNCHANGED",
}

def _resolve_scan_type(s: str) -> Any:
    name = _SCAN_TYPE_MAP.get(s, s.upper())
    try:
        return getattr(ScanType, name)
    except AttributeError:
        raise HTTPException(status_code=400, detail=f"Unknown scan type: {s!r}")

def _parse_val_for_dtype(s: str, dt: Any) -> Any:
    if dt in (DataType.FLOAT, DataType.DOUBLE):
        return float(s)
    if dt in (DataType.STRING_UTF8, DataType.STRING_UTF16):
        return s
    if dt == DataType.BYTES:
        return bytes.fromhex(s.replace(" ", ""))
    return int(s, 0)

_MAX_MATCH_RESPONSE = 2000


def _matches_list(results: Any, limit: int = _MAX_MATCH_RESPONSE) -> List[dict]:
    return [{"address": _fa(m.address)} for m in results._matches[:limit]]


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

# ── status ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    return {
        "dma_available":  HAS_DMA,
        "dma_error":      _DMA_ERR if not HAS_DMA else "",
        "connected":      _S.device  is not None,
        "attached":       _S.process is not None,
        "process_name":   _S.process.name if _S.process else None,
        "process_pid":    _S.process.pid  if _S.process else None,
        "device_type":    _S.device_type,
    }

# ── device connect / disconnect ───────────────────────────────────────────────

class ConnectReq(BaseModel):
    device_type: str = "fpga"

@app.post("/api/connect")
def post_connect(req: ConnectReq,
                 authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    if not HAS_DMA:
        raise HTTPException(status_code=503,
                            detail=f"dma_memory not available on this server: {_DMA_ERR}")
    if _S.device:
        try:
            _S.device.disconnect()
        except Exception:
            pass
    try:
        dev = DMADevice(req.device_type)
        dev.connect()
        _S.device      = dev
        _S.device_type = req.device_type
        _S.process     = None
        _S.scanner     = None
        return {"ok": True, "device": req.device_type}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/disconnect")
def post_disconnect(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    if _S.device:
        try:
            _S.device.disconnect()
        except Exception:
            pass
    _S.device  = None
    _S.process = None
    _S.scanner = None
    return {"ok": True}

# ── processes ─────────────────────────────────────────────────────────────────

@app.get("/api/processes")
def get_processes(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_device()
    try:
        procs = _S.device.list_processes()
        return {"processes": [{"pid": p["pid"], "name": p["name"]} for p in procs]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── attach / detach ───────────────────────────────────────────────────────────

class AttachReq(BaseModel):
    pid: int

@app.post("/api/attach")
def post_attach(req: AttachReq,
                authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_device()
    try:
        proc    = _S.device.get_process(req.pid)
        scanner = proc.scanner()
        _S.process = proc
        _S.scanner = scanner
        _S.scan_sessions.clear()
        return {"ok": True, "name": proc.name, "pid": proc.pid}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/detach")
def post_detach(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _S.process = None
    _S.scanner = None
    _S.scan_sessions.clear()
    return {"ok": True}

# ── memory read / write ───────────────────────────────────────────────────────

class ReadReq(BaseModel):
    address: str   # hex string, e.g. "0x7FF812340000"
    size: int

@app.post("/api/memory/read")
def post_read(req: ReadReq,
              authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        raw = _S.process.read(_pa(req.address), req.size)
        return {"ok": True, "data": raw.hex() if raw else ""}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

class WriteReq(BaseModel):
    address: str   # hex string
    data:    str   # hex-encoded bytes, e.g. "3F800000"

@app.post("/api/memory/write")
def post_write(req: WriteReq,
               authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        ok = _S.process.write(_pa(req.address),
                              bytes.fromhex(req.data.replace(" ", "")))
        return {"ok": bool(ok)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── modules & regions ─────────────────────────────────────────────────────────

@app.get("/api/modules")
def get_modules(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        return {"modules": [
            {"base": _fa(m.base), "size": m.size, "name": m.name, "path": m.path}
            for m in _S.process.modules()
        ]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/regions")
def get_regions(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        return {"regions": [
            {
                "va_start":   _fa(r["va_start"]),
                "va_end":     _fa(r["va_end"]),
                "size":       r["size"],
                "protection": r.get("protection", ""),
                "type":       r.get("type", ""),
                "tag":        r.get("tag",  ""),
            }
            for r in _S.process.memory_regions()
        ]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ── scanning ──────────────────────────────────────────────────────────────────

class FirstScanReq(BaseModel):
    value:      str
    dtype:      str
    scan_type:  str = "Exact"
    value2:     Optional[str] = None

@app.post("/api/scan/first")
def post_scan_first(req: FirstScanReq,
                    authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        dt  = DataType(req.dtype)
        st  = _resolve_scan_type(req.scan_type)
        val = _parse_val_for_dtype(req.value, dt) if req.value else 0
        v2  = _parse_val_for_dtype(req.value2, dt) if req.value2 else None
        t0  = time.time()
        res = _S.scanner.scan(val, dt, st, value2=v2)
        tok = _S.store_scan(res, dt)
        return {
            "token":   tok,
            "count":   len(res),
            "elapsed": round(time.time() - t0, 3),
            "matches": _matches_list(res),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

class NextScanReq(BaseModel):
    token:      str
    value:      Optional[str] = None
    scan_type:  str = "Exact"

@app.post("/api/scan/next")
def post_scan_next(req: NextScanReq,
                   authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        session = _S.get_scan(req.token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scan token not found or expired.")
    try:
        dt   = session["dtype"]
        prev = session["results"]
        st   = _resolve_scan_type(req.scan_type)
        val  = _parse_val_for_dtype(req.value, dt) if req.value else None
        t0   = time.time()
        res  = _S.scanner.next_scan(prev, val, st)
        tok  = _S.store_scan(res, dt)
        return {
            "token":   tok,
            "count":   len(res),
            "elapsed": round(time.time() - t0, 3),
            "matches": _matches_list(res),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

class StringSearchReq(BaseModel):
    text:     str
    encoding: str = "utf16"

@app.post("/api/scan/string")
def post_scan_string(req: StringSearchReq,
                     authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        dt  = DataType.STRING_UTF8 if req.encoding == "utf8" else DataType.STRING_UTF16
        t0  = time.time()
        res = _S.scanner.search_string(req.text, dt)
        tok = _S.store_scan(res, dt)
        return {
            "token":   tok,
            "count":   len(res),
            "elapsed": round(time.time() - t0, 3),
            "matches": _matches_list(res),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

class AobScanReq(BaseModel):
    pattern: str   # e.g. "48 8B ? ? 00"

@app.post("/api/scan/aob")
def post_scan_aob(req: AobScanReq,
                  authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        t0  = time.time()
        res = _S.scanner.search_aob(req.pattern)
        tok = _S.store_scan(res, DataType.BYTES)
        return {
            "token":   tok,
            "count":   len(res),
            "elapsed": round(time.time() - t0, 3),
            "matches": _matches_list(res),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/api/scan/results")
def get_scan_results(token:  str,
                     offset: int = 0,
                     limit:  int = 2000,
                     authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    try:
        session = _S.get_scan(token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Token not found.")
    res  = session["results"]
    page = res._matches[offset:offset + limit]
    return {
        "token":   token,
        "total":   len(res),
        "offset":  offset,
        "matches": [{"address": _fa(m.address)} for m in page],
    }

# ── pointer chain resolver ────────────────────────────────────────────────────

class ResolveReq(BaseModel):
    base:    str         # hex address
    offsets: List[str]   # list of hex offsets

@app.post("/api/pointer/resolve")
def post_resolve(req: ResolveReq,
                 authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    _need_proc()
    try:
        base    = _pa(req.base)
        offsets = [int(o, 16) for o in req.offsets]
        result  = _S.process.resolve_pointer_chain(base, offsets)
        return {"result": _fa(result) if result is not None else None}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    if not HAS_FASTAPI:
        print("ERROR: fastapi and uvicorn are not installed.")
        print("       pip install fastapi uvicorn")
        sys.exit(1)

    ap = argparse.ArgumentParser(
        description="MemEdit Remote API Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--host",         default="127.0.0.1",
                    help="Bind interface (use 0.0.0.0 for LAN)")
    ap.add_argument("--port",         type=int, default=8765,
                    help="TCP port")
    ap.add_argument("--token",        default="",
                    help="Bearer token for auth (leave empty to disable auth)")
    ap.add_argument("--device",       default="fpga",
                    choices=["fpga", "usb3380", "native", "file"],
                    help="DMA device type")
    ap.add_argument("--auto-connect", action="store_true",
                    help="Connect to the DMA device automatically on startup")
    args = ap.parse_args()

    _S.api_token   = args.token
    _S.device_type = args.device

    if args.auto_connect:
        if not HAS_DMA:
            print(f"[!] WARNING: dma_memory unavailable — {_DMA_ERR}")
        else:
            try:
                dev = DMADevice(args.device)
                dev.connect()
                _S.device = dev
                print(f"[+] Auto-connected to {args.device}")
            except Exception as e:
                print(f"[-] Auto-connect failed: {e}")

    print()
    print("  MemEdit Remote API Server")
    print(f"  Listening : http://{args.host}:{args.port}")
    print(f"  Token     : {'(set)' if args.token else '(none — open access)'}")
    print(f"  Device    : {args.device}")
    print(f"  DMA avail : {HAS_DMA}")
    print(f"  Swagger   : http://{args.host}:{args.port}/docs")
    print()
    if not args.token:
        print("  WARNING: No --token set. Anyone on the network can control this server.")
        print()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
