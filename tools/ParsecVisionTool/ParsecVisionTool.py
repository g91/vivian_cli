"""
ParsecVisionTool — Real-time overlay with AI object detection, game classification,
and hotkey-triggered region capture for Windows (Parsec or any window).

Launches a transparent always-on-top overlay over the target window.
Detects moving objects, classifies them (player / enemy / NPC / building / tool /
crafting table / item / projectile), and matches against a named image database.

Hotkey (default Ctrl+Alt+S): freeze frame → drag to select a region → name it →
store in database for future recognition.

Windows requirements:
  pip install opencv-python mss pillow keyboard
  (window finding uses ctypes — no extra install needed)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOL_NAME = "ParsecVision"

INPUT_SCHEMA = {
    "type": "object",
    "required": ["command"],
    "properties": {
        "command": {
            "type": "string",
            "description": (
                "ParsecVision operation. One of:\n"
                "- 'start [window_title]' — Start the overlay (default: Parsec)\n"
                "- 'stop' — Stop the overlay\n"
                "- 'status' — Check if overlay is running\n"
                "- 'capture [path]' — Save a screenshot\n"
                "- 'set_hotkey <combo>' — Change capture hotkey (default: ctrl+alt+s)\n"
                "- 'set_process <name>' — Set process name to attach to (default: parsec.exe)\n"
                "- 'db_add <name> <image_path>' — Add a named image to the recognition DB\n"
                "- 'db_remove <name>' — Remove an object from the DB\n"
                "- 'db_list' — List all objects in the DB\n"
                "- 'db_match <image_path>' — Match an image against the DB\n"
                "- 'db_clear' — Remove all objects from the DB\n"
                "- 'configure [key value]' — View or set config (sensitivity, fps, etc.)\n"
                "- 'check_deps' — Check installed Python dependencies"
            ),
        },
        "window_title": {
            "type": "string",
            "description": "Window title substring to attach to (default: 'Parsec').",
        },
        "path": {
            "type": "string",
            "description": "File path for screenshot or db_add image.",
        },
        "name": {
            "type": "string",
            "description": "Object name/label for database operations.",
        },
        "image_path": {
            "type": "string",
            "description": "Path to an image file for db_add or db_match.",
        },
        "threshold": {
            "type": "number",
            "description": "Template-match confidence threshold (0.0-1.0, default 0.85).",
            "default": 0.85,
        },
    },
}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "result": {"type": "string"},
        "running": {"type": "boolean"},
        "summary": {"type": "string"},
        "objects": {"type": "array"},
        "db_size": {"type": "integer"},
        "screenshot_path": {"type": "string"},
    },
}

# ── Paths ─────────────────────────────────────────────────────────────────────
_DB_DIR = Path.home() / ".vivian" / "parsec_vision"
_IMAGES_DIR = _DB_DIR / "images"
_INDEX_FILE = _DB_DIR / "index.json"
_CONFIG_FILE = _DB_DIR / "config.json"
_SNAPSHOTS_DIR = _DB_DIR / "snapshots"
_OVERLAY_SCRIPT = Path(__file__).parent / "overlay.py"

# ── Session state ─────────────────────────────────────────────────────────────
_session: Dict[str, Any] = {
    "running": False,
    "window_title": "Parsec",
    "overlay_proc": None,
}

# ── Default config ────────────────────────────────────────────────────────────
_DEFAULTS: Dict[str, Any] = {
    "sensitivity": 0.85,
    "fps": 10,
    "min_contour_area": 500,
    "capture_hotkey": "ctrl+alt+s",
    "window_title": "Parsec",
    "process_name": "parsec.exe",
    "box_color": "#00FF00",
}


# ── Config / index helpers ────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    _SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def _load_config() -> Dict[str, Any]:
    _ensure_dirs()
    if _CONFIG_FILE.exists():
        try:
            return {**_DEFAULTS, **json.loads(_CONFIG_FILE.read_text())}
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save_config(cfg: Dict[str, Any]) -> None:
    _ensure_dirs()
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def _load_index() -> Dict[str, Any]:
    if _INDEX_FILE.exists():
        try:
            return json.loads(_INDEX_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_index(idx: Dict[str, Any]) -> None:
    _ensure_dirs()
    _INDEX_FILE.write_text(json.dumps(idx, indent=2))


# ── Dependency check ──────────────────────────────────────────────────────────

def _check_deps() -> Dict[str, bool]:
    deps: Dict[str, bool] = {}
    for mod in ["cv2", "numpy", "mss", "PIL", "keyboard"]:
        try:
            __import__(mod)
            deps[mod] = True
        except ImportError:
            deps[mod] = False
    try:
        import ctypes
        ctypes.windll.user32.FindWindowW(None, "")
        deps["win32_ctypes"] = True
    except Exception:
        deps["win32_ctypes"] = False
    return deps


# ── Overlay lifecycle ─────────────────────────────────────────────────────────

def _write_overlay_config(cfg: Dict[str, Any], window_title: str) -> Path:
    """Write the config JSON file consumed by overlay.py."""
    overlay_cfg = {**cfg, "window_title": window_title, "db_dir": str(_DB_DIR)}
    cfg_path = _DB_DIR / "_overlay_config.json"
    cfg_path.write_text(json.dumps(overlay_cfg, indent=2))
    return cfg_path


def _start_overlay(window_title: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not _OVERLAY_SCRIPT.exists():
        return {"result": f"overlay.py not found: {_OVERLAY_SCRIPT}", "running": False}

    cfg_path = _write_overlay_config(cfg, window_title)

    # Launch in a new console window so the user can see errors
    creation_flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    proc = subprocess.Popen(
        [sys.executable, str(_OVERLAY_SCRIPT), str(cfg_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creation_flags,
    )

    _session["running"] = True
    _session["window_title"] = window_title
    _session["overlay_proc"] = proc

    hotkey = cfg.get("capture_hotkey", "ctrl+alt+s")
    return {
        "result": "Overlay started.",
        "running": True,
        "pid": proc.pid,
        "summary": (
            f"Overlay running (PID {proc.pid})\n"
            f"  Target window  : '{window_title}'\n"
            f"  Process filter : {cfg.get('process_name', 'parsec.exe')}\n"
            f"  Capture hotkey : {hotkey.upper()}\n"
            f"    Press hotkey → drag to draw box around an object → name it → saved to DB\n"
            f"  ESC            : cancel capture mode / close overlay\n"
            f"  DB location    : {_DB_DIR}"
        ),
    }


def _stop_overlay() -> Dict[str, Any]:
    proc = _session.get("overlay_proc")
    if proc is None or not _session.get("running"):
        return {"result": "Overlay is not running.", "running": False}
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    _session["running"] = False
    _session["overlay_proc"] = None
    return {"result": "Overlay stopped.", "running": False}


def _overlay_status() -> Dict[str, Any]:
    proc = _session.get("overlay_proc")
    if proc is None:
        return {"running": False, "result": "Overlay has not been started in this session."}
    ret = proc.poll()
    if ret is not None:
        _session["running"] = False
        return {"running": False, "result": f"Overlay has exited (code {ret})."}
    idx = _load_index()
    cfg = _load_config()
    hotkey = cfg.get("capture_hotkey", "ctrl+alt+s")
    return {
        "running": True,
        "result": "Overlay is running.",
        "pid": proc.pid,
        "window_title": _session.get("window_title"),
        "db_size": len(idx),
        "hotkey": hotkey,
        "summary": (
            f"Running  PID={proc.pid}  |  Window='{_session.get('window_title')}'  |  "
            f"DB objects={len(idx)}  |  Hotkey={hotkey.upper()}"
        ),
    }


# ── Database operations ───────────────────────────────────────────────────────

def _db_add(name: str, image_path: str) -> Dict[str, Any]:
    _ensure_dirs()
    src = Path(image_path)
    if not src.exists():
        return {"result": f"Image not found: {image_path}", "success": False}

    ext = src.suffix or ".png"
    filename = f"{name}{ext}"
    dest = _IMAGES_DIR / filename
    counter = 1
    while dest.exists():
        filename = f"{name}_{counter}{ext}"
        dest = _IMAGES_DIR / filename
        counter += 1

    shutil.copy2(src, dest)
    file_hash = hashlib.sha256(dest.read_bytes()).hexdigest()

    idx = _load_index()
    idx[name] = {"filename": filename, "hash": file_hash, "added": time.time(), "source": "manual"}
    _save_index(idx)
    return {"result": f"Added '{name}' to database.", "success": True, "filename": filename, "db_size": len(idx)}


def _db_remove(name: str) -> Dict[str, Any]:
    idx = _load_index()
    if name not in idx:
        return {"result": f"'{name}' not found in database.", "success": False}
    info = idx.pop(name)
    img_file = _IMAGES_DIR / info.get("filename", "")
    if img_file.exists():
        img_file.unlink()
    _save_index(idx)
    return {"result": f"Removed '{name}' from database.", "success": True, "db_size": len(idx)}


def _db_list() -> Dict[str, Any]:
    idx = _load_index()
    if not idx:
        return {"result": "Database is empty. Use db_add or press the hotkey in the overlay to add objects.", "db_size": 0, "items": []}
    items = []
    for name, info in idx.items():
        img_file = _IMAGES_DIR / info.get("filename", "")
        items.append({"name": name, "filename": info.get("filename"), "exists": img_file.exists()})
    lines = [f"Database ({len(idx)} objects):"]
    for item in items:
        ok = "OK" if item["exists"] else "MISSING"
        lines.append(f"  [{ok}] {item['name']}  —  {item['filename']}")
    return {"result": "\n".join(lines), "db_size": len(idx), "items": items}


def _db_clear() -> Dict[str, Any]:
    idx = _load_index()
    count = len(idx)
    for info in idx.values():
        img_file = _IMAGES_DIR / info.get("filename", "")
        if img_file.exists():
            try:
                img_file.unlink()
            except Exception:
                pass
    _save_index({})
    return {"result": f"Cleared {count} objects from database.", "db_size": 0}


def _db_match(image_path: str, threshold: float) -> Dict[str, Any]:
    try:
        import cv2
    except ImportError:
        return {"result": "opencv-python not installed. Run: pip install opencv-python", "matches": []}

    src = Path(image_path)
    if not src.exists():
        return {"result": f"Image not found: {image_path}", "matches": []}

    frame = cv2.imread(str(src))
    if frame is None:
        return {"result": "Could not read image.", "matches": []}

    idx = _load_index()
    if not idx:
        return {"result": "Database is empty.", "matches": []}

    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    matches: List[Dict[str, Any]] = []

    for name, info in idx.items():
        tpl_path = _IMAGES_DIR / info.get("filename", "")
        if not tpl_path.exists():
            continue
        tpl = cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            continue
        th, tw = tpl.shape[:2]
        if th > frame_gray.shape[0] or tw > frame_gray.shape[1]:
            continue
        try:
            res = cv2.matchTemplate(frame_gray, tpl, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(res)
            if mv >= threshold:
                matches.append({"name": name, "confidence": round(float(mv), 3), "x": ml[0], "y": ml[1], "w": tw, "h": th})
        except Exception:
            pass

    matches.sort(key=lambda m: m["confidence"], reverse=True)
    if matches:
        top = matches[0]
        return {"result": f"Best match: '{top['name']}' ({top['confidence']:.1%})", "matches": matches}
    return {"result": "No matches found above threshold.", "matches": []}


# ── Snapshot capture ──────────────────────────────────────────────────────────

def _capture_snapshot(out_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        from mss import mss as _mss
        import numpy as np
        try:
            from PIL import Image
            has_pil = True
        except ImportError:
            import cv2
            has_pil = False
    except ImportError:
        return {"result": "mss not installed. Run: pip install mss", "screenshot_path": None}

    _ensure_dirs()
    if out_path is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = str(_SNAPSHOTS_DIR / f"snapshot_{ts}.png")

    try:
        with _mss() as sct:
            raw = sct.grab(sct.monitors[0])
            if has_pil:
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                img.save(out_path)
            else:
                frame = np.array(raw)
                cv2.imwrite(out_path, frame)
        return {"result": f"Snapshot saved: {out_path}", "screenshot_path": out_path}
    except Exception as exc:
        return {"result": f"Capture failed: {exc}", "screenshot_path": None}


# ── Main dispatch ─────────────────────────────────────────────────────────────

async def call(args: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    cmd_raw = str(args.get("command", "")).strip()
    parts = cmd_raw.split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""

    cfg = _load_config()

    if cmd == "start":
        if _session.get("running"):
            proc = _session.get("overlay_proc")
            if proc and proc.poll() is None:
                return {"result": "Overlay is already running.", "running": True}
        window_title = rest or args.get("window_title", cfg.get("window_title", "Parsec"))
        return _start_overlay(window_title, cfg)

    if cmd == "stop":
        return _stop_overlay()

    if cmd == "status":
        return _overlay_status()

    if cmd == "capture":
        out_path = rest or args.get("path")
        return _capture_snapshot(out_path)

    if cmd == "set_hotkey":
        if not rest:
            return {"result": "Usage: set_hotkey <combo>  e.g.  ctrl+alt+s  or  ctrl+shift+f12"}
        cfg["capture_hotkey"] = rest
        _save_config(cfg)
        return {"result": f"Hotkey set to: {rest.upper()}", "summary": "Restart the overlay for the new hotkey to take effect."}

    if cmd == "set_process":
        if not rest:
            return {"result": "Usage: set_process <process.exe>  e.g.  parsec.exe"}
        cfg["process_name"] = rest
        _save_config(cfg)
        return {"result": f"Process name set to: {rest}"}

    if cmd == "configure":
        sub = rest.split(None, 1)
        if len(sub) < 2:
            lines = [f"Current config ({_CONFIG_FILE}):"]
            for k, v in cfg.items():
                lines.append(f"  {k} = {v!r}")
            return {"result": "\n".join(lines)}
        key, val_str = sub[0], sub[1].strip()
        try:
            val: Any = float(val_str) if "." in val_str else int(val_str)
        except ValueError:
            val = val_str
        cfg[key] = val
        _save_config(cfg)
        return {"result": f"Set {key} = {val!r}"}

    if cmd == "db_add":
        sub = rest.split(None, 1)
        if len(sub) < 2:
            name = args.get("name", "")
            image_path = args.get("image_path", args.get("path", ""))
        else:
            name, image_path = sub[0], sub[1]
        if not name or not image_path:
            return {"result": "Usage: db_add <name> <image_path>"}
        return _db_add(name, image_path)

    if cmd == "db_remove":
        name = rest or args.get("name", "")
        if not name:
            return {"result": "Usage: db_remove <name>"}
        return _db_remove(name)

    if cmd == "db_list":
        return _db_list()

    if cmd == "db_match":
        image_path = rest or args.get("image_path", args.get("path", ""))
        threshold = float(args.get("threshold", cfg.get("sensitivity", 0.85)))
        if not image_path:
            return {"result": "Usage: db_match <image_path>"}
        return _db_match(image_path, threshold)

    if cmd == "db_clear":
        return _db_clear()

    if cmd == "check_deps":
        deps = _check_deps()
        pkg_map = {"cv2": "opencv-python", "numpy": "numpy", "mss": "mss",
                   "PIL": "Pillow", "keyboard": "keyboard", "win32_ctypes": "(built-in ctypes)"}
        lines = ["Dependency check:"]
        all_ok = True
        for mod, pkg in pkg_map.items():
            ok = deps.get(mod, False)
            if not ok:
                all_ok = False
            lines.append(f"  {'OK' if ok else 'MISSING':8s}  {mod:20s}  install: {pkg}")
        if not all_ok:
            missing_pkgs = [pkg_map[m] for m, ok in deps.items() if not ok and pkg_map.get(m) != "(built-in ctypes)"]
            lines.append(f"\nInstall: pip install {' '.join(missing_pkgs)}")
        else:
            lines.append("\nAll dependencies satisfied.")
        return {"result": "\n".join(lines), "deps": deps, "all_ok": all_ok}

    return {
        "result": (
            "ParsecVision commands:\n"
            "  start [window_title]   — Launch overlay (attaches to Parsec by default)\n"
            "  stop                   — Stop overlay\n"
            "  status                 — Check status + DB size\n"
            "  capture [path]         — Save screenshot\n"
            "  set_hotkey <combo>     — Change the capture hotkey (e.g. ctrl+alt+s)\n"
            "  set_process <name.exe> — Set which process to attach to\n"
            "  configure [key val]    — View / change settings\n"
            "  db_add <name> <path>   — Add image to recognition database\n"
            "  db_remove <name>       — Remove image from database\n"
            "  db_list                — List all named objects\n"
            "  db_match <path>        — Match image against database\n"
            "  db_clear               — Delete entire database\n"
            "  check_deps             — Verify Python dependencies\n"
            "\n"
            f"  In-overlay hotkey: {cfg.get('capture_hotkey', 'ctrl+alt+s').upper()}\n"
            "  → Drag to select a game object → give it a name → stored for future recognition"
        )
    }


def description() -> str:
    return (
        "ParsecVision: transparent always-on-top overlay for Parsec (or any window). "
        "Detects moving game objects with bounding boxes and classifies them as "
        "player / enemy / NPC / building / tool / crafting table / item / projectile. "
        "Matches against a named image database. Ctrl+Alt+S hotkey: drag-to-select any "
        "region on screen, name it, and it will be recognized automatically in future frames."
    )


def prompt() -> str:
    return (
        "Use ParsecVision to overlay your Parsec game stream. "
        "Run 'start' to launch. The overlay auto-attaches to the Parsec process. "
        "Press Ctrl+Alt+S to enter capture mode — drag a box around any game object, "
        "type a name (player, chest, crafting table, etc.) and it will be recognized "
        "in all future frames automatically."
    )
