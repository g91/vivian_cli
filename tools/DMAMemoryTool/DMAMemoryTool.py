"""
DMAMemoryTool — Vivian CLI interface for the dma_memory library.

Provides memory scanning via PCILeech FPGA DMA cards (75T, 35T, ScreamerM2, etc.)
directly from the Vivian CLI. Supports exact/range/changed value scans, string
search, AoB pattern scan, pointer resolution, and value freezing.

Requires: pip install memprocfs numpy
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "DMAMemory"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "DMAMemory operation. One of:\n"
                "- 'connect [device]'              — Connect to DMA card (default: fpga)\n"
                "- 'disconnect'                     — Disconnect from DMA card\n"
                "- 'list_processes'                 — List all running processes\n"
                "- 'ps [filter]'                    — List/search processes (case-insensitive filter)\n"
                "- 'attach <name_or_pid>'           — Attach to a process\n"
                "- 'modules'                        — List modules of attached process\n"
                "- 'regions'                        — List memory regions\n"
                "- 'read <addr> <type> [count]'     — Read value(s) from address\n"
                "- 'write <addr> <type> <value>'    — Write value to address\n"
                "- 'scan <value> <type>'            — First scan (exact match)\n"
                "- 'scan_range <min> <max> <type>'  — Scan for value in range\n"
                "- 'scan_unknown <type>'            — Scan all addresses (first unknown scan)\n"
                "- 'next_scan <value>'              — Narrow previous scan (exact)\n"
                "- 'next_changed'                   — Narrow: keep changed values\n"
                "- 'next_unchanged'                 — Narrow: keep unchanged values\n"
                "- 'next_increased'                 — Narrow: keep increased values\n"
                "- 'next_decreased'                 — Narrow: keep decreased values\n"
                "- 'results [limit]'                — Show current scan results\n"
                "- 'results_export <path>'          — Export results to CSV\n"
                "- 'freeze <addr> <type> <value>'   — Lock a value at address\n"
                "- 'thaw <addr>'                    — Stop freezing an address\n"
                "- 'thaw_all'                       — Stop all frozen addresses\n"
                "- 'search_string <text> [utf8|utf16]' — Search for a string\n"
                "- 'search_aob <pattern>'           — AoB scan: '48 8B ? ? 00'\n"
                "- 'pointers_to <addr>'             — Find pointers pointing to address\n"
                "- 'resolve_chain <base> <off1,off2,...>' — Follow pointer chain\n"
                "- 'check_deps'                     — Check required packages"
            ),
        },
        "process": {
            "type": "string",
            "description": "Process name or PID to attach to.",
        },
        "address": {
            "type": "string",
            "description": "Memory address as hex string (e.g. '0x1A2B3C4D') or decimal.",
        },
        "value": {
            "type": "string",
            "description": "Value for scan/write/freeze operations.",
        },
        "data_type": {
            "type": "string",
            "description": "Data type: int8/int16/int32/int64/uint8/uint16/uint32/uint64/float/double/string_utf8/string_utf16/bytes",
            "default": "int32",
        },
        "pattern": {
            "type": "string",
            "description": "AoB pattern with optional '?' wildcards: '48 8B 05 ? ? ? ?'",
        },
        "limit": {
            "type": "integer",
            "description": "Max results to display (default: 50).",
            "default": 50,
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string"},
        "addresses": {"type": "array"},
        "count": {"type": "integer"},
        "value": {},
        "summary": {"type": "string"},
    },
}

# ── Session state ─────────────────────────────────────────────────────────────
_session: Dict[str, Any] = {
    "device": None,
    "process": None,
    "scanner": None,
    "scan_results": None,
    "scan_type": None,
    "frozen": {},      # addr -> FrozenAddress
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_addr(s: str) -> int:
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    return int(s)


def _parse_type(s: str):
    from .dma_memory.types import DataType
    mapping = {
        "int8": DataType.INT8, "int16": DataType.INT16,
        "int32": DataType.INT32, "int64": DataType.INT64,
        "uint8": DataType.UINT8, "uint16": DataType.UINT16,
        "uint32": DataType.UINT32, "uint64": DataType.UINT64,
        "float": DataType.FLOAT, "double": DataType.DOUBLE,
        "string_utf8": DataType.STRING_UTF8, "string": DataType.STRING_UTF16,
        "string_utf16": DataType.STRING_UTF16, "bytes": DataType.BYTES,
        "aob": DataType.BYTES,
    }
    key = s.strip().lower()
    if key not in mapping:
        raise ValueError(f"Unknown type '{s}'. Valid: {', '.join(mapping)}")
    return mapping[key]


def _parse_value(s: str, data_type) -> Any:
    from .dma_memory.types import DataType
    if data_type in (DataType.FLOAT, DataType.DOUBLE):
        return float(s)
    if data_type in (DataType.STRING_UTF8, DataType.STRING_UTF16):
        return s
    if data_type == DataType.BYTES:
        return s  # AoB pattern string
    return int(s, 16) if s.startswith("0x") else int(s)


def _check_attached() -> Optional[str]:
    if _session["process"] is None:
        return "Not attached to a process. Run 'attach <name_or_pid>' first."
    return None


# ── Main dispatch ─────────────────────────────────────────────────────────────

async def call(args: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    cmd_raw = str(args.get("command", "")).strip()
    parts = cmd_raw.split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    # Lazy imports
    try:
        from .dma_memory import DMADevice, DataType, ScanType
        from .dma_memory.types import format_value
    except ImportError as e:
        return {"result": f"Import error: {e}. Run check_deps."}

    # ── connect ───────────────────────────────────────────────────────────────
    if cmd == "connect":
        device_type = rest or "fpga"
        try:
            dev = DMADevice(device_type)
            dev.connect()
            _session["device"] = dev
            return {
                "result": f"Connected to DMA device: {device_type}",
                "summary": f"Device type: {device_type}\nReady. Use 'list_processes' to see running processes.",
            }
        except Exception as exc:
            return {"result": f"Connection failed: {exc}"}

    # ── disconnect ────────────────────────────────────────────────────────────
    if cmd == "disconnect":
        dev = _session.get("device")
        if dev:
            dev.disconnect()
            _session.update({"device": None, "process": None, "scanner": None, "scan_results": None})
        return {"result": "Disconnected."}

    # ── list_processes / ps ───────────────────────────────────────────────────
    if cmd in ("list_processes", "ps"):
        dev = _session.get("device")
        if not dev:
            return {"result": "Not connected. Run 'connect' first."}
        procs = dev.list_processes()
        name_filter = rest.lower() if rest else ""
        if name_filter:
            procs = [p for p in procs if name_filter in p["name"].lower()]
        lines = [f"{'PID':>8}  {'PPID':>8}  {'Name':<30}  Path"]
        lines.append("-" * 82)
        for p in procs:
            lines.append(
                f"{p['pid']:>8}  {p.get('ppid', 0):>8}  {p['name']:<30}  {p.get('path','')[:34]}"
            )
        header = f"Processes: {len(procs)}"
        if name_filter:
            header += f"  (filter: '{name_filter}')"
        return {"result": header + "\n" + "\n".join(lines), "count": len(procs)}

    # ── attach ────────────────────────────────────────────────────────────────
    if cmd == "attach":
        target = rest or args.get("process", "")
        if not target:
            return {"result": "Usage: attach <process_name_or_pid>"}
        dev = _session.get("device")
        if not dev:
            return {"result": "Not connected. Run 'connect' first."}
        try:
            name_or_pid = int(target) if target.isdigit() else target
            proc = dev.get_process(name_or_pid)
            _session["process"] = proc
            _session["scanner"] = proc.scanner()
            _session["scan_results"] = None
            mods = proc.modules()
            base = proc.base_address
            return {
                "result": f"Attached to {proc.name} (PID {proc.pid})",
                "summary": (
                    f"Process : {proc.name}  PID={proc.pid}\n"
                    f"Base    : 0x{base:016X}\n"
                    f"Modules : {len(mods)}"
                ),
            }
        except Exception as exc:
            return {"result": f"Attach failed: {exc}"}

    # ── modules ───────────────────────────────────────────────────────────────
    if cmd == "modules":
        err = _check_attached()
        if err:
            return {"result": err}
        mods = _session["process"].modules()
        lines = [f"{'Base':>20}  {'Size':>10}  Name"]
        lines.append("-" * 55)
        for m in sorted(mods, key=lambda m: m.name.lower()):
            lines.append(f"0x{m.base:016X}  0x{m.size:08X}  {m.name}")
        return {"result": "\n".join(lines), "count": len(mods)}

    # ── regions ───────────────────────────────────────────────────────────────
    if cmd == "regions":
        err = _check_attached()
        if err:
            return {"result": err}
        regions = _session["process"].memory_regions()
        lines = [f"{'Start':>20}  {'End':>20}  {'Size':>12}  Type / Protection"]
        lines.append("-" * 80)
        for r in regions[:100]:
            lines.append(
                f"0x{r['va_start']:016X}  0x{r['va_end']:016X}  "
                f"0x{r['size']:010X}  {r.get('type',''):12} {r.get('protection','')}"
            )
        if len(regions) > 100:
            lines.append(f"... ({len(regions)-100} more)")
        return {"result": "\n".join(lines), "count": len(regions)}

    # ── read ──────────────────────────────────────────────────────────────────
    if cmd == "read":
        err = _check_attached()
        if err:
            return {"result": err}
        r_parts = rest.split()
        if len(r_parts) < 2:
            return {"result": "Usage: read <address> <type> [count]"}
        addr = _parse_addr(r_parts[0])
        dt = _parse_type(r_parts[1])
        count = int(r_parts[2]) if len(r_parts) > 2 else 1
        proc = _session["process"]
        results_out = []
        for i in range(count):
            off = addr + i * (type_size_safe(dt))
            raw = proc.read(off, type_size_safe(dt))
            if raw:
                from .dma_memory.types import decode
                val = decode(raw, dt)
                results_out.append(f"0x{off:016X} = {format_value(val, dt)}")
            else:
                results_out.append(f"0x{off:016X} = <unreadable>")
        return {"result": "\n".join(results_out), "count": count}

    # ── write ─────────────────────────────────────────────────────────────────
    if cmd == "write":
        err = _check_attached()
        if err:
            return {"result": err}
        w_parts = rest.split(None, 2)
        if len(w_parts) < 3:
            return {"result": "Usage: write <address> <type> <value>"}
        addr = _parse_addr(w_parts[0])
        dt = _parse_type(w_parts[1])
        val = _parse_value(w_parts[2], dt)
        from .dma_memory.types import encode
        data = encode(val, dt)
        ok = _session["process"].write(addr, data)
        return {"result": f"{'Written' if ok else 'FAILED'}: 0x{addr:016X} = {format_value(val, dt)}"}

    # ── scan ──────────────────────────────────────────────────────────────────
    if cmd == "scan":
        err = _check_attached()
        if err:
            return {"result": err}
        s_parts = rest.split()
        if len(s_parts) < 2:
            return {"result": "Usage: scan <value> <type>   e.g. scan 100.0 float"}
        val_str, type_str = s_parts[0], s_parts[1]
        dt = _parse_type(type_str)
        val = _parse_value(val_str, dt)
        t0 = time.time()
        results = _session["scanner"].scan(val, dt, ScanType.EXACT)
        elapsed = time.time() - t0
        _session["scan_results"] = results
        _session["scan_type"] = dt
        return {
            "result": f"Found {len(results)} addresses in {elapsed:.2f}s",
            "count": len(results),
            "summary": f"Scan: {format_value(val, dt)} ({type_str}) — {len(results)} results",
        }

    # ── scan_range ────────────────────────────────────────────────────────────
    if cmd == "scan_range":
        err = _check_attached()
        if err:
            return {"result": err}
        r_parts = rest.split()
        if len(r_parts) < 3:
            return {"result": "Usage: scan_range <min> <max> <type>"}
        dt = _parse_type(r_parts[2])
        lo = _parse_value(r_parts[0], dt)
        hi = _parse_value(r_parts[1], dt)
        t0 = time.time()
        results = _session["scanner"].scan(lo, dt, ScanType.RANGE, value2=hi)
        elapsed = time.time() - t0
        _session["scan_results"] = results
        _session["scan_type"] = dt
        return {
            "result": f"Found {len(results)} addresses in range [{lo}, {hi}] in {elapsed:.2f}s",
            "count": len(results),
        }

    # ── scan_unknown ──────────────────────────────────────────────────────────
    if cmd == "scan_unknown":
        err = _check_attached()
        if err:
            return {"result": err}
        dt = _parse_type(rest or args.get("data_type", "int32"))
        t0 = time.time()
        results = _session["scanner"].scan(0, dt, ScanType.UNKNOWN)
        elapsed = time.time() - t0
        _session["scan_results"] = results
        _session["scan_type"] = dt
        return {
            "result": f"Stored {len(results)} addresses in {elapsed:.2f}s (unknown first scan)",
            "count": len(results),
            "summary": "Change the value in-game, then use next_changed / next_increased / next_decreased.",
        }

    # ── next_scan + variants ──────────────────────────────────────────────────
    if cmd in ("next_scan", "next_changed", "next_unchanged", "next_increased", "next_decreased"):
        err = _check_attached()
        if err:
            return {"result": err}
        if _session["scan_results"] is None:
            return {"result": "No active scan. Run 'scan' or 'scan_unknown' first."}

        scan_type_map = {
            "next_scan":       ScanType.EXACT,
            "next_changed":    ScanType.CHANGED,
            "next_unchanged":  ScanType.UNCHANGED,
            "next_increased":  ScanType.INCREASED,
            "next_decreased":  ScanType.DECREASED,
        }
        st = scan_type_map[cmd]

        val = None
        if cmd == "next_scan":
            if not rest:
                return {"result": "Usage: next_scan <value>"}
            dt = _session["scan_type"]
            val = _parse_value(rest, dt)

        prev_count = len(_session["scan_results"])
        t0 = time.time()
        _session["scan_results"] = _session["scanner"].next_scan(
            _session["scan_results"], val, st
        )
        elapsed = time.time() - t0
        new_count = len(_session["scan_results"])
        return {
            "result": f"{prev_count} → {new_count} addresses ({elapsed:.2f}s)",
            "count": new_count,
            "summary": f"Eliminated {prev_count - new_count} addresses. {new_count} remaining.",
        }

    # ── results ───────────────────────────────────────────────────────────────
    if cmd == "results":
        if _session["scan_results"] is None:
            return {"result": "No active scan."}
        limit = int(rest) if rest.isdigit() else int(args.get("limit", 50))
        r = _session["scan_results"]
        r.print_table(limit)
        addrs = [f"0x{m.address:016X}" for m in r._matches[:limit]]
        return {
            "result": f"{len(r)} results (showing {min(len(r), limit)})",
            "addresses": addrs,
            "count": len(r),
        }

    # ── results_export ────────────────────────────────────────────────────────
    if cmd == "results_export":
        if _session["scan_results"] is None:
            return {"result": "No active scan."}
        path = rest or f"scan_results_{int(time.time())}.csv"
        out = _session["scan_results"].export_csv(path)
        return {"result": f"Exported {len(_session['scan_results'])} results to {out}"}

    # ── freeze ────────────────────────────────────────────────────────────────
    if cmd == "freeze":
        err = _check_attached()
        if err:
            return {"result": err}
        f_parts = rest.split(None, 2)
        if len(f_parts) < 3:
            return {"result": "Usage: freeze <address> <type> <value>"}
        addr = _parse_addr(f_parts[0])
        dt = _parse_type(f_parts[1])
        val = _parse_value(f_parts[2], dt)
        from .dma_memory.results import FrozenAddress
        from .dma_memory.types import encode
        fa = FrozenAddress(addr, val, dt, _session["process"])
        fa.start()
        _session["frozen"][addr] = fa
        return {
            "result": f"Freezing 0x{addr:016X} = {format_value(val, dt)} ({dt.value})",
            "summary": "Value will be written every 50ms. Use 'thaw' to stop.",
        }

    # ── thaw ──────────────────────────────────────────────────────────────────
    if cmd == "thaw":
        if not rest:
            return {"result": "Usage: thaw <address>"}
        addr = _parse_addr(rest)
        fa = _session["frozen"].pop(addr, None)
        if fa:
            fa.stop()
            return {"result": f"Unfrozen 0x{addr:016X}"}
        return {"result": f"0x{addr:016X} was not frozen."}

    if cmd == "thaw_all":
        for fa in _session["frozen"].values():
            fa.stop()
        count = len(_session["frozen"])
        _session["frozen"].clear()
        return {"result": f"Stopped {count} frozen address(es)."}

    # ── search_string ─────────────────────────────────────────────────────────
    if cmd == "search_string":
        err = _check_attached()
        if err:
            return {"result": err}
        s_parts = rest.split()
        if not s_parts:
            return {"result": "Usage: search_string <text> [utf8|utf16]"}
        text = s_parts[0]
        enc  = s_parts[1].lower() if len(s_parts) > 1 else "utf16"
        dt = DataType.STRING_UTF8 if enc == "utf8" else DataType.STRING_UTF16
        t0 = time.time()
        results = _session["scanner"].search_string(text, dt)
        elapsed = time.time() - t0
        _session["scan_results"] = results
        _session["scan_type"] = dt
        addrs = [f"0x{m.address:016X}" for m in results._matches[:50]]
        return {
            "result": f"Found {len(results)} occurrences of {text!r} ({enc}) in {elapsed:.2f}s",
            "addresses": addrs,
            "count": len(results),
        }

    # ── search_aob ────────────────────────────────────────────────────────────
    if cmd == "search_aob":
        err = _check_attached()
        if err:
            return {"result": err}
        if not rest:
            return {"result": "Usage: search_aob <pattern>  e.g. '48 8B 05 ? ? ? ?'"}
        t0 = time.time()
        results = _session["scanner"].search_aob(rest)
        elapsed = time.time() - t0
        _session["scan_results"] = results
        _session["scan_type"] = DataType.BYTES
        addrs = [f"0x{m.address:016X}" for m in results._matches[:50]]
        return {
            "result": f"Found {len(results)} AoB matches in {elapsed:.2f}s",
            "addresses": addrs,
            "count": len(results),
        }

    # ── pointers_to ───────────────────────────────────────────────────────────
    if cmd == "pointers_to":
        err = _check_attached()
        if err:
            return {"result": err}
        if not rest:
            return {"result": "Usage: pointers_to <address>"}
        addr = _parse_addr(rest)
        t0 = time.time()
        ptrs = _session["scanner"].find_pointers_to(addr)
        elapsed = time.time() - t0
        lines = [f"0x{p:016X}" for p in ptrs[:50]]
        return {
            "result": f"Found {len(ptrs)} pointer(s) to 0x{addr:016X} in {elapsed:.2f}s",
            "addresses": lines,
            "count": len(ptrs),
        }

    # ── resolve_chain ─────────────────────────────────────────────────────────
    if cmd == "resolve_chain":
        err = _check_attached()
        if err:
            return {"result": err}
        c_parts = rest.split()
        if len(c_parts) < 2:
            return {"result": "Usage: resolve_chain <base_address> <offset1,offset2,...>"}
        base = _parse_addr(c_parts[0])
        offsets = [int(o, 16) if o.startswith("0x") else int(o, 16) for o in c_parts[1].split(",")]
        final = _session["scanner"].scan_pointer_chain(base, offsets)
        if final is None:
            return {"result": "Pointer chain is invalid (null pointer encountered)."}
        return {
            "result": f"Resolved: 0x{final:016X}",
            "address": f"0x{final:016X}",
        }

    # ── check_deps ────────────────────────────────────────────────────────────
    if cmd == "check_deps":
        deps = {}
        pkg_map = {
            "memprocfs": "memprocfs",
            "numpy":     "numpy",
        }
        for mod, pkg in pkg_map.items():
            try:
                __import__(mod)
                deps[mod] = True
            except ImportError:
                deps[mod] = False

        lines = ["Dependency check:"]
        all_ok = True
        for mod, ok in deps.items():
            if not ok:
                all_ok = False
            lines.append(f"  {'OK' if ok else 'MISSING':8s}  {mod}")
        if not all_ok:
            missing = [pkg_map[m] for m, ok in deps.items() if not ok]
            lines.append(f"\nInstall: pip install {' '.join(missing)}")
            lines.append("Also download MemProcFS native binaries:")
            lines.append("  https://github.com/ufrisk/MemProcFS/releases")
        else:
            lines.append("\nAll dependencies satisfied.")
        return {"result": "\n".join(lines), "deps": deps, "all_ok": all_ok}

    # ── help ──────────────────────────────────────────────────────────────────
    return {
        "result": (
            "DMAMemory commands:\n"
            "  connect [fpga|usb3380|native|file]  — Connect to DMA card\n"
            "  disconnect                           — Disconnect\n"
            "  list_processes                       — List all processes\n"
            "  ps [filter]                          — List/search processes by name\n"
            "  attach <name|pid>                    — Attach to a process\n"
            "  modules                              — List loaded modules\n"
            "  regions                              — List memory regions\n"
            "  read <addr> <type> [count]           — Read typed value(s)\n"
            "  write <addr> <type> <value>          — Write a value\n"
            "  scan <value> <type>                  — Exact-match first scan\n"
            "  scan_range <min> <max> <type>        — Range first scan\n"
            "  scan_unknown <type>                  — Store all addresses\n"
            "  next_scan <value>                    — Narrow by exact value\n"
            "  next_changed                         — Narrow: value changed\n"
            "  next_unchanged                       — Narrow: value same\n"
            "  next_increased                       — Narrow: value went up\n"
            "  next_decreased                       — Narrow: value went down\n"
            "  results [limit]                      — Show scan results\n"
            "  results_export <path>                — Save results to CSV\n"
            "  freeze <addr> <type> <value>         — Lock value in memory\n"
            "  thaw <addr>                          — Stop freezing address\n"
            "  thaw_all                             — Stop all freezes\n"
            "  search_string <text> [utf8|utf16]    — Search for a string\n"
            "  search_aob <pattern>                 — AoB scan with ? wildcards\n"
            "  pointers_to <addr>                   — Find pointers to address\n"
            "  resolve_chain <base> <off1,off2,...> — Follow pointer chain\n"
            "  check_deps                           — Check memprocfs/numpy\n"
            "\n"
            "Supported types: int8 int16 int32 int64 uint8 uint16 uint32 uint64\n"
            "                 float double string_utf8 string_utf16 bytes\n"
            "\n"
            "Card: connect to 75T/35T via 'connect fpga'"
        )
    }


def type_size_safe(dt) -> int:
    from .dma_memory.types import type_size, DataType
    if dt in (DataType.STRING_UTF8, DataType.STRING_UTF16, DataType.BYTES):
        return 256
    return type_size(dt)


def description() -> str:
    return (
        "DMAMemory: PCILeech FPGA DMA memory scanner for 75T/35T/ScreamerM2 cards. "
        "Scans process memory for integers, floats, strings, and byte patterns. "
        "Supports exact/range/unknown/changed/increased/decreased scans, "
        "AoB pattern matching with wildcards, pointer chain resolution, and value freezing."
    )


def prompt() -> str:
    return (
        "Use DMAMemory to scan process memory via your FPGA DMA card. "
        "Start with 'connect fpga', then 'attach <game.exe>', then "
        "'scan 100 int32' to find all 32-bit addresses with value 100. "
        "Change the value in-game, then 'next_decreased' to narrow down. "
        "Use 'freeze <addr> int32 100' to lock a value."
    )
