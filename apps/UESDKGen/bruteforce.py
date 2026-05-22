"""bruteforce.py — Automated UE3 GNames/GObjects/offset discovery for UESDKGen.

BruteForcer.full_discover()  runs three phases:
  1. Pattern scan   — tries every known signature from GAME_PROFILES
  2. TArray scan    — finds TArray-shaped triples in memory
  3. Offset brute force — for each candidate pair tries all
     (name_field_off, name_str_off) combinations, scoring them by
     reading back valid ASCII UE3 names.

Returns a list of DiscoveryResult dicts sorted by confidence (0-100).
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

try:
    from .backends import MemoryBackend
    from .reader   import PatternScanner, UE3Reader
    from .profiles import GAME_PROFILES
except ImportError:
    from backends import MemoryBackend   # type: ignore[no-redef]
    from reader   import PatternScanner, UE3Reader  # type: ignore[no-redef]
    from profiles import GAME_PROFILES   # type: ignore[no-redef]


# ── Offset search spaces ──────────────────────────────────────────────────────
_NAME_FIELD_OFFS = list(range(0x00, 0x60, 4))   # UObject.FName.dwIndex
_NAME_STR_OFFS   = list(range(0x00, 0x30, 4))   # FNameEntry.Name[]


# ── Pattern extraction from profiles ─────────────────────────────────────────

def _collect_patterns() -> List[Dict]:
    """Build a deduplicated list of pattern descriptors from GAME_PROFILES."""
    seen: set = set()
    out: List[Dict] = []
    for key, prof in GAME_PROFILES.items():
        gop = prof.get("gobj_pattern")
        gnp = prof.get("gnam_pattern")
        if not gop or not gnp:
            continue
        sig = (bytes(gop), bytes(gnp))
        if sig in seen:
            continue
        seen.add(sig)
        out.append({
            "label":     f"{key} — {prof['name']}",
            "gobj_pat":  gop,
            "gobj_mask": prof["gobj_mask"],
            "gobj_off":  prof["gobj_off"],
            "gnam_pat":  gnp,
            "gnam_mask": prof["gnam_mask"],
            "gnam_off":  prof["gnam_off"],
        })
    return out


ALL_PATTERNS: List[Dict] = _collect_patterns()


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _score_gnames(backend: MemoryBackend, gnames_va: int,
                  name_str_off: int, is64: bool,
                  sample: int = 50) -> int:
    """Return 0-100: % of sampled GNames entries that decode as printable ASCII."""
    ptr_sz = 8 if is64 else 4
    gn_ptr = backend.rptr(gnames_va, is64)
    gn_cnt = backend.ru32(gnames_va + ptr_sz)
    if not gn_ptr or not gn_cnt or not (64 <= gn_cnt <= 600_000):
        return 0
    valid = tested = 0
    for i in range(min(sample, gn_cnt)):
        entry = backend.rptr(gn_ptr + i * ptr_sz, is64)
        if not entry:
            continue
        raw = backend.read(entry + name_str_off, 64)
        if not raw:
            continue
        end = raw.find(b"\x00")
        if end < 1:
            continue
        name = raw[:end]
        if all(32 <= b < 128 for b in name) and len(name) >= 2:
            valid += 1
        tested += 1
    return int(valid * 100 // max(tested, 1))


def _score_gobjects(backend: MemoryBackend, gobjects_va: int,
                    gnames_va: int, name_field_off: int,
                    name_str_off: int, is64: bool,
                    sample: int = 50) -> int:
    """Return 0-100: % of sampled GObjects that resolve to a valid ASCII name."""
    ptr_sz = 8 if is64 else 4
    go_ptr = backend.rptr(gobjects_va, is64)
    go_cnt = backend.ru32(gobjects_va + ptr_sz)
    gn_ptr = backend.rptr(gnames_va, is64)
    gn_cnt = backend.ru32(gnames_va + ptr_sz)
    if not all([go_ptr, go_cnt, gn_ptr, gn_cnt]):
        return 0
    if not (64 <= go_cnt <= 600_000):
        return 0
    valid = tested = 0
    for i in range(min(sample * 4, go_cnt)):
        obj = backend.rptr(go_ptr + i * ptr_sz, is64)
        if not obj:
            continue
        ni = backend.ru32(obj + name_field_off)
        if ni is None or ni >= gn_cnt:
            continue
        entry = backend.rptr(gn_ptr + ni * ptr_sz, is64)
        if not entry:
            continue
        raw = backend.read(entry + name_str_off, 32)
        if not raw:
            continue
        end = raw.find(b"\x00")
        if end < 1:
            continue
        name = raw[:end]
        if all(32 <= b < 128 for b in name) and len(name) >= 2:
            valid += 1
        tested += 1
        if tested >= sample:
            break
    return int(valid * 100 // max(tested, 1))


# ── BruteForcer ───────────────────────────────────────────────────────────────

class BruteForcer:
    """Three-phase UE3 struct discovery engine.

    Usage::

        bf = BruteForcer(backend, base=0x400000, size=0x2000000, is64=False)
        results = bf.full_discover(progress_cb)
        # returns list of dicts sorted by confidence, best first

    ``progress_cb(message: str, fraction: float)`` is optional.
    """

    def __init__(self, backend: MemoryBackend,
                 base: int  = 0x00400000,
                 size: int  = 0x02000000,
                 is64: bool = False) -> None:
        self._b       = backend
        self._base    = base
        self._size    = size
        self._is64    = is64
        self._scanner = PatternScanner(backend)

    # ── Phase 1a: known byte-pattern signatures ───────────────────────────

    def scan_patterns(self, cb: Optional[Callable] = None) -> List[Dict]:
        """Try all known byte-pattern signatures extracted from GAME_PROFILES.

        Returns a list of ``{gobj_va, gnam_va, pattern, source}`` dicts.
        """
        found: List[Dict] = []
        n = len(ALL_PATTERNS)
        for i, p in enumerate(ALL_PATTERNS):
            if cb:
                cb(f"Pattern {i + 1}/{n}: {p['label']}", (i / max(n, 1)) * 0.50)
            gobj_va = self._scanner.scan(
                self._base, self._size,
                p["gobj_pat"], p["gobj_mask"], p["gobj_off"], self._is64)
            gnam_va = self._scanner.scan(
                self._base, self._size,
                p["gnam_pat"], p["gnam_mask"], p["gnam_off"], self._is64)
            if gobj_va or gnam_va:
                found.append({
                    "gobj_va": gobj_va or 0,
                    "gnam_va": gnam_va or 0,
                    "pattern": p["label"],
                    "source":  "pattern",
                })
        return found

    # ── Phase 1b: generic TArray scan ────────────────────────────────────

    def scan_tarrays(self, cb: Optional[Callable] = None) -> List[Dict]:
        """Scan memory for TArray-shaped triples and pair Objects/Names candidates.

        Returns a list of ``{gobj_va, gnam_va, pattern, source}`` dicts.
        """
        reader = UE3Reader(self._b, is64=self._is64)

        def _inner_cb(done: int, total: int) -> None:
            if cb:
                cb(f"TArray scan {done / max(total, 1) * 100:.0f}%",
                   0.50 + (done / max(total, 1)) * 0.15)

        cands   = reader.scan_tarrays(self._base, self._size, _inner_cb)
        gobj_c  = [c for c in cands if "Object" in c.get("note", "")]
        gnam_c  = [c for c in cands if "Name"   in c.get("note", "")]

        out: List[Dict] = []
        for go in gobj_c[:8]:
            for gn in gnam_c[:8]:
                out.append({
                    "gobj_va": go["va"],
                    "gnam_va": gn["va"],
                    "pattern": "TArray scan",
                    "source":  "tarrays",
                })
        return out

    # ── Phase 2: offset brute force ───────────────────────────────────────

    def brute_offsets(self, gobj_va: int, gnam_va: int,
                      cb: Optional[Callable] = None) -> Optional[Dict]:
        """Try every (name_str_off, name_field_off) combination.

        Returns the best-scoring ``{name_field_off, name_str_off, confidence}``
        dict, or ``None`` when confidence < 20.
        """
        if not gobj_va or not gnam_va:
            return None

        # Step A — find best name_str_off by scoring GNames reads alone
        best_nso       = 0x10
        best_nso_score = 0
        for nso in _NAME_STR_OFFS:
            s = _score_gnames(self._b, gnam_va, nso, self._is64, sample=40)
            if s > best_nso_score:
                best_nso_score = s
                best_nso       = nso
        if best_nso_score < 10:
            return None   # can't read names at all — bad candidate

        # Step B — find best name_field_off by cross-checking GObjects → GNames
        best_nfo  = 0x2C
        best_score = 0
        n = len(_NAME_FIELD_OFFS)
        for i, nfo in enumerate(_NAME_FIELD_OFFS):
            if cb:
                cb(f"Offset probe {i + 1}/{n}", 0.65 + i / n * 0.30)
            s = _score_gobjects(
                self._b, gobj_va, gnam_va, nfo, best_nso, self._is64, sample=40)
            if s > best_score:
                best_score = s
                best_nfo   = nfo

        if best_score < 20:
            return None

        return {
            "name_field_off": best_nfo,
            "name_str_off":   best_nso,
            "confidence":     best_score,
        }

    # ── Full pipeline ─────────────────────────────────────────────────────

    def full_discover(self, cb: Optional[Callable] = None) -> List[Dict]:
        """Run all three phases.

        Returns a list of result dicts sorted by confidence (best first):
        ``{gobj_va, gnam_va, name_field_off, name_str_off, confidence, pattern, source}``
        """
        if cb:
            cb("Phase 1a: Pattern scan…", 0.0)
        candidates = self.scan_patterns(cb)

        if cb:
            cb("Phase 1b: TArray scan…", 0.50)
        candidates += self.scan_tarrays(cb)

        # Deduplicate by (gobj_va, gnam_va) pair
        seen: set = set()
        deduped: List[Dict] = []
        for c in candidates:
            key = (c.get("gobj_va"), c.get("gnam_va"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(c)

        results: List[Dict] = []
        nd = max(len(deduped), 1)
        for i, c in enumerate(deduped):
            if cb:
                cb(f"Phase 2: Brute-force offsets {i + 1}/{nd}…",
                   0.65 + i / nd * 0.30)
            offsets = self.brute_offsets(c["gobj_va"], c["gnam_va"], cb)
            if offsets:
                results.append({
                    "gobj_va":        c["gobj_va"],
                    "gnam_va":        c["gnam_va"],
                    "name_field_off": offsets["name_field_off"],
                    "name_str_off":   offsets["name_str_off"],
                    "confidence":     offsets["confidence"],
                    "pattern":        c["pattern"],
                    "source":         c["source"],
                })

        results.sort(key=lambda r: r["confidence"], reverse=True)
        if cb:
            cb("Discovery complete.", 1.0)
        return results
