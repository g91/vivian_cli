"""
dma_memory.process — Process and module abstraction.

Provides typed read/write helpers (read_int32, read_float, etc.) and
a scanner() factory for spawning MemoryScanner instances.
"""
from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .scanner import MemoryScanner


class DMAModule:
    """A loaded module (DLL/EXE) inside a process."""

    def __init__(self, info: Any) -> None:
        self.name: str       = getattr(info, "name", "")
        self.base: int       = getattr(info, "base", 0)
        self.size: int       = getattr(info, "image_size", 0)
        self.path: str       = getattr(info, "fullname", "")

    @property
    def end(self) -> int:
        return self.base + self.size

    def __repr__(self) -> str:
        return f"DMAModule({self.name!r}, base=0x{self.base:X}, size=0x{self.size:X})"


class DMAProcess:
    """
    Represents a single running process accessible via DMA.

    Provides:
    - Typed reads/writes (int8/16/32/64, float, double, string, bytes)
    - Module enumeration
    - Memory region (VAD) enumeration
    - scanner() factory
    """

    def __init__(self, vmm: Any, pid: int) -> None:
        self._vmm = vmm
        self._pid = pid
        self._proc: Any = vmm.process(pid)

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def name(self) -> str:
        return getattr(self._proc, "name", "")

    @property
    def base_address(self) -> int:
        """Base address of the main EXE module."""
        mods = self.modules()
        if mods:
            main_name = self.name.lower()
            for m in mods:
                if m.name.lower() == main_name:
                    return m.base
            return mods[0].base
        return 0

    # ── Modules ───────────────────────────────────────────────────────────────

    def modules(self) -> List[DMAModule]:
        """Return all loaded modules for this process."""
        try:
            raw = self._proc.module_list()
            return [DMAModule(m) for m in raw]
        except Exception:
            return []

    def get_module(self, name: str) -> Optional[DMAModule]:
        """Find a module by name (case-insensitive)."""
        name_l = name.lower()
        for m in self.modules():
            if m.name.lower() == name_l:
                return m
        return None

    # ── Memory regions ────────────────────────────────────────────────────────

    def memory_regions(self) -> List[Dict[str, Any]]:
        """
        Return readable virtual memory regions (VAD entries).
        Each dict has: va_start, va_end, size, type, protection, tag.
        """
        try:
            regions = []
            for entry in self._proc.maps.vad():
                prot = entry.get("protection", "")
                # Skip regions without read access
                if not any(c in prot for c in ("r", "R", "-r-", "R--")):
                    # Keep entries where protection looks readable
                    if not prot or "---" in prot:
                        continue
                start = entry.get("start", 0)
                end   = entry.get("end",   0)
                if end <= start:
                    continue
                regions.append({
                    "va_start":   start,
                    "va_end":     end,
                    "size":       end - start,
                    "type":       entry.get("type", ""),
                    "protection": prot,
                    "tag":        entry.get("tag", ""),
                })
            return regions
        except Exception:
            return []

    # ── Raw read / write ──────────────────────────────────────────────────────

    def read(self, address: int, size: int) -> bytes:
        """Read raw bytes from a virtual address."""
        try:
            return bytes(self._proc.memory.read(address, size))
        except Exception:
            return b""

    def write(self, address: int, data: bytes) -> bool:
        """Write raw bytes to a virtual address. Returns True on success."""
        try:
            self._proc.memory.write(address, data)
            return True
        except Exception:
            return False

    # ── Typed reads ───────────────────────────────────────────────────────────

    def _read_fmt(self, address: int, fmt: str) -> Any:
        size = struct.calcsize(fmt)
        raw = self.read(address, size)
        if len(raw) < size:
            return None
        return struct.unpack(fmt, raw)[0]

    def read_int8(self,   addr: int) -> Optional[int]:   return self._read_fmt(addr, "<b")
    def read_int16(self,  addr: int) -> Optional[int]:   return self._read_fmt(addr, "<h")
    def read_int32(self,  addr: int) -> Optional[int]:   return self._read_fmt(addr, "<i")
    def read_int64(self,  addr: int) -> Optional[int]:   return self._read_fmt(addr, "<q")
    def read_uint8(self,  addr: int) -> Optional[int]:   return self._read_fmt(addr, "<B")
    def read_uint16(self, addr: int) -> Optional[int]:   return self._read_fmt(addr, "<H")
    def read_uint32(self, addr: int) -> Optional[int]:   return self._read_fmt(addr, "<I")
    def read_uint64(self, addr: int) -> Optional[int]:   return self._read_fmt(addr, "<Q")
    def read_float(self,  addr: int) -> Optional[float]: return self._read_fmt(addr, "<f")
    def read_double(self, addr: int) -> Optional[float]: return self._read_fmt(addr, "<d")

    def read_string_utf8(self, addr: int, max_length: int = 256) -> str:
        raw = self.read(addr, max_length)
        return raw.split(b"\x00")[0].decode("utf-8", errors="replace")

    def read_string_utf16(self, addr: int, max_length: int = 512) -> str:
        raw = self.read(addr, max_length)
        i = 0
        while i + 1 < len(raw):
            if raw[i] == 0 and raw[i + 1] == 0 and i % 2 == 0:
                break
            i += 2
        return raw[:i].decode("utf-16-le", errors="replace")

    def read_pointer(self, addr: int, is_64bit: bool = True) -> Optional[int]:
        """Read a pointer value (8 bytes for 64-bit, 4 bytes for 32-bit)."""
        return self.read_uint64(addr) if is_64bit else self.read_uint32(addr)

    def resolve_pointer_chain(self, base: int, offsets: List[int],
                               is_64bit: bool = True) -> Optional[int]:
        """
        Follow a chain of pointers.
        e.g. base=0x1A2B3C4D, offsets=[0x10, 0x50, 0x8] resolves:
            ptr1 = read_pointer(base)
            ptr2 = read_pointer(ptr1 + 0x10)
            final = ptr2 + 0x50 + 0x8  ← last offset is added, not dereferenced
        """
        ptr = base
        for offset in offsets[:-1]:
            ptr_val = self.read_pointer(ptr + offset, is_64bit)
            if ptr_val is None or ptr_val == 0:
                return None
            ptr = ptr_val
        return ptr + offsets[-1] if offsets else ptr

    # ── Typed writes ──────────────────────────────────────────────────────────

    def _write_fmt(self, address: int, fmt: str, value: Any) -> bool:
        return self.write(address, struct.pack(fmt, value))

    def write_int8(self,   addr: int, v: int)   -> bool: return self._write_fmt(addr, "<b", v)
    def write_int16(self,  addr: int, v: int)   -> bool: return self._write_fmt(addr, "<h", v)
    def write_int32(self,  addr: int, v: int)   -> bool: return self._write_fmt(addr, "<i", v)
    def write_int64(self,  addr: int, v: int)   -> bool: return self._write_fmt(addr, "<q", v)
    def write_uint8(self,  addr: int, v: int)   -> bool: return self._write_fmt(addr, "<B", v)
    def write_uint16(self, addr: int, v: int)   -> bool: return self._write_fmt(addr, "<H", v)
    def write_uint32(self, addr: int, v: int)   -> bool: return self._write_fmt(addr, "<I", v)
    def write_uint64(self, addr: int, v: int)   -> bool: return self._write_fmt(addr, "<Q", v)
    def write_float(self,  addr: int, v: float) -> bool: return self._write_fmt(addr, "<f", v)
    def write_double(self, addr: int, v: float) -> bool: return self._write_fmt(addr, "<d", v)

    # ── Scanner factory ───────────────────────────────────────────────────────

    def scanner(self) -> "MemoryScanner":
        """Create a MemoryScanner bound to this process."""
        from .scanner import MemoryScanner
        return MemoryScanner(self)

    # ── Repr ──────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"DMAProcess(pid={self._pid}, name={self.name!r})"
