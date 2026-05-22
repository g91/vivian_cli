"""
dma_memory — PCILeech FPGA DMA memory scanning library.

Supports 75T, 35T, ScreamerM2, AC701, and any PCILeech-compatible DMA card.

Quick start:
    from dma_memory import DMADevice, DataType, ScanType

    with DMADevice("fpga") as dma:
        proc = dma.get_process("game.exe")
        scanner = proc.scanner()

        # First scan: find all float addresses equal to 100.0
        results = scanner.scan(100.0, DataType.FLOAT)

        # Narrow down after changing health to 75.0
        results = scanner.next_scan(results, 75.0)

        # Freeze the first result at 100.0
        results[0].freeze(100.0)

        # AoB (Array of Bytes) scan with wildcards
        addrs = scanner.search_aob("48 8B 05 ? ? ? ? 48 8B")

        # String search
        addrs = scanner.search_string("PlayerName")
"""

from .device import DMADevice, DEVICE_FPGA, DEVICE_USB3380, DEVICE_NATIVE, DEVICE_FILE
from .process import DMAProcess, DMAModule
from .scanner import MemoryScanner
from .results import ScanResults, FrozenAddress
from .types import DataType, ScanType

__all__ = [
    "DMADevice",
    "DMAProcess",
    "DMAModule",
    "MemoryScanner",
    "ScanResults",
    "FrozenAddress",
    "DataType",
    "ScanType",
    "DEVICE_FPGA",
    "DEVICE_USB3380",
    "DEVICE_NATIVE",
    "DEVICE_FILE",
]

__version__ = "1.0.0"
