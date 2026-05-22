"""
dma_memory.device — DMA device connection manager.

Wraps memprocfs (MemProcFS / LeechCore) to connect to PCILeech-compatible
FPGA DMA cards: 75T, 35T, ScreamerM2, AC701, CW305, etc.

Install backend:
    pip install memprocfs
    # Also install MemProcFS native binaries from:
    # https://github.com/ufrisk/MemProcFS/releases
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ── Backend import ────────────────────────────────────────────────────────────
try:
    import memprocfs as _vmm_mod   # type: ignore
    Vmm = _vmm_mod.Vmm
    HAS_VMM = True
except ImportError:
    try:
        from vmmpy import Vmm      # type: ignore  (legacy fallback)
        HAS_VMM = True
    except ImportError:
        HAS_VMM = False
        Vmm = None  # type: ignore

# ── Device type constants ─────────────────────────────────────────────────────
DEVICE_FPGA     = "fpga"       # PCILeech 75T / 35T / ScreamerM2 / AC701 / CW305
DEVICE_USB3380  = "usb3380"    # USB3380 (older, slower DMA)
DEVICE_NATIVE   = "native"     # Direct kernel read (no card needed, Windows only)
DEVICE_FILE     = "file"       # Offline memory dump (.dmp / .raw)


class DMADevice:
    """
    Connection to a PCILeech FPGA DMA card (or compatible device).

    Usage:
        # Context manager (auto-disconnects)
        with DMADevice("fpga") as dma:
            proc = dma.get_process("notepad.exe")

        # Manual
        dma = DMADevice("fpga")
        dma.connect()
        ...
        dma.disconnect()

    For 75T card:
        DMADevice("fpga")                      # auto-detect
        DMADevice("fpga", ["-device", "fpga:algo=2"])   # specific algo

    For memory dump:
        DMADevice("file", ["-device", "file:///C:/dump.raw"])
    """

    def __init__(
        self,
        device_type: str = DEVICE_FPGA,
        extra_args: Optional[List[str]] = None,
    ) -> None:
        self.device_type = device_type
        self._extra_args: List[str] = extra_args or []
        self._vmm: Optional[Any] = None

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self, verbose: bool = False) -> "DMADevice":
        """Connect to the DMA device. Returns self for chaining."""
        if not HAS_VMM:
            raise ImportError(
                "memprocfs is not installed.\n"
                "  pip install memprocfs\n"
                "Also download MemProcFS native binaries:\n"
                "  https://github.com/ufrisk/MemProcFS/releases"
            )
        vmm_args = ["-device", self.device_type]
        if verbose:
            vmm_args += ["-v", "-printf"]
        vmm_args += self._extra_args
        try:
            self._vmm = Vmm(vmm_args)
        except Exception as exc:
            raise ConnectionError(
                f"Failed to connect to '{self.device_type}': {exc}\n"
                "Ensure the FPGA card is inserted, drivers loaded, and "
                "MemProcFS is in PATH."
            ) from exc
        return self

    def disconnect(self) -> None:
        """Disconnect from the DMA device."""
        if self._vmm is not None:
            try:
                self._vmm.close()
            except Exception:
                pass
            self._vmm = None

    @property
    def is_connected(self) -> bool:
        return self._vmm is not None

    @property
    def _vmm_handle(self) -> Any:
        if self._vmm is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._vmm

    # ── Process enumeration ───────────────────────────────────────────────────

    def list_processes(self) -> List[Dict[str, Any]]:
        """Return a sorted list of all running processes."""
        result = []
        for p in self._vmm_handle.process_list():
            try:
                path = p.pathuser
            except Exception:
                path = ""
            result.append({
                "pid":  p.pid,
                "ppid": getattr(p, "ppid", 0),
                "name": p.name,
                "path": path,
            })
        return sorted(result, key=lambda p: p["name"].lower())

    def get_process(self, name_or_pid: "str | int") -> "DMAProcess":
        """
        Get a process by name (substring, case-insensitive) or integer PID.

        If multiple names match, an exact match is preferred; otherwise the
        first partial match is used. Raises ProcessLookupError if none found.
        """
        from .process import DMAProcess

        if isinstance(name_or_pid, int):
            return DMAProcess(self._vmm_handle, pid=name_or_pid)

        name_lower = name_or_pid.lower()
        procs = self.list_processes()
        matches = [p for p in procs if name_lower in p["name"].lower()]
        if not matches:
            raise ProcessLookupError(
                f"No process found matching '{name_or_pid}'.\n"
                f"Running processes: {[p['name'] for p in procs]}"
            )
        exact = [p for p in matches if p["name"].lower() == name_lower]
        chosen = (exact or matches)[0]
        return DMAProcess(self._vmm_handle, pid=chosen["pid"])

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "DMADevice":
        return self.connect()

    def __exit__(self, *_: Any) -> None:
        self.disconnect()

    def __repr__(self) -> str:
        status = "connected" if self.is_connected else "disconnected"
        return f"DMADevice(type={self.device_type!r}, {status})"
