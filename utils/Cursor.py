"""
    pass of src/utils/Cursor
"""
from __future__ import annotations

from typing import Any, Optional, Union, Callable, List, Dict, Tuple, Set, Literal, TYPE_CHECKING
import re
import hashlib
import glob
import math
from enum import Enum, auto
from collections import defaultdict
import struct


WrappedText = List[str]
Position = Dict[str, Any]


class Cursor:
    def __init__(self, offset=None, measuredText=None, selection=None, text=None, columns=None, cursorChar=None, mask=None, invert=None, ghostText=None, maxVisibleLines=None, lineStart=None, lineEnd=None, targetColumn=None, char=None, type=None, count=None):
        self.offset = offset
        self.measuredText = measuredText
        self.selection = selection
        self.text = text
        self.columns = columns
        self.cursorChar = cursorChar
        self.mask = mask
        self.invert = invert
        self.ghostText = ghostText
        self.maxVisibleLines = maxVisibleLines
        self.lineStart = lineStart
        self.lineEnd = lineEnd
        self.targetColumn = targetColumn
        self.char = char
        self.type = type
        self.count = count



class WrappedLine:
    def __init__(self, text=None, startOffset=None, isPrecededByNewline=None, endsWithNewline=None):
        self.text = text
        self.startOffset = startOffset
        self.isPrecededByNewline = isPrecededByNewline
        self.endsWithNewline = endsWithNewline



class MeasuredText:
    def __init__(self, _wrappedLines=None, text=None, navigationCache=None, graphemeBoundaries=None, columns=None, boundaries=None, target=None, findNext=None):
        self._wrappedLines = _wrappedLines
        self.text = text
        self.navigationCache = navigationCache
        self.graphemeBoundaries = graphemeBoundaries
        self.columns = columns
        self.boundaries = boundaries
        self.target = target
        self.findNext = findNext



VIM_WORD_CHAR_REGEX: Any = None  # type: ignore
WHITESPACE_REGEX: Any = None  # type: ignore
isVimWordChar: Any = None  # type: ignore
isVimWhitespace: Any = None  # type: ignore
isVimPunctuation: Any = None  # type: ignore


def pushToKillRing(text, direction='append'):
    if len(text) > 0:
        if lastActionWasKill and len(killRing) > 0:
            # Accumulate with the most recent kill
            if direction == 'prepend':
                killRing[0] = text + killRing[0]
            else:
                killRing[0] = killRing[0] + text
        else:
            # Add new entry to front of ring
            killRing.unshift(text)
            if len(killRing) > KILL_RING_MAX_SIZE:
                killRing.pop()
        lastActionWasKill = True
        # Reset yank state when killing new text
        lastActionWasYank = False


def getLastKill():
    return killRing[0] if killRing[0] is not None else ''


def getKillRingItem(index):
    return index


def getKillRingSize():
    return len(killRing)


def clearKillRing():
    global killRing, killRingIndex, lastActionWasKill, lastActionWasYank, lastYankStart, lastYankLength
    killRing = []
    killRingIndex = 0
    lastActionWasKill = False
    lastActionWasYank = False
    lastYankStart = 0
    lastYankLength = 0


def resetKillAccumulation():
    global lastActionWasKill
    lastActionWasKill = False


def recordYank(start, length):
    global lastYankStart, lastYankLength, lastActionWasYank, killRingIndex
    lastYankStart = start
    lastYankLength = length
    lastActionWasYank = True
    killRingIndex = 0


def canYankPop():
    return lastActionWasYank and len(killRing) > 1


def yankPop():
    global killRingIndex
    if not lastActionWasYank or len(killRing) <= 1:
        return None
    killRingIndex = (killRingIndex + 1) % len(killRing)
    text = killRing[killRingIndex] if killRingIndex < len(killRing) else ''
    return {'text': text, 'start': lastYankStart, 'length': lastYankLength}


def updateYankLength(length):
    global lastYankLength
    lastYankLength = length


def resetYankState():
    global lastActionWasYank
    lastActionWasYank = False

