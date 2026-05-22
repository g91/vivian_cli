"""
dma_memory.results — Scan result management.

ScanResults holds discovered addresses and supports:
- Narrowing (next_scan)
- Re-reading current values
- Freeze/thaw (lock a value in memory)
- CSV/text export
- Iteration and indexing
"""
from __future__ import annotations

import csv
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from .types import DataType, ScanType, decode, encode, format_value, compare, type_size

if TYPE_CHECKING:
    from .process import DMAProcess


class MatchAddress:
    """A single address result from a scan."""

    __slots__ = ("address", "value", "prev_value", "data_type", "_proc")

    def __init__(self, address: int, value: Any, data_type: DataType,
                 proc: "DMAProcess", prev_value: Any = None) -> None:
        self.address    = address
        self.value      = value
        self.prev_value = prev_value
        self.data_type  = data_type
        self._proc      = proc

    def refresh(self) -> Any:
        """Re-read the current value from memory."""
        size = _read_size(self.data_type, self.value)
        raw = self._proc.read(self.address, size)
        self.prev_value = self.value
        self.value = decode(raw, self.data_type)
        return self.value

    def write(self, value: Any) -> bool:
        """Write a new value to this address."""
        data = encode(value, self.data_type)
        return self._proc.write(self.address, data)

    def freeze(self, value: Any, interval: float = 0.05) -> "FrozenAddress":
        """Continuously write value to lock it. Returns a FrozenAddress handle."""
        fa = FrozenAddress(self.address, value, self.data_type, self._proc, interval)
        fa.start()
        return fa

    def __repr__(self) -> str:
        return (
            f"MatchAddress(0x{self.address:016X}, "
            f"{format_value(self.value, self.data_type)}, {self.data_type.value})"
        )


def _read_size(dt: DataType, sample_value: Any) -> int:
    """Determine bytes to read for a DataType."""
    if dt in (DataType.STRING_UTF8, DataType.STRING_UTF16):
        return max(256, len(str(sample_value)) * 4 + 4)
    if dt == DataType.BYTES:
        return len(sample_value) if isinstance(sample_value, (bytes, bytearray)) else 16
    return type_size(dt)


class FrozenAddress:
    """Locks a value at an address by writing it repeatedly in a background thread."""

    def __init__(self, address: int, value: Any, data_type: DataType,
                 proc: "DMAProcess", interval: float = 0.05) -> None:
        self.address   = address
        self.value     = value
        self.data_type = data_type
        self._proc     = proc
        self.interval  = interval
        self._stop     = threading.Event()
        self._thread   = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        data = encode(self.value, self.data_type)
        while not self._stop.is_set():
            self._proc.write(self.address, data)
            self._stop.wait(self.interval)

    def start(self) -> "FrozenAddress":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def __enter__(self) -> "FrozenAddress":
        return self.start()

    def __exit__(self, *_: Any) -> None:
        self.stop()

    def __repr__(self) -> str:
        status = "active" if self._thread.is_alive() else "stopped"
        return f"FrozenAddress(0x{self.address:016X} = {self.value}, {status})"


class ScanResults:
    """
    A collection of addresses from a memory scan.

    Supports next_scan() to narrow down, freeze(), export, and iteration.
    """

    def __init__(self, matches: List[MatchAddress], data_type: DataType,
                 proc: "DMAProcess") -> None:
        self._matches   = matches
        self.data_type  = data_type
        self._proc      = proc
        self._frozen: List[FrozenAddress] = []

    # ── Core interface ────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._matches)

    def __iter__(self) -> Iterator[MatchAddress]:
        return iter(self._matches)

    def __getitem__(self, idx: int) -> MatchAddress:
        return self._matches[idx]

    def addresses(self) -> List[int]:
        return [m.address for m in self._matches]

    def values(self) -> List[Any]:
        return [m.value for m in self._matches]

    # ── Narrowing ─────────────────────────────────────────────────────────────

    def next_scan(
        self,
        target: Any = None,
        scan_type: ScanType = ScanType.EXACT,
        target2: Any = None,           # upper bound for RANGE
    ) -> "ScanResults":
        """
        Re-read all stored addresses and keep only those that pass the filter.

        For relative scan types (CHANGED / INCREASED / etc.) the previous
        stored value is used as the baseline — no target needed.
        """
        kept: List[MatchAddress] = []
        size = _read_size(self.data_type, self._matches[0].value if self._matches else b"")

        for m in self._matches:
            raw = self._proc.read(m.address, size)
            if not raw:
                continue
            new_val = decode(raw, self.data_type)
            if compare(new_val, m.value, target, scan_type, target2):
                kept.append(MatchAddress(m.address, new_val, self.data_type, self._proc, m.value))

        return ScanResults(kept, self.data_type, self._proc)

    def refresh(self) -> None:
        """Re-read every address and update stored values in place."""
        size = _read_size(self.data_type, self._matches[0].value if self._matches else b"")
        for m in self._matches:
            raw = self._proc.read(m.address, size)
            if raw:
                m.prev_value = m.value
                m.value = decode(raw, self.data_type)

    # ── Freeze / thaw ─────────────────────────────────────────────────────────

    def freeze_all(self, value: Any, interval: float = 0.05) -> List[FrozenAddress]:
        """Freeze every address in the results at the given value."""
        for fa in self._frozen:
            fa.stop()
        self._frozen = [
            m.freeze(value, interval) for m in self._matches
        ]
        return self._frozen

    def thaw_all(self) -> None:
        """Stop all active freezes."""
        for fa in self._frozen:
            fa.stop()
        self._frozen.clear()

    # ── Export ────────────────────────────────────────────────────────────────

    def export_csv(self, path: "str | Path") -> Path:
        """Write results to a CSV file. Returns the path."""
        out = Path(path)
        with out.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["address_hex", "address_dec", "value", "data_type"])
            for m in self._matches:
                writer.writerow([
                    f"0x{m.address:016X}",
                    m.address,
                    format_value(m.value, self.data_type),
                    self.data_type.value,
                ])
        return out

    def print_table(self, limit: int = 50) -> None:
        """Print a formatted table of results."""
        count = len(self._matches)
        shown = min(count, limit)
        print(f"{'Address':<20} {'Value':<24} {'Type'}")
        print("-" * 56)
        for m in self._matches[:shown]:
            print(
                f"0x{m.address:016X}  "
                f"{format_value(m.value, self.data_type):<24}  "
                f"{self.data_type.value}"
            )
        if count > shown:
            print(f"... ({count - shown} more results)")
        print(f"\nTotal: {count}")

    def __repr__(self) -> str:
        return f"ScanResults({len(self._matches)} addresses, type={self.data_type.value})"
