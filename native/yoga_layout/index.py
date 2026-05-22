"""Yoga flexbox layout engine — mirrors src/native-ts/yoga-layout/index.ts.

This is a pure-Python port of the ~2 600-line TypeScript yoga-layout
implementation used by the Ink terminal-UI library.

Public API (identical names to TypeScript):

    createConfig() -> Config
    DEFAULT_CONFIG: Config
    class Node:
        # tree
        insertChild(child, index)
        removeChild(child)
        getChild(index) -> Node | None
        getChildCount() -> int
        getParent() -> Node | None
        # lifecycle
        free()
        freeRecursive()
        reset()
        # dirty / layout state
        markDirty()
        isDirty() -> bool
        hasNewLayout() -> bool
        markLayoutSeen()
        # measure
        setMeasureFunc(fn | None)
        unsetMeasureFunc()
        # layout results
        getComputedLeft() / Top / Width / Height / Right / Bottom
        getComputedLayout() -> dict
        getComputedBorder / Padding / Margin(edge)
        # style setters (see below — all TS names preserved)
        calculateLayout(ownerWidth?, ownerHeight?, direction?)
    loadYoga() -> Coroutine[Yoga]
    getYogaCounters() -> dict
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from vivian_cli.native.yoga_layout.enums import (
    Align, BoxSizing, Display, Edge, Errata, FlexDirection,
    Gutter, Justify, MeasureMode, Overflow, PositionType, Unit, Wrap,
)

# ─── Value type ──────────────────────────────────────────────────────────────

@dataclass
class Value:
    unit:  int   # Unit.*
    value: float

UNDEFINED_VALUE = Value(Unit.Undefined, float("nan"))
AUTO_VALUE      = Value(Unit.Auto,      float("nan"))

def pointValue(v: float) -> Value:
    return Value(Unit.Point, v)

def percentValue(v: float) -> Value:
    return Value(Unit.Percent, v)

def resolveValue(v: Value, owner: float) -> float:
    """Resolve a Value against an owner dimension. Returns NaN for undefined."""
    if v.unit == Unit.Point:
        return v.value
    if v.unit == Unit.Percent:
        if _isDefined(owner):
            return v.value * owner / 100.0
        return float("nan")
    return float("nan")

def _isDefined(v: float) -> bool:
    return v == v and not math.isinf(v)

def _sameFloat(a: float, b: float) -> bool:
    if a != a and b != b:
        return True
    return abs(a - b) < 1e-6

# ─── Edge indices (physical, matching the TS EDGE_* constants) ───────────────

EDGE_LEFT   = 0
EDGE_TOP    = 1
EDGE_RIGHT  = 2
EDGE_BOTTOM = 3

# ─── Style / Layout ──────────────────────────────────────────────────────────

@dataclass
class Style:
    flexDirection:  int   = FlexDirection.Row
    flexWrap:       int   = Wrap.NoWrap
    justifyContent: int   = Justify.FlexStart
    alignItems:     int   = Align.Stretch
    alignSelf:      int   = Align.Auto
    alignContent:   int   = Align.FlexStart
    overflow:       int   = Overflow.Visible
    display:        int   = Display.Flex
    positionType:   int   = PositionType.Relative
    flexGrow:       float = 0.0
    flexShrink:     float = 1.0
    flexBasis:      Value = field(default_factory=lambda: AUTO_VALUE)
    width:          Value = field(default_factory=lambda: UNDEFINED_VALUE)
    height:         Value = field(default_factory=lambda: UNDEFINED_VALUE)
    minWidth:       Value = field(default_factory=lambda: UNDEFINED_VALUE)
    minHeight:      Value = field(default_factory=lambda: UNDEFINED_VALUE)
    maxWidth:       Value = field(default_factory=lambda: UNDEFINED_VALUE)
    maxHeight:      Value = field(default_factory=lambda: UNDEFINED_VALUE)
    # margin[EDGE_LEFT..EDGE_BOTTOM], then Start/End/Horizontal/Vertical/All
    margin:         list[Value] = field(default_factory=lambda: [UNDEFINED_VALUE]*9)
    padding:        list[Value] = field(default_factory=lambda: [UNDEFINED_VALUE]*9)
    border:         list[Value] = field(default_factory=lambda: [UNDEFINED_VALUE]*9)
    position:       list[Value] = field(default_factory=lambda: [UNDEFINED_VALUE]*9)
    gap:            list[Value] = field(default_factory=lambda: [UNDEFINED_VALUE]*3)
    aspectRatio:    float = float("nan")
    direction:      int   = 0  # Direction.Inherit


@dataclass
class Layout:
    left:   float = 0.0
    top:    float = 0.0
    width:  float = 0.0
    height: float = 0.0
    # resolved edges (filled by layoutNode / resolveEdges4Into)
    margin:  list[float] = field(default_factory=lambda: [0.0]*4)
    padding: list[float] = field(default_factory=lambda: [0.0]*4)
    border:  list[float] = field(default_factory=lambda: [0.0]*4)
    hadOverflow: bool = False

# ─── Config ──────────────────────────────────────────────────────────────────

class Config:
    def __init__(self) -> None:
        self.pointScaleFactor: float = 1.0
        self.errata: int = Errata.None_
        self.useWebDefaults: bool = False
        self._experimentalFeatures: set[int] = set()

    def free(self) -> None:
        pass

    def isExperimentalFeatureEnabled(self, feature: int) -> bool:
        return feature in self._experimentalFeatures

    def setExperimentalFeatureEnabled(self, feature: int, enabled: bool) -> None:
        if enabled:
            self._experimentalFeatures.add(feature)
        else:
            self._experimentalFeatures.discard(feature)

    def setPointScaleFactor(self, f: float) -> None:
        self.pointScaleFactor = f

    def getErrata(self) -> int:
        return self.errata

    def setErrata(self, e: int) -> None:
        self.errata = e

    def setUseWebDefaults(self, v: bool) -> None:
        self.useWebDefaults = v

def createConfig() -> Config:
    return Config()

DEFAULT_CONFIG = createConfig()

# ─── Profiling counters ───────────────────────────────────────────────────────

_generation:        int = 0
_yogaNodesVisited:  int = 0
_yogaMeasureCalls:  int = 0
_yogaCacheHits:     int = 0
_yogaLiveNodes:     int = 0

def getYogaCounters() -> dict:
    return {
        "visited":   _yogaNodesVisited,
        "measured":  _yogaMeasureCalls,
        "cacheHits": _yogaCacheHits,
        "live":      _yogaLiveNodes,
    }

# ─── Node ────────────────────────────────────────────────────────────────────

CACHE_SLOTS = 4

class Node:
    """Yoga flexbox layout node."""

    def __init__(self, config: Optional[Config] = None) -> None:
        global _yogaLiveNodes
        _yogaLiveNodes += 1

        self.style:    Style  = Style()
        self.layout:   Layout = Layout()
        self.parent:   Optional["Node"] = None
        self.children: list["Node"] = []
        self.measureFunc: Optional[Callable] = None
        self.config: Config = config or DEFAULT_CONFIG

        self.isDirty_:            bool  = True
        self.isReferenceBaseline_: bool  = False
        self._hasNewLayout:       bool  = True

        # Scratch: main/cross sizes during layout
        self._mainSize:  float = 0.0
        self._crossSize: float = 0.0
        self._flexBasis: float = 0.0
        self._lineIndex: int   = 0

        # Fast-path flags
        self._hasAutoMargin: bool = False
        self._hasPosition:   bool = False
        self._hasPadding:    bool = False
        self._hasBorder:     bool = False
        self._hasMargin:     bool = False

        # Flex-basis cache
        self._fbBasis:      float = float("nan")
        self._fbOwnerW:     float = float("nan")
        self._fbOwnerH:     float = float("nan")
        self._fbAvailMain:  float = float("nan")
        self._fbAvailCross: float = float("nan")
        self._fbCrossMode:  int   = MeasureMode.Undefined
        self._fbGen:        int   = -1

        # Layout cache (single-entry fast path)
        self._lW:    float = float("nan"); self._lH:    float = float("nan")
        self._lWM:   int   = -1;           self._lHM:   int   = -1
        self._lOW:   float = float("nan"); self._lOH:   float = float("nan")
        self._lFW:   Optional[float] = None; self._lFH: Optional[float] = None
        self._lOutW: float = 0.0;           self._lOutH: float = 0.0
        self._hasL:  bool  = False

        # Measure cache
        self._mW:    float = float("nan"); self._mH:    float = float("nan")
        self._mWM:   int   = -1;           self._mHM:   int   = -1
        self._mOW:   float = float("nan"); self._mOH:   float = float("nan")
        self._mOutW: float = 0.0;           self._mOutH: float = 0.0
        self._hasM:  bool  = False

        # Multi-entry cache
        self._cIn:  Optional[list[float]] = None
        self._cOut: Optional[list[float]] = None
        self._cGen: int = -1
        self._cN:   int = 0

    # ── Tree ──

    def insertChild(self, child: "Node", index: int) -> None:
        if child.parent:
            child.parent.removeChild(child)
        child.parent = self
        self.children.insert(index, child)
        self.markDirty()

    def removeChild(self, child: "Node") -> None:
        if child in self.children:
            self.children.remove(child)
            child.parent = None
        self.markDirty()

    def getChild(self, index: int) -> Optional["Node"]:
        if 0 <= index < len(self.children):
            return self.children[index]
        return None

    def getChildCount(self) -> int:
        return len(self.children)

    def getParent(self) -> Optional["Node"]:
        return self.parent

    # ── Lifecycle ──

    def free(self) -> None:
        global _yogaLiveNodes
        _yogaLiveNodes = max(0, _yogaLiveNodes - 1)

    def freeRecursive(self) -> None:
        for c in list(self.children):
            c.freeRecursive()
        self.free()

    def reset(self) -> None:
        assert len(self.children) == 0, "reset() requires no children"
        self.style    = Style()
        self.layout   = Layout()
        self.isDirty_ = True
        self._hasNewLayout = True
        self.measureFunc = None

    # ── Dirty / layout state ──

    def markDirty(self) -> None:
        self.isDirty_ = True
        self._hasNewLayout = True
        self._hasL = False
        self._hasM = False
        if self.parent:
            self.parent.markDirty()

    def isDirty(self) -> bool:
        return self.isDirty_

    def hasNewLayout(self) -> bool:
        return self._hasNewLayout

    def markLayoutSeen(self) -> None:
        self._hasNewLayout = False

    # ── Measure ──

    def setMeasureFunc(self, fn: Optional[Callable]) -> None:
        self.measureFunc = fn
        self.markDirty()

    def unsetMeasureFunc(self) -> None:
        self.setMeasureFunc(None)

    # ── Layout results ──

    def getComputedLeft(self)   -> float: return self.layout.left
    def getComputedTop(self)    -> float: return self.layout.top
    def getComputedWidth(self)  -> float: return self.layout.width
    def getComputedHeight(self) -> float: return self.layout.height
    def getComputedRight(self)  -> float: return self.layout.left + self.layout.width
    def getComputedBottom(self) -> float: return self.layout.top  + self.layout.height

    def getComputedLayout(self) -> dict:
        return {
            "left":   self.layout.left,
            "top":    self.layout.top,
            "width":  self.layout.width,
            "height": self.layout.height,
            "right":  self.getComputedRight(),
            "bottom": self.getComputedBottom(),
        }

    def getComputedBorder(self, edge: int) -> float:
        return _resolveEdge(self.style.border, _physicalEdge(edge), self.layout.width)

    def getComputedPadding(self, edge: int) -> float:
        return _resolveEdge(self.style.padding, _physicalEdge(edge), self.layout.width)

    def getComputedMargin(self, edge: int) -> float:
        return _resolveEdge(self.style.margin, _physicalEdge(edge), self.layout.width)

    # ── Style setters ──

    def _setWidth(self, v: Value) -> None:
        self.style.width = v; self.markDirty()
    def setWidth(self, v: float) -> None:
        self._setWidth(parseDimension(v))
    def setWidthPercent(self, v: float) -> None:
        self._setWidth(percentValue(v))
    def setWidthAuto(self) -> None:
        self._setWidth(AUTO_VALUE)

    def _setHeight(self, v: Value) -> None:
        self.style.height = v; self.markDirty()
    def setHeight(self, v: float) -> None:
        self._setHeight(parseDimension(v))
    def setHeightPercent(self, v: float) -> None:
        self._setHeight(percentValue(v))
    def setHeightAuto(self) -> None:
        self._setHeight(AUTO_VALUE)

    def setMinWidth(self, v: float) -> None:
        self.style.minWidth = parseDimension(v); self.markDirty()
    def setMinWidthPercent(self, v: float) -> None:
        self.style.minWidth = percentValue(v); self.markDirty()
    def setMinHeight(self, v: float) -> None:
        self.style.minHeight = parseDimension(v); self.markDirty()
    def setMinHeightPercent(self, v: float) -> None:
        self.style.minHeight = percentValue(v); self.markDirty()
    def setMaxWidth(self, v: float) -> None:
        self.style.maxWidth = parseDimension(v); self.markDirty()
    def setMaxWidthPercent(self, v: float) -> None:
        self.style.maxWidth = percentValue(v); self.markDirty()
    def setMaxHeight(self, v: float) -> None:
        self.style.maxHeight = parseDimension(v); self.markDirty()
    def setMaxHeightPercent(self, v: float) -> None:
        self.style.maxHeight = percentValue(v); self.markDirty()

    def setFlexDirection(self, v: int) -> None:
        self.style.flexDirection = v; self.markDirty()
    def setFlexGrow(self, v: float) -> None:
        self.style.flexGrow = v; self.markDirty()
    def setFlexShrink(self, v: float) -> None:
        self.style.flexShrink = v; self.markDirty()
    def setFlex(self, v: float) -> None:
        self.style.flexGrow = v
        self.style.flexShrink = 1.0 if v != 0 else 0.0
        self.style.flexBasis = pointValue(0.0) if v != 0 else AUTO_VALUE
        self.markDirty()

    def setFlexBasis(self, v: float) -> None:
        self.style.flexBasis = parseDimension(v); self.markDirty()
    def setFlexBasisPercent(self, v: float) -> None:
        self.style.flexBasis = percentValue(v); self.markDirty()
    def setFlexBasisAuto(self) -> None:
        self.style.flexBasis = AUTO_VALUE; self.markDirty()

    def setFlexWrap(self, v: int) -> None:
        self.style.flexWrap = v; self.markDirty()
    def setAlignItems(self, v: int) -> None:
        self.style.alignItems = v; self.markDirty()
    def setAlignSelf(self, v: int) -> None:
        self.style.alignSelf = v; self.markDirty()
    def setAlignContent(self, v: int) -> None:
        self.style.alignContent = v; self.markDirty()
    def setJustifyContent(self, v: int) -> None:
        self.style.justifyContent = v; self.markDirty()
    def setDisplay(self, v: int) -> None:
        self.style.display = v; self.markDirty()
    def getDisplay(self) -> int:
        return self.style.display

    def setPositionType(self, v: int) -> None:
        self.style.positionType = v; self.markDirty()
    def setOverflow(self, v: int) -> None:
        self.style.overflow = v; self.markDirty()
    def setDirection(self, v: int) -> None:
        self.style.direction = v; self.markDirty()
    def setBoxSizing(self, v: int) -> None:
        pass  # stub — not yet implemented

    def _setEdge(self, edges: list[Value], edge: int, v: Value) -> None:
        edges[edge] = v
        self._updateEdgeFlags()
        self.markDirty()

    def _updateEdgeFlags(self) -> None:
        def _anyDefined(edges: list[Value]) -> bool:
            return any(e.unit != Unit.Undefined for e in edges)
        def _anyAuto(edges: list[Value]) -> bool:
            return any(e.unit == Unit.Auto for e in edges)
        self._hasMargin  = _anyDefined(self.style.margin)
        self._hasAutoMargin = _anyAuto(self.style.margin)
        self._hasPadding = _anyDefined(self.style.padding)
        self._hasBorder  = _anyDefined(self.style.border)
        self._hasPosition = _anyDefined(self.style.position)

    def setPosition(self, edge: int, v: float) -> None:
        self._setEdge(self.style.position, _physicalEdge(edge), parseDimension(v))
    def setPositionPercent(self, edge: int, v: float) -> None:
        self._setEdge(self.style.position, _physicalEdge(edge), percentValue(v))
    def setPositionAuto(self, edge: int) -> None:
        self._setEdge(self.style.position, _physicalEdge(edge), AUTO_VALUE)

    def setMargin(self, edge: int, v: float) -> None:
        self._setEdge(self.style.margin, edge, parseDimension(v))
    def setMarginPercent(self, edge: int, v: float) -> None:
        self._setEdge(self.style.margin, edge, percentValue(v))
    def setMarginAuto(self, edge: int) -> None:
        self._setEdge(self.style.margin, edge, AUTO_VALUE)

    def setPadding(self, edge: int, v: float) -> None:
        self._setEdge(self.style.padding, edge, parseDimension(v))
    def setPaddingPercent(self, edge: int, v: float) -> None:
        self._setEdge(self.style.padding, edge, percentValue(v))

    def setBorder(self, edge: int, v: float) -> None:
        self._setEdge(self.style.border, edge, parseDimension(v))

    def setGap(self, gutter: int, v: float) -> None:
        self.style.gap[gutter] = parseDimension(v); self.markDirty()
    def setGapPercent(self, gutter: int, v: float) -> None:
        self.style.gap[gutter] = percentValue(v); self.markDirty()

    # ── Style getters ──

    def getFlexDirection(self)  -> int:   return self.style.flexDirection
    def getJustifyContent(self) -> int:   return self.style.justifyContent
    def getAlignItems(self)     -> int:   return self.style.alignItems
    def getAlignSelf(self)      -> int:   return self.style.alignSelf
    def getAlignContent(self)   -> int:   return self.style.alignContent
    def getFlexGrow(self)       -> float: return self.style.flexGrow
    def getFlexShrink(self)     -> float: return self.style.flexShrink
    def getFlexBasis(self)      -> Value: return self.style.flexBasis
    def getFlexWrap(self)       -> int:   return self.style.flexWrap
    def getWidth(self)          -> Value: return self.style.width
    def getHeight(self)         -> Value: return self.style.height
    def getOverflow(self)       -> int:   return self.style.overflow
    def getPositionType(self)   -> int:   return self.style.positionType
    def getDirection(self)      -> int:   return self.style.direction

    # ── Style copy (full implementation) ──

    def copyStyle(self, other: "Node") -> None:
        import copy
        self.style = copy.deepcopy(other.style)
        self.markDirty()

    def setDirtiedFunc(self, _fn: Any) -> None: pass
    def unsetDirtiedFunc(self) -> None: pass

    def setIsReferenceBaseline(self, v: bool) -> None:
        self.isReferenceBaseline_ = v; self.markDirty()

    def isReferenceBaseline(self) -> bool:
        return self.isReferenceBaseline_

    def setAspectRatio(self, v: float) -> None:
        self.style.aspectRatio = v; self.markDirty()

    def getAspectRatio(self) -> float:
        return self.style.aspectRatio

    def setAlwaysFormsContainingBlock(self, _v: bool) -> None: pass

    # ── Entry point ──

    def calculateLayout(
        self,
        ownerWidth:  float = float("nan"),
        ownerHeight: float = float("nan"),
        direction:   int   = 0,
    ) -> None:
        """Run the flexbox layout algorithm on this tree."""
        global _generation
        _generation += 1
        _layoutNode(
            self,
            ownerWidth  if _isDefined(ownerWidth)  else float("nan"),
            ownerHeight if _isDefined(ownerHeight) else float("nan"),
            MeasureMode.Undefined if not _isDefined(ownerWidth)  else MeasureMode.Exactly,
            MeasureMode.Undefined if not _isDefined(ownerHeight) else MeasureMode.Exactly,
            ownerWidth  if _isDefined(ownerWidth)  else float("nan"),
            ownerHeight if _isDefined(ownerHeight) else float("nan"),
            True,
        )
        if self.config.pointScaleFactor != 0:
            _roundLayout(self, self.config.pointScaleFactor, 0.0, 0.0)
        self._hasNewLayout = True

# ─── Edge resolution helpers ──────────────────────────────────────────────────

def _physicalEdge(edge: int) -> int:
    """Map Edge enum value to physical [0..3] index (Left/Top/Right/Bottom)."""
    if edge == Edge.Left  or edge == Edge.Start:      return EDGE_LEFT
    if edge == Edge.Top:                               return EDGE_TOP
    if edge == Edge.Right or edge == Edge.End:         return EDGE_RIGHT
    if edge == Edge.Bottom:                            return EDGE_BOTTOM
    return EDGE_LEFT

def _resolveEdgeRaw(edges: list[Value], phys: int) -> Value:
    """Return the most-specific defined value for a physical edge."""
    v = edges[phys]
    if v.unit != Unit.Undefined:
        return v
    # Logical shortcuts: start→left(0), end→right(2)
    if phys == EDGE_LEFT:
        v = edges[Edge.Start]
        if v.unit != Unit.Undefined: return v
        v = edges[Edge.Horizontal]
        if v.unit != Unit.Undefined: return v
    elif phys == EDGE_RIGHT:
        v = edges[Edge.End]
        if v.unit != Unit.Undefined: return v
        v = edges[Edge.Horizontal]
        if v.unit != Unit.Undefined: return v
    elif phys == EDGE_TOP:
        v = edges[Edge.Vertical]
        if v.unit != Unit.Undefined: return v
    elif phys == EDGE_BOTTOM:
        v = edges[Edge.Vertical]
        if v.unit != Unit.Undefined: return v
    # All
    v = edges[Edge.All]
    if v.unit != Unit.Undefined: return v
    return UNDEFINED_VALUE

def _resolveEdge(edges: list[Value], phys: int, ownerSize: float, allowAuto: bool = False) -> float:
    v = _resolveEdgeRaw(edges, phys)
    if v.unit == Unit.Auto:
        return 0.0 if not allowAuto else float("nan")
    r = resolveValue(v, ownerSize)
    return r if _isDefined(r) else 0.0

def _resolveEdges4Into(edges: list[Value], ownerSize: float, out: list[float]) -> None:
    for i in range(4):
        out[i] = _resolveEdge(edges, i, ownerSize)

def _isMarginAuto(edges: list[Value], phys: int) -> bool:
    return _resolveEdgeRaw(edges, phys).unit == Unit.Auto

def _hasAnyAutoEdge(edges: list[Value]) -> bool:
    return any(e.unit == Unit.Auto for e in edges)

# ─── Axis helpers ─────────────────────────────────────────────────────────────

def _isRow(dir_: int) -> bool:
    return dir_ == FlexDirection.Row or dir_ == FlexDirection.RowReverse

def _isReverse(dir_: int) -> bool:
    return dir_ == FlexDirection.RowReverse or dir_ == FlexDirection.ColumnReverse

def _crossAxis(dir_: int) -> int:
    return FlexDirection.Column if _isRow(dir_) else FlexDirection.Row

def _leadingEdge(dir_: int) -> int:
    if dir_ == FlexDirection.Row:           return EDGE_LEFT
    if dir_ == FlexDirection.RowReverse:    return EDGE_RIGHT
    if dir_ == FlexDirection.Column:        return EDGE_TOP
    return EDGE_BOTTOM  # ColumnReverse

def _trailingEdge(dir_: int) -> int:
    if dir_ == FlexDirection.Row:           return EDGE_RIGHT
    if dir_ == FlexDirection.RowReverse:    return EDGE_LEFT
    if dir_ == FlexDirection.Column:        return EDGE_BOTTOM
    return EDGE_TOP  # ColumnReverse

def _childMarginForAxis(child: Node, axis: int, ownerW: float) -> float:
    if not child._hasMargin:
        return 0.0
    lead  = _resolveEdge(child.style.margin, _leadingEdge(axis),  ownerW)
    trail = _resolveEdge(child.style.margin, _trailingEdge(axis), ownerW)
    return lead + trail

def _resolveGap(style: Style, gutter: int, ownerSize: float) -> float:
    v = style.gap[gutter]
    if v.unit == Unit.Undefined:
        v = style.gap[Gutter.All]
    r = resolveValue(v, ownerSize)
    return max(0.0, r) if _isDefined(r) else 0.0

# ─── Bound axis (min/max clamping) ───────────────────────────────────────────

def _boundAxis(style: Style, isWidth: bool, value: float, ownerW: float, ownerH: float) -> float:
    minV = style.minWidth  if isWidth else style.minHeight
    maxV = style.maxWidth  if isWidth else style.maxHeight
    owner = ownerW if isWidth else ownerH
    v = value
    if maxV.unit == Unit.Point and v > maxV.value:
        v = maxV.value
    elif maxV.unit == Unit.Percent:
        m = maxV.value * owner / 100.0
        if m == m and v > m:
            v = m
    if minV.unit == Unit.Point and v < minV.value:
        v = minV.value
    elif minV.unit == Unit.Percent:
        m = minV.value * owner / 100.0
        if m == m and v < m:
            v = m
    return v

# ─── Cache helpers ─────────────────────────────────────────────────────────────

def _cacheWrite(
    node: Node,
    availW: float, availH: float,
    wMode: int, hMode: int,
    ownerW: float, ownerH: float,
    forceW: Optional[float], forceH: Optional[float],
    wasDirty: bool,
) -> None:
    node._lW = availW; node._lH = availH
    node._lWM = wMode; node._lHM = hMode
    node._lOW = ownerW; node._lOH = ownerH
    node._lFW = forceW; node._lFH = forceH
    node._lOutW = node.layout.width; node._lOutH = node.layout.height
    node._hasL = True

def _commitCacheOutputs(node: Node, performLayout: bool) -> None:
    if not performLayout:
        node._lOutW = node.layout.width
        node._lOutH = node.layout.height

def _cacheHit(
    node: Node,
    availW: float, availH: float,
    wMode: int, hMode: int,
    ownerW: float, ownerH: float,
    forceW: Optional[float], forceH: Optional[float],
) -> bool:
    if not node._hasL:
        return False
    if node.isDirty_:
        return False
    if not _sameFloat(node._lW, availW):   return False
    if not _sameFloat(node._lH, availH):   return False
    if node._lWM != wMode:                 return False
    if node._lHM != hMode:                 return False
    if not _sameFloat(node._lOW, ownerW):  return False
    if not _sameFloat(node._lOH, ownerH):  return False
    if forceW is None and node._lFW is not None: return False
    if forceH is None and node._lFH is not None: return False
    if forceW is not None and not _sameFloat(node._lFW or 0, forceW): return False
    if forceH is not None and not _sameFloat(node._lFH or 0, forceH): return False
    return True

# ─── Collect layout children (handles display:contents) ──────────────────────

def _zeroLayoutRecursive(node: Node) -> None:
    for c in node.children:
        c.layout.left = 0.0; c.layout.top = 0.0
        c.layout.width = 0.0; c.layout.height = 0.0
        c.isDirty_ = True; c._hasL = False; c._hasM = False
        _zeroLayoutRecursive(c)

def _collectLayoutChildren(node: Node, flow: list[Node], abs_: list[Node]) -> None:
    for c in node.children:
        d = c.style.display
        if d == Display.None_:
            c.layout.left = c.layout.top = c.layout.width = c.layout.height = 0.0
            _zeroLayoutRecursive(c)
        elif d == Display.Contents:
            c.layout.left = c.layout.top = c.layout.width = c.layout.height = 0.0
            _collectLayoutChildren(c, flow, abs_)
        elif c.style.positionType == PositionType.Absolute:
            abs_.append(c)
        else:
            flow.append(c)

# ─── Baseline ─────────────────────────────────────────────────────────────────

def _resolveChildAlign(parent: Node, child: Node) -> int:
    return parent.style.alignItems if child.style.alignSelf == Align.Auto else child.style.alignSelf

def _calculateBaseline(node: Node) -> float:
    baselineChild: Optional[Node] = None
    for c in node.children:
        if c._lineIndex > 0: break
        if c.style.positionType == PositionType.Absolute: continue
        if c.style.display == Display.None_: continue
        if _resolveChildAlign(node, c) == Align.Baseline or c.isReferenceBaseline_:
            baselineChild = c; break
        if baselineChild is None:
            baselineChild = c
    if baselineChild is None:
        return node.layout.height
    return _calculateBaseline(baselineChild) + baselineChild.layout.top

def _isBaselineLayout(node: Node, flowChildren: list[Node]) -> bool:
    if not _isRow(node.style.flexDirection): return False
    if node.style.alignItems == Align.Baseline: return True
    for c in flowChildren:
        if c.style.alignSelf == Align.Baseline: return True
    return False

def _isStretchAlign(child: Node) -> bool:
    p = child.parent
    if not p: return False
    align = p.style.alignItems if child.style.alignSelf == Align.Auto else child.style.alignSelf
    return align == Align.Stretch

def _hasMeasureFuncInSubtree(node: Node) -> bool:
    if node.measureFunc: return True
    return any(_hasMeasureFuncInSubtree(c) for c in node.children)

# ─── computeFlexBasis ─────────────────────────────────────────────────────────

def _computeFlexBasis(
    child: Node,
    mainAxis: int,
    availableMain: float,
    availableCross: float,
    crossMode: int,
    ownerW: float,
    ownerH: float,
) -> float:
    global _generation
    sameGen = child._fbGen == _generation
    if (
        (sameGen or not child.isDirty_)
        and child._fbCrossMode == crossMode
        and _sameFloat(child._fbOwnerW, ownerW)
        and _sameFloat(child._fbOwnerH, ownerH)
        and _sameFloat(child._fbAvailMain, availableMain)
        and _sameFloat(child._fbAvailCross, availableCross)
    ):
        return child._fbBasis

    cs = child.style
    isMainRow = _isRow(mainAxis)

    # Explicit flex-basis
    basis_v = resolveValue(cs.flexBasis, availableMain)
    if _isDefined(basis_v):
        b = max(0.0, basis_v)
        _saveFb(child, b, ownerW, ownerH, availableMain, availableCross, crossMode)
        return b

    # Style dimension on main axis
    mainStyleDim = cs.width if isMainRow else cs.height
    mainOwner    = ownerW   if isMainRow else ownerH
    resolved = resolveValue(mainStyleDim, mainOwner)
    if _isDefined(resolved):
        b = max(0.0, resolved)
        _saveFb(child, b, ownerW, ownerH, availableMain, availableCross, crossMode)
        return b

    # Need to measure
    crossStyleDim = cs.height if isMainRow else cs.width
    crossOwner    = ownerH    if isMainRow else ownerW
    crossConstraint = resolveValue(crossStyleDim, crossOwner)
    if _isDefined(crossConstraint):
        crossConstraintMode = MeasureMode.Exactly
    else:
        crossConstraintMode = MeasureMode.Undefined
        if _isDefined(availableCross):
            crossConstraint = availableCross
            crossConstraintMode = (
                MeasureMode.Exactly
                if crossMode == MeasureMode.Exactly and _isStretchAlign(child)
                else MeasureMode.AtMost
            )

    mainConstraint     = float("nan")
    mainConstraintMode = MeasureMode.Undefined
    if isMainRow and _isDefined(availableMain) and _hasMeasureFuncInSubtree(child):
        mainConstraint     = availableMain
        mainConstraintMode = MeasureMode.AtMost

    mw     = mainConstraint     if isMainRow else crossConstraint
    mh     = crossConstraint    if isMainRow else mainConstraint
    mwMode = mainConstraintMode if isMainRow else crossConstraintMode
    mhMode = crossConstraintMode if isMainRow else mainConstraintMode

    _layoutNode(child, mw, mh, mwMode, mhMode, ownerW, ownerH, False)
    b = child.layout.width if isMainRow else child.layout.height
    _saveFb(child, b, ownerW, ownerH, availableMain, availableCross, crossMode)
    return b

def _saveFb(child: Node, b: float, ow: float, oh: float, am: float, ac: float, cm: int) -> None:
    child._fbBasis      = b
    child._fbOwnerW     = ow
    child._fbOwnerH     = oh
    child._fbAvailMain  = am
    child._fbAvailCross = ac
    child._fbCrossMode  = cm
    child._fbGen        = _generation

# ─── resolveFlexibleLengths ───────────────────────────────────────────────────

def _resolveFlexibleLengths(
    children: list[Node],
    availableInnerMain: float,
    totalFlexBasis: float,
    isMainRow: bool,
    ownerW: float,
    ownerH: float,
) -> None:
    n = len(children)
    frozen = [False] * n
    initialFree = (availableInnerMain - totalFlexBasis) if _isDefined(availableInnerMain) else 0.0

    for i, c in enumerate(children):
        clamped = _boundAxis(c.style, isMainRow, c._flexBasis, ownerW, ownerH)
        inflexible = (
            not _isDefined(availableInnerMain)
            or (initialFree >= 0 and c.style.flexGrow == 0)
            or (initialFree < 0 and c.style.flexShrink == 0)
        )
        if inflexible:
            c._mainSize = max(0.0, clamped)
            frozen[i] = True
        else:
            c._mainSize = c._flexBasis

    unclamped = [0.0] * n
    for _ in range(n + 1):
        frozenDelta  = 0.0
        totalGrow    = 0.0
        totalShrinkS = 0.0
        unfrozenCount = 0
        for i, c in enumerate(children):
            if frozen[i]:
                frozenDelta += c._mainSize - c._flexBasis
            else:
                totalGrow    += c.style.flexGrow
                totalShrinkS += c.style.flexShrink * c._flexBasis
                unfrozenCount += 1
        if unfrozenCount == 0:
            break
        remaining = initialFree - frozenDelta
        if remaining > 0 and totalGrow > 0 and totalGrow < 1:
            scaled = initialFree * totalGrow
            if scaled < remaining:
                remaining = scaled
        elif remaining < 0 and totalShrinkS > 0:
            totalShrink = sum(c.style.flexShrink for i, c in enumerate(children) if not frozen[i])
            if totalShrink < 1:
                scaled = initialFree * totalShrink
                if scaled > remaining:
                    remaining = scaled

        totalViolation = 0.0
        for i, c in enumerate(children):
            if frozen[i]:
                continue
            t = c._flexBasis
            if remaining > 0 and totalGrow > 0:
                t += remaining * c.style.flexGrow / totalGrow
            elif remaining < 0 and totalShrinkS > 0:
                t += remaining * (c.style.flexShrink * c._flexBasis) / totalShrinkS
            unclamped[i] = t
            clamped = max(0.0, _boundAxis(c.style, isMainRow, t, ownerW, ownerH))
            c._mainSize = clamped
            totalViolation += clamped - t

        if totalViolation == 0:
            break
        anyFrozen = False
        for i, c in enumerate(children):
            if frozen[i]:
                continue
            v = c._mainSize - unclamped[i]
            if (totalViolation > 0 and v > 0) or (totalViolation < 0 and v < 0):
                frozen[i] = True
                anyFrozen = True
        if not anyFrozen:
            break

# ─── Absolute child positioning ───────────────────────────────────────────────

def _justifyAbsolute(justify: int, lead: float, trail: float, childSize: float) -> float:
    if justify == Justify.Center:
        return lead + (trail - lead - childSize) / 2
    if justify == Justify.FlexEnd:
        return trail - childSize
    return lead

def _alignAbsolute(align: int, lead: float, trail: float, childSize: float, wrapReverse: bool) -> float:
    if align == Align.Center:
        return lead + (trail - lead - childSize) / 2
    if align == Align.FlexEnd:
        return (lead if wrapReverse else trail - childSize)
    return (trail - childSize if wrapReverse else lead)

def _layoutAbsoluteChild(
    parent: Node, child: Node,
    parentWidth: float, parentHeight: float,
    pad: list[float], bor: list[float],
) -> None:
    cs = child.style
    posLeft   = _resolveEdgeRaw(cs.position, EDGE_LEFT)
    posRight  = _resolveEdgeRaw(cs.position, EDGE_RIGHT)
    posTop    = _resolveEdgeRaw(cs.position, EDGE_TOP)
    posBottom = _resolveEdgeRaw(cs.position, EDGE_BOTTOM)

    rLeft   = resolveValue(posLeft,   parentWidth)
    rRight  = resolveValue(posRight,  parentWidth)
    rTop    = resolveValue(posTop,    parentHeight)
    rBottom = resolveValue(posBottom, parentHeight)

    padBoxW = parentWidth  - bor[EDGE_LEFT] - bor[EDGE_RIGHT]
    padBoxH = parentHeight - bor[EDGE_TOP]  - bor[EDGE_BOTTOM]

    cw = resolveValue(cs.width,  padBoxW)
    ch = resolveValue(cs.height, padBoxH)

    if not _isDefined(cw) and _isDefined(rLeft) and _isDefined(rRight):
        cw = padBoxW - rLeft - rRight
    if not _isDefined(ch) and _isDefined(rTop) and _isDefined(rBottom):
        ch = padBoxH - rTop - rBottom

    _layoutNode(
        child, cw, ch,
        MeasureMode.Exactly    if _isDefined(cw) else MeasureMode.Undefined,
        MeasureMode.Exactly    if _isDefined(ch) else MeasureMode.Undefined,
        padBoxW, padBoxH, True,
    )

    mL = _resolveEdge(cs.margin, EDGE_LEFT,   parentWidth)
    mT = _resolveEdge(cs.margin, EDGE_TOP,    parentWidth)
    mR = _resolveEdge(cs.margin, EDGE_RIGHT,  parentWidth)
    mB = _resolveEdge(cs.margin, EDGE_BOTTOM, parentWidth)

    mainAxis    = parent.style.flexDirection
    reversed_   = _isReverse(mainAxis)
    mainRow     = _isRow(mainAxis)
    wrapReverse = parent.style.flexWrap == Wrap.WrapReverse
    alignment   = parent.style.alignItems if cs.alignSelf == Align.Auto else cs.alignSelf

    if _isDefined(rLeft):
        left = bor[EDGE_LEFT] + rLeft + mL
    elif _isDefined(rRight):
        left = parentWidth - bor[EDGE_RIGHT] - rRight - child.layout.width - mR
    elif mainRow:
        lead  = pad[EDGE_LEFT] + bor[EDGE_LEFT]
        trail = parentWidth - pad[EDGE_RIGHT] - bor[EDGE_RIGHT]
        if reversed_:
            left = trail - child.layout.width - mR
        else:
            left = _justifyAbsolute(parent.style.justifyContent, lead, trail, child.layout.width) + mL
    else:
        left = _alignAbsolute(
            alignment,
            pad[EDGE_LEFT] + bor[EDGE_LEFT],
            parentWidth - pad[EDGE_RIGHT] - bor[EDGE_RIGHT],
            child.layout.width, wrapReverse,
        ) + mL

    if _isDefined(rTop):
        top = bor[EDGE_TOP] + rTop + mT
    elif _isDefined(rBottom):
        top = parentHeight - bor[EDGE_BOTTOM] - rBottom - child.layout.height - mB
    elif mainRow:
        top = _alignAbsolute(
            alignment,
            pad[EDGE_TOP] + bor[EDGE_TOP],
            parentHeight - pad[EDGE_BOTTOM] - bor[EDGE_BOTTOM],
            child.layout.height, wrapReverse,
        ) + mT
    else:
        lead  = pad[EDGE_TOP] + bor[EDGE_TOP]
        trail = parentHeight - pad[EDGE_BOTTOM] - bor[EDGE_BOTTOM]
        if reversed_:
            top = trail - child.layout.height - mB
        else:
            top = _justifyAbsolute(parent.style.justifyContent, lead, trail, child.layout.height) + mT

    child.layout.left = left
    child.layout.top  = top

# ─── Rounding ─────────────────────────────────────────────────────────────────

def _isWholeNumber(v: float) -> bool:
    frac = v - math.floor(v)
    return frac < 0.0001 or frac > 0.9999

def _roundValue(v: float, scale: float, forceCeil: bool, forceFloor: bool) -> float:
    scaled = v * scale
    frac   = scaled - math.floor(scaled)
    if frac < 0: frac += 1
    if frac < 0.0001:
        scaled = math.floor(scaled)
    elif frac > 0.9999:
        scaled = math.ceil(scaled)
    elif forceCeil:
        scaled = math.ceil(scaled)
    elif forceFloor:
        scaled = math.floor(scaled)
    else:
        scaled = math.floor(scaled) + (1 if frac >= 0.4999 else 0)
    return scaled / scale

def _roundLayout(node: Node, scale: float, absLeft: float, absTop: float) -> None:
    if scale == 0: return
    l          = node.layout
    nodeLeft   = l.left
    nodeTop    = l.top
    nodeWidth  = l.width
    nodeHeight = l.height
    absNodeLeft = absLeft + nodeLeft
    absNodeTop  = absTop  + nodeTop
    isText = node.measureFunc is not None
    l.left = _roundValue(nodeLeft, scale, False, isText)
    l.top  = _roundValue(nodeTop,  scale, False, isText)
    absRight  = absNodeLeft + nodeWidth
    absBottom = absNodeTop  + nodeHeight
    hasFracW  = not _isWholeNumber(nodeWidth  * scale)
    hasFracH  = not _isWholeNumber(nodeHeight * scale)
    l.width  = (
        _roundValue(absRight,     scale, isText and hasFracW,  isText and not hasFracW)
        - _roundValue(absNodeLeft, scale, False, isText)
    )
    l.height = (
        _roundValue(absBottom,    scale, isText and hasFracH,  isText and not hasFracH)
        - _roundValue(absNodeTop,  scale, False, isText)
    )
    for c in node.children:
        _roundLayout(c, scale, absNodeLeft, absNodeTop)

# ─── parseDimension ───────────────────────────────────────────────────────────

def parseDimension(v: Any) -> Value:
    """Convert a raw user value (number, 'auto', '50%', etc.) to a Value."""
    if v is None or v is UNDEFINED_VALUE:
        return UNDEFINED_VALUE
    if v is AUTO_VALUE:
        return AUTO_VALUE
    if isinstance(v, Value):
        return v
    if isinstance(v, str):
        if v == "auto":
            return AUTO_VALUE
        if v.endswith("%"):
            try: return percentValue(float(v[:-1]))
            except ValueError: return UNDEFINED_VALUE
        try: n = float(v)
        except ValueError: return UNDEFINED_VALUE
        return pointValue(n) if math.isfinite(n) else UNDEFINED_VALUE
    if isinstance(v, (int, float)):
        fv = float(v)
        return pointValue(fv) if math.isfinite(fv) else UNDEFINED_VALUE
    return UNDEFINED_VALUE

# ─── Core layoutNode ──────────────────────────────────────────────────────────

def _layoutNode(
    node: Node,
    availableWidth:  float,
    availableHeight: float,
    widthMode:  int,
    heightMode: int,
    ownerWidth:  float,
    ownerHeight: float,
    performLayout: bool,
    forceWidth:  Optional[float] = None,
    forceHeight: Optional[float] = None,
) -> None:
    """Core recursive flexbox layout — mirrors layoutNode() in TS."""
    global _yogaNodesVisited, _yogaMeasureCalls, _yogaCacheHits

    _yogaNodesVisited += 1

    style  = node.style
    isMainRow = _isRow(style.flexDirection)
    mainAxis  = style.flexDirection
    crossAx   = _crossAxis(mainAxis)

    # Cache hit (skip layout if inputs unchanged and node clean)
    wasDirty = node.isDirty_
    if _cacheHit(node, availableWidth, availableHeight, widthMode, heightMode,
                 ownerWidth, ownerHeight, forceWidth, forceHeight):
        _yogaCacheHits += 1
        node.layout.width  = node._lOutW
        node.layout.height = node._lOutH
        node.isDirty_ = False
        return

    # Measure function (leaf node)
    if node.measureFunc is not None and not node.children:
        _yogaMeasureCalls += 1
        # Check measure cache
        if (node._hasM
                and _sameFloat(node._mW, availableWidth)
                and node._mWM == widthMode
                and _sameFloat(node._mH, availableHeight)
                and node._mHM == heightMode
                and _sameFloat(node._mOW, ownerWidth)
                and _sameFloat(node._mOH, ownerHeight)):
            node.layout.width  = node._mOutW
            node.layout.height = node._mOutH
        else:
            mw = availableWidth  if _isDefined(availableWidth)  else float("nan")
            mh = availableHeight if _isDefined(availableHeight) else float("nan")
            try:
                result = node.measureFunc(mw, widthMode, mh, heightMode)
                rw = float(result.get("width",  0) if isinstance(result, dict) else result[0])
                rh = float(result.get("height", 0) if isinstance(result, dict) else result[1])
            except Exception:
                rw = rh = 0.0
            node.layout.width  = _boundAxis(style, True,  rw, ownerWidth, ownerHeight)
            node.layout.height = _boundAxis(style, False, rh, ownerWidth, ownerHeight)
            node._mW = availableWidth; node._mH = availableHeight
            node._mWM = widthMode;     node._mHM = heightMode
            node._mOW = ownerWidth;    node._mOH = ownerHeight
            node._mOutW = node.layout.width
            node._mOutH = node.layout.height
            node._hasM = True
        _cacheWrite(node, availableWidth, availableHeight, widthMode, heightMode,
                    ownerWidth, ownerHeight, forceWidth, forceHeight, wasDirty)
        node.isDirty_ = False
        return

    # Resolve padding and border
    pad = [0.0] * 4
    bor = [0.0] * 4
    _resolveEdges4Into(style.padding, ownerWidth, pad)
    _resolveEdges4Into(style.border,  ownerWidth, bor)

    # Available inner dimensions
    mainLeadPB  = pad[_leadingEdge(mainAxis)]  + bor[_leadingEdge(mainAxis)]
    mainTrailPB = pad[_trailingEdge(mainAxis)] + bor[_trailingEdge(mainAxis)]
    crossLeadPB = pad[_leadingEdge(crossAx)]   + bor[_leadingEdge(crossAx)]
    crossTrailPB = pad[_trailingEdge(crossAx)] + bor[_trailingEdge(crossAx)]
    mainPadBorder  = mainLeadPB  + mainTrailPB
    crossPadBorder = crossLeadPB + crossTrailPB

    mainSize_  = availableWidth  if isMainRow else availableHeight
    crossSize_ = availableHeight if isMainRow else availableWidth
    mainMode   = widthMode  if isMainRow else heightMode
    crossMode  = heightMode if isMainRow else widthMode

    innerMainSize  = mainSize_  - mainPadBorder  if _isDefined(mainSize_)  else float("nan")
    innerCrossSize = crossSize_ - crossPadBorder if _isDefined(crossSize_) else float("nan")

    # Collect flow and absolute children
    flowChildren: list[Node] = []
    absChildren:  list[Node] = []
    _collectLayoutChildren(node, flowChildren, absChildren)

    # STEP 1: Determine flex-basis for each flow child
    isWrap = style.flexWrap != Wrap.NoWrap
    gapMain  = _resolveGap(style, Gutter.Column if isMainRow else Gutter.Row,   innerMainSize)
    gapCross = _resolveGap(style, Gutter.Row    if isMainRow else Gutter.Column, innerCrossSize)

    for c in flowChildren:
        c._flexBasis = _computeFlexBasis(
            c, mainAxis,
            innerMainSize  if _isDefined(innerMainSize)  else float("nan"),
            innerCrossSize if _isDefined(innerCrossSize) else float("nan"),
            crossMode, ownerWidth, ownerHeight,
        )

    # STEP 2: Line breaking
    lines: list[list[Node]] = []
    current_line: list[Node] = []
    line_used = 0.0

    for i, c in enumerate(flowChildren):
        c._hasAutoMargin = c._hasMargin and _hasAnyAutoEdge(c.style.margin)
        cm = _childMarginForAxis(c, mainAxis, ownerWidth)
        item_size = c._flexBasis + cm

        if isWrap and _isDefined(innerMainSize) and current_line:
            consumed = line_used + item_size
            if i > (len(lines) * 0) and consumed > innerMainSize + 1e-6:
                lines.append(current_line)
                current_line = []
                line_used = 0.0

        current_line.append(c)
        line_used += item_size + (gapMain if current_line else 0)

    if current_line:
        lines.append(current_line)

    if not lines:
        lines = [[]]

    lineCount = len(lines)
    lineConsumedMain = [0.0] * lineCount
    lineCrossSizes   = [0.0] * lineCount
    lineMaxAscent    = [0.0] * lineCount

    isBaseline = _isBaselineLayout(node, flowChildren)
    maxLineMain = 0.0
    totalLinesCross = 0.0

    for li, line in enumerate(lines):
        # STEP 3: Flex distribution
        totalFlexBasis = 0.0
        for c in line:
            totalFlexBasis += c._flexBasis + _childMarginForAxis(c, mainAxis, ownerWidth)
        totalFlexBasis += gapMain * (len(line) - 1) if len(line) > 1 else 0

        _resolveFlexibleLengths(line, innerMainSize, totalFlexBasis,
                                isMainRow, ownerWidth, ownerHeight)

        # Lay out each child at its resolved main size
        lineCross = 0.0
        for c in line:
            cMarginCross = _childMarginForAxis(c, crossAx, ownerWidth)
            # Determine cross constraint
            crossStyleDef = _isDefined(resolveValue(
                c.style.height if isMainRow else c.style.width,
                ownerHeight    if isMainRow else ownerWidth,
            ))
            hasCrossAutoMargin = (
                c._hasAutoMargin
                and (_isMarginAuto(c.style.margin, EDGE_TOP)
                     or _isMarginAuto(c.style.margin, EDGE_BOTTOM))
                if isMainRow else
                c._hasAutoMargin
                and (_isMarginAuto(c.style.margin, EDGE_LEFT)
                     or _isMarginAuto(c.style.margin, EDGE_RIGHT))
            )
            childAlign = _resolveChildAlign(node, c)
            if (childAlign == Align.Stretch and not crossStyleDef
                    and not hasCrossAutoMargin and _isDefined(innerCrossSize)):
                cCross = max(0.0, innerCrossSize - cMarginCross)
                _layoutNode(c, c._mainSize if isMainRow else cCross,
                            cCross if isMainRow else c._mainSize,
                            MeasureMode.Exactly, MeasureMode.Exactly,
                            ownerWidth, ownerHeight, performLayout,
                            isMainRow, not isMainRow)
            else:
                crossConstraint = resolveValue(
                    c.style.height if isMainRow else c.style.width,
                    ownerHeight    if isMainRow else ownerWidth,
                )
                if _isDefined(crossConstraint):
                    cCrossMode = MeasureMode.Exactly
                    cCross = crossConstraint
                elif _isDefined(innerCrossSize):
                    cCrossMode = MeasureMode.AtMost
                    cCross = max(0.0, innerCrossSize - cMarginCross)
                else:
                    cCrossMode = MeasureMode.Undefined
                    cCross = float("nan")
                _layoutNode(c, c._mainSize if isMainRow else cCross,
                            cCross if isMainRow else c._mainSize,
                            MeasureMode.Exactly,
                            cCrossMode if isMainRow else MeasureMode.Exactly,
                            ownerWidth, ownerHeight, performLayout,
                            isMainRow, not isMainRow)

            c._crossSize = c.layout.height if isMainRow else c.layout.width
            lineCross = max(lineCross, c._crossSize + cMarginCross)

        # Baseline layout adjustment
        if isBaseline:
            maxAscent = maxDescent = 0.0
            for c in line:
                if _resolveChildAlign(node, c) != Align.Baseline: continue
                mTop = _resolveEdge(c.style.margin, EDGE_TOP,    ownerWidth)
                mBot = _resolveEdge(c.style.margin, EDGE_BOTTOM, ownerWidth)
                asc  = _calculateBaseline(c) + mTop
                desc = c.layout.height + mTop + mBot - asc
                if asc  > maxAscent:  maxAscent  = asc
                if desc > maxDescent: maxDescent = desc
            lineMaxAscent[li] = maxAscent
            if maxAscent + maxDescent > lineCross:
                lineCross = maxAscent + maxDescent

        # Accumulate line consumed-main
        mainLead  = _leadingEdge(mainAxis)
        mainTrail = _trailingEdge(mainAxis)
        consumed  = gapMain * (len(line) - 1) if len(line) > 1 else 0.0
        for c in line:
            cm = c.layout.margin
            consumed += c._mainSize + cm[mainLead] + cm[mainTrail]
        lineConsumedMain[li] = consumed
        lineCrossSizes[li]   = lineCross
        maxLineMain = max(maxLineMain, consumed)
        totalLinesCross += lineCross

    totalCrossGap = gapCross * (lineCount - 1) if lineCount > 1 else 0.0
    totalLinesCross += totalCrossGap

    # STEP 4: Container dimensions
    isScroll    = style.overflow == Overflow.Scroll
    contentMain = maxLineMain + mainPadBorder
    finalMainSize = (
        mainSize_ if mainMode == MeasureMode.Exactly
        else (max(min(mainSize_, contentMain), mainPadBorder) if mainMode == MeasureMode.AtMost and isScroll
              else (mainSize_ if isWrap and lineCount > 1 and mainMode == MeasureMode.AtMost
                    else contentMain))
    )
    contentCross = totalLinesCross + crossPadBorder
    finalCrossSize = (
        crossSize_ if crossMode == MeasureMode.Exactly
        else (max(min(crossSize_, contentCross), crossPadBorder) if crossMode == MeasureMode.AtMost and isScroll
              else contentCross)
    )

    node.layout.width  = _boundAxis(style, True,  finalMainSize  if isMainRow  else finalCrossSize, ownerWidth, ownerHeight)
    node.layout.height = _boundAxis(style, False, finalCrossSize if isMainRow  else finalMainSize,  ownerWidth, ownerHeight)
    _commitCacheOutputs(node, performLayout)
    _cacheWrite(node, availableWidth, availableHeight, widthMode, heightMode,
                ownerWidth, ownerHeight, forceWidth, forceHeight, wasDirty)

    node.isDirty_ = False

    if not performLayout:
        return

    # STEP 5: Position lines (align-content) and children
    actualInnerMain  = (node.layout.width  if isMainRow else node.layout.height) - mainPadBorder
    actualInnerCross = (node.layout.height if isMainRow else node.layout.width)  - crossPadBorder
    mainLeadEdgePhys  = _leadingEdge(mainAxis)
    mainTrailEdgePhys = _trailingEdge(mainAxis)
    crossLeadEdgePhys  = EDGE_TOP  if isMainRow else EDGE_LEFT
    crossTrailEdgePhys = EDGE_BOTTOM if isMainRow else EDGE_RIGHT
    reversed_   = _isReverse(mainAxis)
    mainContainerSize  = node.layout.width  if isMainRow else node.layout.height
    crossContainerSize = node.layout.height if isMainRow else node.layout.width
    crossLead = pad[crossLeadEdgePhys] + bor[crossLeadEdgePhys]

    # Align-content: distribute cross space among lines
    lineCrossOffset = crossLead
    betweenLines    = gapCross
    freeCross = actualInnerCross - totalLinesCross
    if lineCount == 1 and not isWrap and not isBaseline:
        lineCrossSizes[0] = actualInnerCross
    else:
        remCross = max(0.0, freeCross)
        ac = style.alignContent
        if ac == Align.Center:
            lineCrossOffset += freeCross / 2
        elif ac == Align.FlexEnd:
            lineCrossOffset += freeCross
        elif ac == Align.Stretch and lineCount > 0 and remCross > 0:
            add = remCross / lineCount
            for i in range(lineCount):
                lineCrossSizes[i] += add
        elif ac == Align.SpaceBetween and lineCount > 1:
            betweenLines += remCross / (lineCount - 1)
        elif ac == Align.SpaceAround and lineCount > 0:
            betweenLines    += remCross / lineCount
            lineCrossOffset += remCross / lineCount / 2
        elif ac == Align.SpaceEvenly and lineCount > 0:
            betweenLines    += remCross / (lineCount + 1)
            lineCrossOffset += remCross / (lineCount + 1)

    wrapReverse = style.flexWrap == Wrap.WrapReverse
    lineCrossPos = lineCrossOffset

    for li, line in enumerate(lines):
        lineCross    = lineCrossSizes[li]
        consumedMain = lineConsumedMain[li]
        n = len(line)

        # Re-stretch children if needed
        if isWrap or crossMode != MeasureMode.Exactly:
            for c in line:
                cStyle    = c.style
                childAlign = _resolveChildAlign(node, c)
                crossStyleDef = _isDefined(resolveValue(
                    cStyle.height if isMainRow else cStyle.width,
                    ownerHeight   if isMainRow else ownerWidth,
                ))
                hasCrossAutoMargin = (
                    c._hasAutoMargin and (
                        _isMarginAuto(cStyle.margin, crossLeadEdgePhys)
                        or _isMarginAuto(cStyle.margin, crossTrailEdgePhys)
                    )
                )
                if childAlign == Align.Stretch and not crossStyleDef and not hasCrossAutoMargin:
                    cMarginCross = _childMarginForAxis(c, crossAx, ownerWidth)
                    target = max(0.0, lineCross - cMarginCross)
                    if not _sameFloat(c._crossSize, target):
                        cw = c._mainSize if isMainRow else target
                        ch = target      if isMainRow else c._mainSize
                        _layoutNode(c, cw, ch, MeasureMode.Exactly, MeasureMode.Exactly,
                                    ownerWidth, ownerHeight, performLayout,
                                    isMainRow, not isMainRow)
                        c._crossSize = target

        # Justify-content + auto margins
        mainOffset_    = pad[mainLeadEdgePhys] + bor[mainLeadEdgePhys]
        betweenMain    = gapMain
        numAutoMain    = 0
        for c in line:
            if not c._hasAutoMargin: continue
            if _isMarginAuto(c.style.margin, mainLeadEdgePhys):  numAutoMain += 1
            if _isMarginAuto(c.style.margin, mainTrailEdgePhys): numAutoMain += 1
        freeMain      = actualInnerMain - consumedMain
        remainingMain = max(0.0, freeMain)
        autoMarginMainSize = (remainingMain / numAutoMain) if numAutoMain > 0 and remainingMain > 0 else 0.0

        if numAutoMain == 0:
            jc = style.justifyContent
            if jc == Justify.Center:
                mainOffset_ += freeMain / 2
            elif jc == Justify.FlexEnd:
                mainOffset_ += freeMain
            elif jc == Justify.SpaceBetween and n > 1:
                betweenMain += remainingMain / (n - 1)
            elif jc == Justify.SpaceAround and n > 0:
                betweenMain  += remainingMain / n
                mainOffset_  += remainingMain / n / 2
            elif jc == Justify.SpaceEvenly and n > 0:
                betweenMain  += remainingMain / (n + 1)
                mainOffset_  += remainingMain / (n + 1)

        effectiveLineCrossPos = (
            crossContainerSize - lineCrossPos - lineCross
            if wrapReverse else lineCrossPos
        )

        pos = mainOffset_
        for c in line:
            cMargin      = c.style.margin
            cLayoutMargin = c.layout.margin
            mMainLead  = mMainTrail = mCrossLead = mCrossTrail = 0.0
            if c._hasAutoMargin:
                aml = _isMarginAuto(cMargin, mainLeadEdgePhys)
                amt = _isMarginAuto(cMargin, mainTrailEdgePhys)
                acl = _isMarginAuto(cMargin, crossLeadEdgePhys)
                act = _isMarginAuto(cMargin, crossTrailEdgePhys)
                mMainLead  = autoMarginMainSize if aml else cLayoutMargin[mainLeadEdgePhys]
                mMainTrail = autoMarginMainSize if amt else cLayoutMargin[mainTrailEdgePhys]
                mCrossLead  = 0.0 if acl else cLayoutMargin[crossLeadEdgePhys]
                mCrossTrail = 0.0 if act else cLayoutMargin[crossTrailEdgePhys]
            else:
                mMainLead   = cLayoutMargin[mainLeadEdgePhys]
                mMainTrail  = cLayoutMargin[mainTrailEdgePhys]
                mCrossLead  = cLayoutMargin[crossLeadEdgePhys]
                mCrossTrail = cLayoutMargin[crossTrailEdgePhys]

            mainPos = (
                mainContainerSize - (pos + mMainLead) - c._mainSize
                if reversed_ else pos + mMainLead
            )

            childAlign = _resolveChildAlign(node, c)
            crossPos   = effectiveLineCrossPos + mCrossLead
            crossFree  = lineCross - c._crossSize - mCrossLead - mCrossTrail

            if c._hasAutoMargin:
                acl = _isMarginAuto(cMargin, crossLeadEdgePhys)
                act = _isMarginAuto(cMargin, crossTrailEdgePhys)
                if acl and act:
                    crossPos += max(0.0, crossFree) / 2
                elif acl:
                    crossPos += max(0.0, crossFree)
            else:
                if childAlign == Align.Center:
                    crossPos += crossFree / 2
                elif childAlign == Align.FlexEnd:
                    if not wrapReverse: crossPos += crossFree
                elif childAlign in (Align.FlexStart, Align.Stretch):
                    if wrapReverse: crossPos += crossFree
                elif childAlign == Align.Baseline and isBaseline:
                    crossPos = effectiveLineCrossPos + lineMaxAscent[li] - _calculateBaseline(c)

            # Relative position offsets
            relX = relY = 0.0
            if c._hasPosition:
                relLeft   = resolveValue(_resolveEdgeRaw(c.style.position, EDGE_LEFT),  ownerWidth)
                relRight  = resolveValue(_resolveEdgeRaw(c.style.position, EDGE_RIGHT), ownerWidth)
                relTop    = resolveValue(_resolveEdgeRaw(c.style.position, EDGE_TOP),   ownerWidth)
                relBottom = resolveValue(_resolveEdgeRaw(c.style.position, EDGE_BOTTOM),ownerWidth)
                relX = relLeft  if _isDefined(relLeft)  else (-relRight  if _isDefined(relRight)  else 0.0)
                relY = relTop   if _isDefined(relTop)   else (-relBottom if _isDefined(relBottom) else 0.0)

            if isMainRow:
                c.layout.left = mainPos + relX
                c.layout.top  = crossPos + relY
            else:
                c.layout.left = crossPos + relX
                c.layout.top  = mainPos  + relY

            pos += c._mainSize + mMainLead + mMainTrail + betweenMain

        lineCrossPos += lineCross + betweenLines

    # STEP 6: Absolute children
    for c in absChildren:
        _layoutAbsoluteChild(node, c, node.layout.width, node.layout.height, pad, bor)

# ─── Yoga module API (matches yoga-layout/load shape) ─────────────────────────

class Yoga:
    class Config:
        @staticmethod
        def create() -> Config:
            return createConfig()
        @staticmethod
        def destroy(config: Config) -> None:
            pass

    class Node:
        @staticmethod
        def create(config: Optional[Config] = None) -> "Node":
            return Node(config)
        @staticmethod
        def createDefault() -> "Node":
            return Node()
        @staticmethod
        def createWithConfig(config: Config) -> "Node":
            return Node(config)
        @staticmethod
        def destroy(node: "Node") -> None:
            node.free()


_YOGA_INSTANCE = Yoga()


async def loadYoga() -> Yoga:
    """Return the Yoga singleton (async for API compatibility with WASM loader)."""
    return _YOGA_INSTANCE
