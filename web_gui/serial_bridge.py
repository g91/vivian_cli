"""Server-side serial bridge.

Browsers that don't have Web Serial (Firefox, Safari, mobile) still need a way
to monitor an ESP32. This module opens a serial port via pyserial on the
server and exposes it through:

  GET  /api/serial/ports         list available ports
  POST /api/serial/open  {port, baud}
  GET  /api/serial/stream        SSE — bytes from the open port
  POST /api/serial/write {data}
  POST /api/serial/close

Only one port is open at a time. pyserial is loaded lazily so the web GUI
still works without it.
"""
from __future__ import annotations
import base64
import queue
import threading
import time
from typing import Optional


_serial_mod = None
_list_ports_mod = None
_import_error: Optional[str] = None


def _ensure_pyserial() -> bool:
    global _serial_mod, _list_ports_mod, _import_error
    if _serial_mod is not None:
        return True
    try:
        import serial  # type: ignore
        from serial.tools import list_ports  # type: ignore
        _serial_mod = serial
        _list_ports_mod = list_ports
        return True
    except ImportError as e:
        _import_error = (f"pyserial is not installed. Install with `pip install pyserial`, "
                         f"then reload the page. ({e})")
        return False


class _Bridge:
    """Singleton that owns the active port + reader thread."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.port = None
        self.path: Optional[str] = None
        self.baud: int = 115200
        self.subscribers: list[queue.Queue] = []
        self._reader: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # ── port lifecycle ────────────────────────────────────────────────
    def list_ports(self) -> list[dict]:
        if not _ensure_pyserial():
            return []
        out = []
        for p in _list_ports_mod.comports():
            out.append({
                "path": p.device,
                "description": p.description or "",
                "manufacturer": getattr(p, "manufacturer", "") or "",
                "vid_pid": (f"{p.vid:04x}:{p.pid:04x}" if p.vid and p.pid else ""),
            })
        return out

    def open(self, path: str, baud: int) -> dict:
        if not _ensure_pyserial():
            return {"ok": False, "error": _import_error}
        with self.lock:
            if self.port is not None:
                self._close_locked()
            try:
                self.port = _serial_mod.Serial(path, baud, timeout=0.1)
            except Exception as e:
                self.port = None
                return {"ok": False, "error": f"{type(e).__name__}: {e}"}
            self.path = path
            self.baud = baud
            self._stop.clear()
            self._reader = threading.Thread(target=self._read_loop, daemon=True,
                                            name=f"serial-{path}")
            self._reader.start()
        return {"ok": True, "port": path, "baud": baud}

    def close(self) -> dict:
        with self.lock:
            self._close_locked()
        return {"ok": True}

    def _close_locked(self) -> None:
        self._stop.set()
        if self.port is not None:
            try:
                self.port.close()
            except Exception:
                pass
        self.port = None
        self.path = None
        # Wake any subscribers so their stream ends
        for q in self.subscribers:
            q.put(None)
        self.subscribers.clear()

    def write(self, data: bytes) -> dict:
        with self.lock:
            if self.port is None:
                return {"ok": False, "error": "port is not open"}
            try:
                self.port.write(data)
            except Exception as e:
                return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        return {"ok": True, "bytes": len(data)}

    def subscribe(self) -> queue.Queue:
        """Caller polls .get() to receive bytes. ``None`` means stream end."""
        q: queue.Queue = queue.Queue()
        with self.lock:
            self.subscribers.append(q)
            if self.port is None:
                q.put(None)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def status(self) -> dict:
        return {
            "open": self.port is not None,
            "port": self.path,
            "baud": self.baud,
            "pyserial_available": _ensure_pyserial(),
            "pyserial_error": _import_error,
        }

    # ── reader thread ────────────────────────────────────────────────
    def _read_loop(self) -> None:
        port = self.port
        while not self._stop.is_set() and port is not None:
            try:
                data = port.read(4096)
            except Exception:
                break
            if not data:
                # Give other threads a beat — pyserial's timeout already throttles
                continue
            payload = base64.b64encode(data).decode("ascii")
            with self.lock:
                for q in list(self.subscribers):
                    q.put(payload)
        # On exit, signal subscribers
        with self.lock:
            for q in self.subscribers:
                q.put(None)


bridge = _Bridge()
