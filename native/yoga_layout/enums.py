"""Yoga-layout enum constants — mirrors src/native-ts/yoga-layout/enums.ts.

The TypeScript source uses `const` objects with `as const` rather than TS
enums. We mirror the same pattern here: plain integer constants grouped inside
classes (class acts as a namespace). All integer values are identical to the
TS original so they interop correctly with the layout algorithm.

Display.None_ is named with a trailing underscore because Python reserves
`None` as a keyword. The value (1) is identical to the TS `None: 1`.
"""
from __future__ import annotations


class Align:
    Auto         = 0
    FlexStart    = 1
    Center       = 2
    FlexEnd      = 3
    Stretch      = 4
    Baseline     = 5
    SpaceBetween = 6
    SpaceAround  = 7
    SpaceEvenly  = 8


class BoxSizing:
    BorderBox  = 0
    ContentBox = 1


class Dimension:
    Width  = 0
    Height = 1


class Direction:
    Inherit = 0
    LTR     = 1
    RTL     = 2


class Display:
    Flex     = 0
    None_    = 1   # Python cannot use `None` as an attribute name
    Contents = 2


class Edge:
    Left       = 0
    Top        = 1
    Right      = 2
    Bottom     = 3
    Start      = 4
    End        = 5
    Horizontal = 6
    Vertical   = 7
    All        = 8


class Errata:
    """Bitmask flags — combine with bitwise OR."""
    # TS: None: 0 (Python: None_ to avoid keyword clash)
    None_                                          = 0
    StretchFlexBasis                               = 1
    AbsolutePositionWithoutInsetsExcludesPadding   = 2
    AbsolutePercentAgainstInnerSize                = 4
    All                                            = 2147483647
    Classic                                        = 2147483646


class ExperimentalFeature:
    WebFlexBasis = 0


class FlexDirection:
    Column        = 0
    ColumnReverse = 1
    Row           = 2
    RowReverse    = 3


class Gutter:
    Column = 0
    Row    = 1
    All    = 2


class Justify:
    FlexStart    = 0
    Center       = 1
    FlexEnd      = 2
    SpaceBetween = 3
    SpaceAround  = 4
    SpaceEvenly  = 5


class MeasureMode:
    Undefined = 0
    Exactly   = 1
    AtMost    = 2


class Overflow:
    Visible = 0
    Hidden  = 1
    Scroll  = 2


class PositionType:
    Static   = 0
    Relative = 1
    Absolute = 2


class Unit:
    Undefined = 0
    Point     = 1
    Percent   = 2
    Auto      = 3


class Wrap:
    NoWrap      = 0
    Wrap        = 1
    WrapReverse = 2
