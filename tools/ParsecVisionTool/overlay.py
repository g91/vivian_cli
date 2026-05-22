"""
ParsecVision Overlay — Standalone overlay application.

Attach to any window (Parsec or other), detect motion, draw bounding boxes,
label objects from an AI image database, and allow hotkey-triggered region
capture for naming and saving new objects.

Run:  python overlay.py <config_json_path>
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import queue
import shutil
import sys
import threading
import time
import struct
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Optional heavy deps — fail gracefully ────────────────────────────────────
try:
    import tkinter as tk
    from tkinter import simpledialog, messagebox, ttk
    HAS_TK = True
except ImportError:
    HAS_TK = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from mss import mss as _mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import keyboard as _keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

# ── Win32 helpers (pure ctypes — no pywin32 required) ────────────────────────
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002


def _find_window_by_title(title_sub: str) -> Optional[Tuple[int, int, int, int, int]]:
    """
    Enumerate all windows, find one whose title contains title_sub.
    Returns (hwnd, x, y, width, height) or None.
    """
    results = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def enum_cb(hwnd, _lparam):
        if not _user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        _user32.GetWindowTextW(hwnd, buf, 256)
        if title_sub.lower() in buf.value.lower():
            rect = ctypes.wintypes.RECT()
            _user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 50 and h > 50:
                results.append((hwnd, rect.left, rect.top, w, h))
        return True

    _user32.EnumWindows(enum_cb, 0)
    return results[0] if results else None


def _find_process_windows(proc_name: str) -> List[Tuple[int, int, int, int, int]]:
    """
    Find windows belonging to a process by name (e.g. 'parsec.exe').
    Returns list of (hwnd, x, y, width, height).
    """
    import ctypes.wintypes

    # Get PIDs matching process name via tasklist
    try:
        out = subprocess.check_output(
            ['tasklist', '/FI', f'IMAGENAME eq {proc_name}', '/FO', 'CSV', '/NH'],
            text=True, timeout=5, stderr=subprocess.DEVNULL
        )
        pids = set()
        for line in out.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    pass
    except Exception:
        pids = set()

    if not pids:
        return []

    results = []
    pid_buf = ctypes.wintypes.DWORD()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    def enum_cb(hwnd, _lparam):
        if not _user32.IsWindowVisible(hwnd):
            return True
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_buf))
        if pid_buf.value in pids:
            rect = ctypes.wintypes.RECT()
            _user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 100 and h > 100:
                results.append((hwnd, rect.left, rect.top, w, h))
        return True

    _user32.EnumWindows(enum_cb, 0)
    return results


def _set_click_through(hwnd: int, enable: bool) -> None:
    """Enable or disable click-through on a window."""
    style = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if enable:
        _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    else:
        _user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)


# ── Object category heuristics ───────────────────────────────────────────────

def _heuristic_classify(
    bbox: Dict[str, int],
    motion_speed: float,
    frame_w: int,
    frame_h: int,
) -> Tuple[str, float]:
    """Classify a detected object by size/motion/aspect heuristics."""
    bw, bh = bbox["w"], bbox["h"]
    area = bw * bh
    frame_area = frame_w * frame_h
    rel_area = area / max(frame_area, 1)
    aspect = bw / max(bh, 1)  # < 1 = taller than wide (humanoid), > 1 = wider

    if rel_area < 0.001:
        if motion_speed > 80:
            return "projectile", 0.55
        return "item", 0.45

    if rel_area < 0.008:
        if motion_speed > 30:
            return "projectile", 0.50
        if 0.5 < aspect < 2.0:
            return "item / tool", 0.50
        return "item", 0.45

    if rel_area < 0.10:
        # Fast moving = definitely a player/entity
        if motion_speed > 15:
            return "player / entity", 0.65
        # Tall & narrow = standing humanoid (NPC/player standing still)
        if aspect < 0.60:
            return "player / entity", 0.55
        # Roughly square / slightly tall = could be NPC
        if 0.60 <= aspect < 1.2:
            return "enemy / NPC", 0.50
        # Wide = inanimate object
        return "item / tool", 0.45

    if rel_area < 0.25:
        if motion_speed > 5:
            return "large entity", 0.45
        return "building / structure", 0.50

    return "terrain / large structure", 0.50


def _merge_boxes(
    boxes: List[Tuple[int, int, int, int, float]],
    expand: int = 25,
) -> List[Tuple[int, int, int, int]]:
    """
    Merge overlapping or nearby bounding boxes to eliminate fragments.

    boxes: list of (x, y, w, h, area)
    expand: pixel margin used when checking for nearness
    Returns: list of merged (x, y, w, h)
    """
    if not boxes:
        return []
    # Sort largest area first so big boxes absorb small fragments
    boxes = sorted(boxes, key=lambda b: b[4], reverse=True)
    n = len(boxes)
    used = [False] * n
    merged: List[Tuple[int, int, int, int]] = []

    for i in range(n):
        if used[i]:
            continue
        x0, y0, w0, h0, _ = boxes[i]
        rx0, ry0, rx1, ry1 = x0, y0, x0 + w0, y0 + h0
        # Expand the current box and absorb neighbours
        changed = True
        while changed:
            changed = False
            ex0, ey0, ex1, ey1 = rx0 - expand, ry0 - expand, rx1 + expand, ry1 + expand
            for j in range(i + 1, n):
                if used[j]:
                    continue
                xj, yj, wj, hj, _ = boxes[j]
                cxj, cyj = xj + wj // 2, yj + hj // 2
                if ex0 <= cxj <= ex1 and ey0 <= cyj <= ey1:
                    rx0 = min(rx0, xj)
                    ry0 = min(ry0, yj)
                    rx1 = max(rx1, xj + wj)
                    ry1 = max(ry1, yj + hj)
                    used[j] = True
                    changed = True
        used[i] = True
        merged.append((rx0, ry0, rx1 - rx0, ry1 - ry0))

    return merged


# ── Image database helpers ───────────────────────────────────────────────────

def _load_index(db_dir: Path) -> Dict[str, Any]:
    idx = db_dir / "index.json"
    if idx.exists():
        try:
            return json.loads(idx.read_text())
        except Exception:
            return {}
    return {}


def _save_index(db_dir: Path, index: Dict[str, Any]) -> None:
    (db_dir / "index.json").write_text(json.dumps(index, indent=2))


def _match_db(frame_gray: Any, index: Dict[str, Any], images_dir: Path, threshold: float) -> List[Dict[str, Any]]:
    """Template match all DB images against a grayscale frame."""
    if not HAS_CV2:
        return []
    matches = []
    fh, fw = frame_gray.shape[:2]
    for name, info in index.items():
        tpl_path = images_dir / info.get("filename", "")
        if not tpl_path.exists():
            continue
        tpl = cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE)
        if tpl is None:
            continue
        th, tw = tpl.shape[:2]
        best_val, best_loc, best_scale = 0.0, (0, 0), 1.0
        for scale in [0.5, 0.75, 1.0, 1.25, 1.5]:
            sw, sh = int(tw * scale), int(th * scale)
            if sw < 8 or sh < 8 or sw > fw or sh > fh:
                continue
            try:
                resized = cv2.resize(tpl, (sw, sh))
                res = cv2.matchTemplate(frame_gray, resized, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > best_val:
                    best_val, best_loc, best_scale = mv, ml, scale
            except Exception:
                pass
        if best_val >= threshold:
            matches.append({
                "name": name,
                "confidence": round(float(best_val), 3),
                "x": best_loc[0], "y": best_loc[1],
                "w": int(tw * best_scale), "h": int(th * best_scale),
            })
    matches.sort(key=lambda m: m["confidence"], reverse=True)
    return matches


# ── Detection thread ─────────────────────────────────────────────────────────

class DetectionThread(threading.Thread):
    """
    Background thread: captures frames, detects foreground entities, matches DB.

    Uses MOG2 background subtraction (learns background over ~150 frames) combined
    with classic frame differencing to detect BOTH moving AND stationary entities.
    Nearby/overlapping contours are merged before classification.
    A configurable self-zone excludes the local player's own character.
    """

    def __init__(self, target_rect: Tuple[int, int, int, int], config: Dict[str, Any],
                 db_dir: Path, result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.tx, self.ty, self.tw, self.th = target_rect
        self.config = config
        self.db_dir = db_dir
        self.images_dir = db_dir / "images"
        self.result_queue = result_queue
        self._stop_event = threading.Event()
        self._prev_gray = None
        self._frame_count = 0

    def stop(self):
        self._stop_event.set()

    def run(self):
        if not HAS_MSS or not HAS_CV2:
            return

        sensitivity = float(self.config.get("sensitivity", 0.85))
        min_area = int(self.config.get("min_contour_area", 600))
        fps = int(self.config.get("fps", 10))
        interval = 1.0 / fps
        blur_k = 21

        # ── MOG2 background subtractor ─────────────────────────────────────
        # history=150: adapts background over ~15s @ 10fps
        # varThreshold=40: lower = more sensitive (detects slow-moving/still entities)
        # detectShadows=False: skip shadow detection for speed
        bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=150, varThreshold=40, detectShadows=False
        )

        # ── Self-exclusion zone ────────────────────────────────────────────
        # Prevents boxing the local player's own character.
        # Defaults cover the bottom-center region typical of 3rd-person games.
        sz = self.config.get("self_zone", {})
        sz_xf  = float(sz.get("x_frac",  0.20))  # left edge as fraction of width
        sz_yf  = float(sz.get("y_frac",  0.50))  # top edge as fraction of height
        sz_wf  = float(sz.get("w_frac",  0.60))  # zone width as fraction
        sz_hf  = float(sz.get("h_frac",  0.50))  # zone height as fraction
        sz_en  = bool(sz.get("enabled", True))

        with _mss() as sct:
            while not self._stop_event.is_set():
                t0 = time.time()
                try:
                    monitor = {"left": self.tx, "top": self.ty,
                               "width": self.tw, "height": self.th}
                    raw = sct.grab(monitor)
                    frame = np.array(raw)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    frame_gray_blur = cv2.GaussianBlur(frame_gray, (blur_k, blur_k), 0)
                    self._frame_count += 1

                    # ── Foreground mask: MOG2 (detects stationary + moving) ──
                    fg_mask = bg_sub.apply(frame_gray_blur)

                    # ── Absdiff mask: frame differencing (fast-moving) ───────
                    diff_mask = np.zeros_like(fg_mask)
                    diff = None
                    if self._prev_gray is not None:
                        diff = cv2.absdiff(self._prev_gray, frame_gray_blur)
                        _, diff_mask = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)

                    # ── Combine masks ─────────────────────────────────────────
                    # MOG2 is primary (catches still entities after warmup);
                    # absdiff adds sensitivity for fast movers in early frames.
                    if self._frame_count < 25:
                        # MOG2 not warmed up yet — use only absdiff
                        combined = diff_mask
                    else:
                        combined = cv2.bitwise_or(fg_mask, diff_mask)

                    combined = cv2.dilate(combined, None, iterations=2)
                    contours, _ = cv2.findContours(
                        combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                    )

                    # ── Self-exclusion zone bounds (pixels) ───────────────────
                    sz_x0 = int(sz_xf * self.tw)
                    sz_y0 = int(sz_yf * self.th)
                    sz_x1 = sz_x0 + int(sz_wf * self.tw)
                    sz_y1 = sz_y0 + int(sz_hf * self.th)

                    # ── Collect raw boxes, filtering self-zone ────────────────
                    raw_boxes: List[Tuple[int, int, int, int, float]] = []
                    for cnt in contours:
                        area = cv2.contourArea(cnt)
                        if area < min_area:
                            continue
                        x, y, w, h = cv2.boundingRect(cnt)
                        cx, cy = x + w // 2, y + h // 2
                        # Skip anything whose centre falls in the self-exclusion zone
                        if sz_en and sz_x0 <= cx <= sz_x1 and sz_y0 <= cy <= sz_y1:
                            continue
                        raw_boxes.append((x, y, w, h, float(area)))

                    # ── Merge nearby/overlapping boxes ────────────────────────
                    merged = _merge_boxes(raw_boxes, expand=30)

                    # ── Classify each merged box ──────────────────────────────
                    motion_objects = []
                    for (x, y, w, h) in merged:
                        speed = 0.0
                        if diff is not None:
                            roi = diff[max(0, y):y + h, max(0, x):x + w]
                            speed = float(np.mean(roi)) if roi.size else 0.0
                        label, conf = _heuristic_classify(
                            {"w": w, "h": h}, speed, self.tw, self.th
                        )
                        motion_objects.append({
                            "x": x, "y": y, "w": w, "h": h,
                            "label": label, "confidence": round(conf, 2),
                            "source": "motion",
                            "matched_image": "",
                        })

                    self._prev_gray = frame_gray_blur

                    # ── Template matching (DB) ────────────────────────────────
                    index = _load_index(self.db_dir)
                    db_matches = _match_db(
                        frame_gray, index, self.images_dir, sensitivity
                    )

                    # Enrich motion objects that overlap a DB match
                    for obj in motion_objects:
                        for m in db_matches:
                            ox1, oy1 = obj["x"], obj["y"]
                            ox2, oy2 = ox1 + obj["w"], oy1 + obj["h"]
                            mx1, my1 = m["x"], m["y"]
                            mx2, my2 = mx1 + m["w"], my1 + m["h"]
                            overlap_x = min(ox2, mx2) - max(ox1, mx1)
                            overlap_y = min(oy2, my2) - max(oy1, my1)
                            if overlap_x > 0 and overlap_y > 0:
                                obj["label"]         = m["name"]
                                obj["confidence"]    = m["confidence"]
                                obj["source"]        = "db"
                                obj["matched_image"] = m["name"]
                                break

                    # Add standalone DB matches not overlapping any motion object
                    used_db = {o["matched_image"] for o in motion_objects if o["source"] == "db"}
                    for m in db_matches:
                        if m["name"] not in used_db:
                            motion_objects.append({
                                "x": m["x"], "y": m["y"],
                                "w": m["w"], "h": m["h"],
                                "label": m["name"],
                                "confidence": m["confidence"],
                                "source": "db",
                                "matched_image": m["name"],
                            })

                    # Non-blocking put (drop stale results if consumer is behind)
                    if not self.result_queue.full():
                        self.result_queue.put({
                            "objects": motion_objects,
                            "db_matches": db_matches,
                            "frame": frame.copy(),
                            "timestamp": time.time(),
                        })
                except Exception:
                    pass

                elapsed = time.time() - t0
                self._stop_event.wait(max(0.0, interval - elapsed))


# ── Category color palette ───────────────────────────────────────────────────

_CATEGORY_COLORS = {
    "player": "#00FF00",
    "player / entity": "#00FF00",
    "enemy": "#FF0000",
    "enemy / NPC": "#FF4444",
    "npc": "#FFAA00",
    "item": "#00BFFF",
    "item / tool": "#00BFFF",
    "tool": "#00BFFF",
    "building": "#FF8C00",
    "building / structure": "#FF8C00",
    "structure": "#FF8C00",
    "terrain / large structure": "#A0522D",
    "crafting table": "#9370DB",
    "crafting table / chest": "#9370DB",
    "chest": "#9370DB",
    "projectile": "#FF00FF",
    "large entity": "#FF6B6B",
    "vehicle": "#FFD700",
    "animal": "#90EE90",
    "unknown": "#FFFFFF",
}

_DEFAULT_COLOR = "#00FF00"


def _cat_color(label: str) -> str:
    label_l = label.lower()
    for key, color in _CATEGORY_COLORS.items():
        if key in label_l:
            return color
    return _DEFAULT_COLOR


# ── Filter helpers ───────────────────────────────────────────────────────────

_PLAYER_KEYWORDS = {"player", "enemy", "npc", "entity", "mob", "hostile"}
_OBJECT_KEYWORDS = {"item", "tool", "building", "structure", "crafting", "chest",
                    "terrain", "vehicle", "animal", "projectile", "resource"}


def _passes_filter(obj: Dict[str, Any], mode: str) -> bool:
    """Return True if obj should be displayed under the given filter mode."""
    if mode == "all":
        return True
    label_l = obj.get("label", "").lower()
    if mode == "players":
        return any(kw in label_l for kw in _PLAYER_KEYWORDS)
    if mode == "objects":
        return any(kw in label_l for kw in _OBJECT_KEYWORDS)
    if mode == "known":
        return obj.get("source") == "db"
    return True


# ── Floating control panel ────────────────────────────────────────────────────

class ControlPanel:
    """Small always-on-top filter menu; draggable, dark-themed."""

    _BG = "#1a1a2e"
    _TITLE_BG = "#0d0d1a"
    _ACCENT = "#4fc3f7"

    _FILTERS = [
        ("All",     "all",     "#e0e0e0"),
        ("Players", "players", "#00FF00"),
        ("Objects", "objects", "#00BFFF"),
        ("Known",   "known",   "#FFD700"),
    ]

    def __init__(self, parent_x: int, parent_y: int, parent_w: int,
                 overlay: "ParsecVisionOverlay") -> None:
        self.overlay = overlay
        self._drag_offset: Optional[Tuple[int, int]] = None

        self.win = tk.Toplevel()
        self.win.title("")
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=self._BG)
        # Position top-right of the target window
        px = parent_x + parent_w - 325
        py = parent_y + 8
        self.win.geometry(f"315x100+{px}+{py}")

        self._build_ui()

    def _build_ui(self) -> None:
        # ── Title bar ────────────────────────────────────────────────────────
        bar = tk.Frame(self.win, bg=self._TITLE_BG, height=24)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        tk.Label(
            bar, text="  ParsecVision — Filter",
            bg=self._TITLE_BG, fg=self._ACCENT, font=("Consolas", 8, "bold"),
        ).pack(side=tk.LEFT, padx=4)

        quit_lbl = tk.Label(
            bar, text=" ✕ ", bg=self._TITLE_BG, fg="#ff6b6b",
            font=("Consolas", 10, "bold"), cursor="hand2",
        )
        quit_lbl.pack(side=tk.RIGHT, padx=4)
        quit_lbl.bind("<Button-1>", lambda _: self.overlay._quit())

        for widget in (bar, quit_lbl):
            widget.bind("<ButtonPress-1>", self._drag_press)
            widget.bind("<B1-Motion>", self._drag_move)

        # ── Filter radio buttons ──────────────────────────────────────────────
        body = tk.Frame(self.win, bg=self._BG, padx=8, pady=7)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body, text="Show:", bg=self._BG, fg="#888888",
            font=("Consolas", 8),
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.filter_var = tk.StringVar(value="all")
        self._btns: Dict[str, tk.Radiobutton] = {}

        for text, value, color in self._FILTERS:
            rb = tk.Radiobutton(
                body,
                text=text,
                variable=self.filter_var,
                value=value,
                indicatoron=False,
                bg=self._BG,
                fg=color,
                selectcolor="#2a3a5e",
                activebackground="#2a2a4e",
                activeforeground=color,
                font=("Consolas", 9, "bold"),
                relief="flat",
                bd=1,
                padx=7, pady=3,
                cursor="hand2",
                command=lambda v=value: self._on_filter(v),
            )
            rb.pack(side=tk.LEFT, padx=3)
            self._btns[value] = rb

        # ── Hotkey hint bar ───────────────────────────────────────────────────
        hotkey = self.overlay.config.get("capture_hotkey", "ctrl+alt+s").upper()
        hint = tk.Label(
            self.win,
            text=f"  {hotkey} = capture  |  ESC = quit",
            bg=self._TITLE_BG, fg="#555577", font=("Consolas", 7),
            anchor="w",
        )
        hint.pack(fill=tk.X)
        hint.bind("<ButtonPress-1>", self._drag_press)
        hint.bind("<B1-Motion>", self._drag_move)

    def _on_filter(self, value: str) -> None:
        self.overlay.set_filter(value)

    def _drag_press(self, event: Any) -> None:
        self._drag_offset = (
            event.x_root - self.win.winfo_x(),
            event.y_root - self.win.winfo_y(),
        )

    def _drag_move(self, event: Any) -> None:
        if self._drag_offset:
            nx = event.x_root - self._drag_offset[0]
            ny = event.y_root - self._drag_offset[1]
            self.win.geometry(f"+{nx}+{ny}")

    def destroy(self) -> None:
        try:
            self.win.destroy()
        except Exception:
            pass


# ── Main overlay application ─────────────────────────────────────────────────

class ParsecVisionOverlay:
    HOTKEY = "ctrl+alt+s"
    TRANSPARENT_COLOR = "#010101"  # near-black used as transparent color key

    def __init__(self, config: Dict[str, Any], db_dir: Path):
        self.config = config
        self.db_dir = db_dir
        self.images_dir = db_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.target_title = config.get("window_title", "Parsec")
        self.target_proc = config.get("process_name", "parsec.exe")
        self.sensitivity = float(config.get("sensitivity", 0.85))

        self._target_rect: Optional[Tuple[int, int, int, int]] = None
        self._current_objects: List[Dict[str, Any]] = []
        self._last_frame: Optional[Any] = None
        self._detection_thread: Optional[DetectionThread] = None
        self._result_queue: queue.Queue = queue.Queue(maxsize=2)
        self._capture_mode = False
        self._sel_start: Optional[Tuple[int, int]] = None
        self._sel_rect_id = None
        self._overlay_hwnd = None

        # tkinter
        self.root = tk.Tk()
        self.canvas: Optional[tk.Canvas] = None
        self._box_ids: List[int] = []
        self._label_ids: List[int] = []
        self._status_id: Optional[int] = None

        # Filter mode: "all" | "players" | "objects" | "known"
        self._filter_mode: str = "all"
        self._control_panel: Optional[ControlPanel] = None

        # Session player tracking
        self._players_seen_total: int = 0
        # Stores (cx, cy) of each distinct player seen; used for de-duplication
        self._player_positions_seen: List[Tuple[int, int]] = []

        # Saved snapshots dir
        (db_dir / "snapshots").mkdir(exist_ok=True)

    # ── Window finding ────────────────────────────────────────────────────────

    def _find_target(self) -> Optional[Tuple[int, int, int, int]]:
        """Find the target window rect (x, y, w, h)."""
        # Try by process name first (picks the larger Parsec window, 89.5MB one)
        wins = _find_process_windows(self.target_proc)
        if wins:
            # Pick the window with largest area
            wins.sort(key=lambda w: w[3] * w[4], reverse=True)
            _, x, y, w, h = wins[0]
            return (x, y, w, h)
        # Fallback: by window title
        result = _find_window_by_title(self.target_title)
        if result:
            _, x, y, w, h = result
            return (x, y, w, h)
        return None

    # ── Window setup ─────────────────────────────────────────────────────────

    def _setup_window(self, x: int, y: int, w: int, h: int) -> None:
        """Create the transparent overlay window."""
        self.root.title("ParsecVision Overlay")
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.overrideredirect(True)  # no title bar/borders
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", self.TRANSPARENT_COLOR)
        self.root.config(bg=self.TRANSPARENT_COLOR)

        self.canvas = tk.Canvas(
            self.root,
            width=w, height=h,
            bg=self.TRANSPARENT_COLOR,
            highlightthickness=0,
            cursor="arrow",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Get hwnd for click-through
        self.root.update_idletasks()
        self.root.update()
        self._overlay_hwnd = _user32.FindWindowW(None, "ParsecVision Overlay")
        if self._overlay_hwnd:
            _set_click_through(self._overlay_hwnd, True)

        # Mouse events (used in capture mode)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_release)

        # ESC to exit capture mode or quit
        self.root.bind("<Escape>", self._on_escape)

        # Register hotkey for capture mode
        if HAS_KEYBOARD:
            hotkey = self.config.get("capture_hotkey", self.HOTKEY)
            try:
                _keyboard.add_hotkey(hotkey, self._trigger_capture_mode, suppress=False)
            except Exception:
                pass

    # ── Capture mode ─────────────────────────────────────────────────────────

    def _trigger_capture_mode(self) -> None:
        """Called when the hotkey is pressed — switch to capture mode."""
        self.root.after(0, self._enter_capture_mode)

    def _enter_capture_mode(self) -> None:
        if self._capture_mode:
            return
        self._capture_mode = True
        if self._overlay_hwnd:
            _set_click_through(self._overlay_hwnd, False)
        self.canvas.config(cursor="crosshair")
        # Draw a semi-transparent capture prompt
        w = int(self.root.winfo_width())
        h = int(self.root.winfo_height())
        self._prompt_id = self.canvas.create_text(
            w // 2, 30,
            text="[ CAPTURE MODE — Drag to select region, ESC to cancel ]",
            fill="#FFD700", font=("Consolas", 13, "bold"),
        )

    def _exit_capture_mode(self) -> None:
        self._capture_mode = False
        if self._overlay_hwnd:
            _set_click_through(self._overlay_hwnd, True)
        self.canvas.config(cursor="arrow")
        if hasattr(self, "_prompt_id") and self._prompt_id:
            self.canvas.delete(self._prompt_id)
            self._prompt_id = None
        if self._sel_rect_id:
            self.canvas.delete(self._sel_rect_id)
            self._sel_rect_id = None
        self._sel_start = None

    def _on_escape(self, _event=None) -> None:
        if self._capture_mode:
            self._exit_capture_mode()
        else:
            self._quit()

    def _on_mouse_press(self, event: Any) -> None:
        if not self._capture_mode:
            return
        self._sel_start = (event.x, event.y)
        if self._sel_rect_id:
            self.canvas.delete(self._sel_rect_id)
            self._sel_rect_id = None

    def _on_mouse_drag(self, event: Any) -> None:
        if not self._capture_mode or not self._sel_start:
            return
        if self._sel_rect_id:
            self.canvas.delete(self._sel_rect_id)
        x0, y0 = self._sel_start
        self._sel_rect_id = self.canvas.create_rectangle(
            x0, y0, event.x, event.y,
            outline="#FFD700", width=2, dash=(4, 2),
        )

    def _on_mouse_release(self, event: Any) -> None:
        if not self._capture_mode or not self._sel_start:
            return
        x0, y0 = self._sel_start
        x1, y1 = event.x, event.y
        # Normalize rect
        rx = min(x0, x1); ry = min(y0, y1)
        rw = abs(x1 - x0); rh = abs(y1 - y0)

        if rw < 5 or rh < 5:
            self._exit_capture_mode()
            return

        # Temporarily restore click-through so dialogs work
        if self._overlay_hwnd:
            _set_click_through(self._overlay_hwnd, False)

        # Ask for a name
        name = simpledialog.askstring(
            "Name this object",
            f"Selected region: ({rx},{ry}) {rw}×{rh}\n\nEnter a name for this object:",
            parent=self.root,
        )

        if name and name.strip() and self._last_frame is not None and HAS_CV2:
            name = name.strip()
            # Crop the region from the last captured frame
            tx, ty, tw, th = self._target_rect  # type: ignore
            # The overlay coordinates = offsets within the target window
            crop = self._last_frame[ry:ry+rh, rx:rx+rw]
            if crop.size > 0:
                ext = ".png"
                filename = f"{name}{ext}"
                dest = self.images_dir / filename
                # If name already exists, add suffix
                counter = 1
                while dest.exists():
                    filename = f"{name}_{counter}{ext}"
                    dest = self.images_dir / filename
                    counter += 1

                import hashlib
                cv2.imwrite(str(dest), crop)
                file_hash = hashlib.sha256(dest.read_bytes()).hexdigest()

                index = _load_index(self.db_dir)
                index[name] = {
                    "filename": filename,
                    "hash": file_hash,
                    "added": time.time(),
                    "bbox_sample": {"x": rx, "y": ry, "w": rw, "h": rh},
                }
                _save_index(self.db_dir, index)

                messagebox.showinfo(
                    "Saved",
                    f"'{name}' saved to database.\nFile: {dest}",
                    parent=self.root,
                )

        self._exit_capture_mode()

    # ── Filter ────────────────────────────────────────────────────────────────

    def set_filter(self, mode: str) -> None:
        """Switch the active display filter (all / players / objects / known)."""
        self._filter_mode = mode

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _clear_boxes(self) -> None:
        for item in self._box_ids:
            self.canvas.delete(item)
        for item in self._label_ids:
            self.canvas.delete(item)
        if self._status_id:
            self.canvas.delete(self._status_id)
        self._box_ids.clear()
        self._label_ids.clear()
        self._status_id = None

    def _draw_objects(self) -> None:
        if self.canvas is None or self._capture_mode:
            return
        self._clear_boxes()

        visible = [o for o in self._current_objects if _passes_filter(o, self._filter_mode)]

        for obj in visible:
            x, y, w, h = obj["x"], obj["y"], obj["w"], obj["h"]
            label = obj.get("label", "unknown")
            conf = obj.get("confidence", 0.0)
            color = _cat_color(label)

            # Bounding box
            bid = self.canvas.create_rectangle(
                x, y, x + w, y + h,
                outline=color, width=2,
            )
            self._box_ids.append(bid)

            # Label background
            label_text = f"{label} {conf:.0%}"
            lw = len(label_text) * 7 + 6
            lh = 18
            bg = self.canvas.create_rectangle(
                x, y - lh, x + lw, y,
                fill=color, outline=color,
            )
            self._box_ids.append(bg)

            # Label text
            lid = self.canvas.create_text(
                x + 3, y - lh + 3,
                text=label_text,
                fill="#000000",
                font=("Consolas", 9, "bold"),
                anchor="nw",
            )
            self._label_ids.append(lid)

        # Status bar
        n_total = len(self._current_objects)
        n_visible = len(visible)
        n_db = sum(1 for o in visible if o.get("source") == "db")
        hotkey = self.config.get("capture_hotkey", self.HOTKEY)
        filter_label = {"all": "ALL", "players": "PLAYERS", "objects": "OBJECTS", "known": "KNOWN"}.get(self._filter_mode, self._filter_mode.upper())
        status = (
            f"Showing: {filter_label}  ({n_visible}/{n_total})  "
            f"Players seen: {self._players_seen_total}  "
            f"DB: {n_db}  |  {hotkey.upper()} = capture  |  ESC = quit"
        )
        cw = int(self.canvas.winfo_width())
        ch = int(self.canvas.winfo_height())
        # shadow
        self.canvas.create_text(cw // 2 + 1, ch - 13, text=status, fill="#000000", font=("Consolas", 9))
        self._status_id = self.canvas.create_text(
            cw // 2, ch - 14,
            text=status,
            fill="#FFFFFF",
            font=("Consolas", 9),
        )

    # ── Update loop ───────────────────────────────────────────────────────────

    def _poll_results(self) -> None:
        try:
            while True:
                result = self._result_queue.get_nowait()
                self._current_objects = result.get("objects", [])
                self._last_frame = result.get("frame")
                self._track_players(self._current_objects)
        except queue.Empty:
            pass
        self._draw_objects()

    def _track_players(self, objects: List[Dict[str, Any]]) -> None:
        """Count unique player/enemy/NPC detections across the session."""
        _player_kws = {"player", "enemy", "npc", "entity", "mob", "hostile"}
        for obj in objects:
            lbl = obj.get("label", "").lower()
            if not any(kw in lbl for kw in _player_kws):
                continue
            cx = obj["x"] + obj["w"] // 2
            cy = obj["y"] + obj["h"] // 2
            # Consider it a new unique player if its centre is >120px from every
            # previously logged position (avoids re-counting same NPC every frame)
            is_new = all(
                abs(cx - px) + abs(cy - py) > 120
                for px, py in self._player_positions_seen
            )
            if is_new:
                self._players_seen_total += 1
                self._player_positions_seen.append((cx, cy))
                # Discard oldest entries to avoid stale positions cluttering memory
                if len(self._player_positions_seen) > 80:
                    self._player_positions_seen.pop(0)

    # ── Update loop ───────────────────────────────────────────────────────────

    def _poll_results(self) -> None:
        try:
            while True:
                result = self._result_queue.get_nowait()
                self._current_objects = result.get("objects", [])
                self._last_frame = result.get("frame")
                self._track_players(self._current_objects)
        except queue.Empty:
            pass
        self._draw_objects()
        # Re-position overlay if target window moved
        rect = self._find_target()
        if rect and rect != self._target_rect:
            self._target_rect = rect
            x, y, w, h = rect
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            if self._detection_thread:
                self._detection_thread.stop()
            self._start_detection(*rect)
        self.root.after(100, self._poll_results)

    def _start_detection(self, x: int, y: int, w: int, h: int) -> None:
        self._detection_thread = DetectionThread(
            (x, y, w, h), self.config, self.db_dir, self._result_queue
        )
        self._detection_thread.start()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _quit(self) -> None:
        if self._detection_thread:
            self._detection_thread.stop()
        if self._control_panel:
            self._control_panel.destroy()
        if HAS_KEYBOARD:
            try:
                _keyboard.unhook_all_hotkeys()
            except Exception:
                pass
        self.root.destroy()

    def run(self) -> None:
        if not HAS_TK:
            print("ERROR: tkinter not available.")
            sys.exit(1)
        if not HAS_CV2:
            print("ERROR: opencv-python not installed.")
            sys.exit(1)
        if not HAS_MSS:
            print("ERROR: mss not installed.")
            sys.exit(1)

        rect = self._find_target()
        if not rect:
            print(f"ERROR: Could not find window for '{self.target_title}' / '{self.target_proc}'")
            sys.exit(2)

        self._target_rect = rect
        x, y, w, h = rect
        print(f"Attaching to window at ({x},{y}) {w}x{h}")

        self._setup_window(x, y, w, h)
        self._start_detection(x, y, w, h)

        # Create floating filter control panel
        self._control_panel = ControlPanel(x, y, w, self)

        # Start polling loop
        self.root.after(200, self._poll_results)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.mainloop()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: overlay.py <config_json_path>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        sys.exit(1)

    config = json.loads(config_path.read_text())
    db_dir = Path(config.get("db_dir", Path.home() / ".vivian" / "parsec_vision"))

    overlay = ParsecVisionOverlay(config, db_dir)
    overlay.run()


if __name__ == "__main__":
    main()
