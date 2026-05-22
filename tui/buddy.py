"""Buddy/Companion system — mirrors src/buddy/CompanionSprite.tsx.

ASCII art pet with idle animations, speech bubbles, and pet reactions.
"""

from __future__ import annotations

import random
import time
from typing import Optional

# ── Sprites ────────────────────────────────────────────────

# Clawd the companion — ASCII art frames for idle animation
CLAWD_FRAMES = [
    # Frame 0: Resting
    [
        "   ╭――――――――╮",
        "   │ ◉    ◉ │",
        "   │   ▽    │",
        "   │  ╰╯   │",
        "   ╰――――――――╯",
        "   ╱        ╲",
        "  ╱   ▓▓▓▓   ╲",
        " │  ▓▓▓▓▓▓▓  │",
        " │  ▓▓▓▓▓▓▓  │",
        "  ╲  ▓▓▓▓▓  ╱",
        "   ╲       ╱",
        "    ╲_____╱",
    ],
    # Frame 1: Fidget left
    [
        "   ╭――――――――╮",
        "   │ ◉    ◉ │",
        "   │   ▽    │",
        "   │   ╰╯  │",
        "   ╰――――――――╯",
        "    ╱       ╲",
        "   ╱  ▓▓▓▓   ╲",
        "  │  ▓▓▓▓▓▓▓  │",
        "  │  ▓▓▓▓▓▓▓  │",
        "   ╲  ▓▓▓▓▓  ╱",
        "    ╲       ╱",
        "     ╲_____╱",
    ],
    # Frame 2: Fidget right
    [
        "   ╭――――――――╮",
        "   │ ◉    ◉ │",
        "   │    ▽   │",
        "   │   ╰╯  │",
        "   ╰――――――――╯",
        "   ╱        ╲",
        "  ╱   ▓▓▓▓   ╲",
        " │  ▓▓▓▓▓▓▓  │",
        " │  ▓▓▓▓▓▓▓  │",
        "  ╲  ▓▓▓▓▓  ╱",
        "   ╲       ╱",
        "    ╲_____╱",
    ],
]

# Simplified companion for narrow terminals
CLAWD_SMALL = [
    "  ╭――――╮",
    "  │◉  ◉│",
    "  │  ▽ │",
    "  ╰――――╯",
    "  ╱    ╲",
    " ╱ ▓▓▓▓ ╲",
    "╱ ▓▓▓▓▓ ╲",
]

# ── Speech Bubbles ─────────────────────────────────────────

IDLE_BUBBLES = [
    "Ready to help!",
    "What's next?",
    "I'm here!",
    "Thinking cap on!",
    "Let's build something!",
    "At your service!",
    "How can I assist?",
    "Ready when you are!",
]

WORKING_BUBBLES = [
    "Working on it...",
    "Let me think...",
    "Processing...",
    "Almost there...",
    "Analyzing...",
    "Reading files...",
    "Searching...",
]

SUCCESS_BUBBLES = [
    "Done! ✨",
    "All set!",
    "Finished!",
    "Complete!",
    "Nailed it!",
]

ERROR_BUBBLES = [
    "Hmm, that didn't work.",
    "Let me try again...",
    "Oops!",
    "That's odd...",
]


# ── Buddy Manager ──────────────────────────────────────────

class BuddyManager:
    """Manages the companion sprite, animations, and speech bubbles."""

    TICK_MS = 500
    BUBBLE_SHOW = 20  # ticks (~10s)
    FADE_WINDOW = 6   # last ~3s dim

    # Idle sequence: mostly rest (frame 0), occasional fidget (1-2), rare blink (-1)
    IDLE_SEQUENCE = [0, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 2, 0, 0, 0]

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._tick = 0
        self._seq_idx = 0
        self._bubble: Optional[str] = None
        self._bubble_ticks = 0
        self._bubble_color = "inactive"
        self._pet_hearts_until = 0.0
        self._last_bubble_time = 0.0
        self._mood = "neutral"  # neutral, working, happy, sad

    @property
    def mood(self) -> str:
        return self._mood

    @mood.setter
    def mood(self, value: str):
        self._mood = value

    def tick(self):
        """Advance animation by one tick."""
        self._tick += 1
        self._seq_idx = (self._seq_idx + 1) % len(self.IDLE_SEQUENCE)

        # Manage bubble lifetime
        if self._bubble:
            self._bubble_ticks += 1
            if self._bubble_ticks >= self.BUBBLE_SHOW:
                self._bubble = None
                self._bubble_ticks = 0

        # Random idle bubbles
        if not self._bubble and self._mood == "neutral":
            if random.random() < 0.02:  # 2% chance per tick
                self._bubble = random.choice(IDLE_BUBBLES)
                self._bubble_ticks = 0
                self._bubble_color = "inactive"

    def say(self, text: str, color: str = "inactive"):
        """Make the buddy say something."""
        self._bubble = text
        self._bubble_ticks = 0
        self._bubble_color = color

    def pet(self):
        """Pet the buddy — shows hearts."""
        self._pet_hearts_until = time.time() + 2.5
        self._mood = "happy"
        self.say("Purrr... ♥", "vivian")

    def set_working(self):
        self._mood = "working"
        if not self._bubble:
            self.say(random.choice(WORKING_BUBBLES), "vivian")

    def set_idle(self):
        self._mood = "neutral"

    def set_success(self):
        self._mood = "happy"
        self.say(random.choice(SUCCESS_BUBBLES), "success")

    def set_error(self):
        self._mood = "sad"
        self.say(random.choice(ERROR_BUBBLES), "error")

    def get_current_frame(self, narrow: bool = False) -> list[str]:
        """Get the current sprite frame."""
        if narrow:
            return CLAWD_SMALL

        seq_val = self.IDLE_SEQUENCE[self._seq_idx]
        if seq_val == -1:
            # Blink on frame 0
            frame = CLAWD_FRAMES[0].copy()
            frame[1] = "   │ –    – │"  # Blink eyes
            return frame
        return CLAWD_FRAMES[seq_val]

    def get_bubble(self) -> Optional[tuple[str, str]]:
        """Get current speech bubble (text, color)."""
        if not self._bubble:
            return None
        fading = self._bubble_ticks >= (self.BUBBLE_SHOW - self.FADE_WINDOW)
        color = "inactive" if fading else self._bubble_color
        return (self._bubble, color)

    def get_hearts(self) -> Optional[list[str]]:
        """Get floating hearts if pet animation is active."""
        if time.time() < self._pet_hearts_until:
            elapsed = 2.5 - (self._pet_hearts_until - time.time())
            idx = min(int(elapsed / 0.5), 4)
            H = "♥"
            hearts = [
                f"   {H}    {H}   ",
                f"  {H}  {H}   {H}  ",
                f" {H}   {H}  {H}   ",
                f"{H}  {H}      {H} ",
                "·    ·   ·  ",
            ]
            return hearts[: idx + 1]
        return None

    def render(self, width: int = 80) -> str:
        """Render the full buddy display."""
        if not self.enabled:
            return ""

        narrow = width < 60
        lines: list[str] = []

        # Hearts
        hearts = self.get_hearts()
        if hearts:
            lines.extend(hearts)

        # Speech bubble
        bubble = self.get_bubble()
        if bubble:
            text, color = bubble
            bubble_lines = self._wrap_bubble(text, 30)
            for i, bl in enumerate(bubble_lines):
                prefix = "  " if i == 0 else "  "
                lines.append(f"{prefix}{bl}")

        # Sprite
        frame = self.get_current_frame(narrow)
        lines.extend(frame)

        return "\n".join(lines)

    @staticmethod
    def _wrap_bubble(text: str, width: int) -> list[str]:
        """Wrap bubble text to width."""
        words = text.split()
        result: list[str] = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 > width and current:
                result.append(current)
                current = w
            else:
                current = f"{current} {w}" if current else w
        if current:
            result.append(current)
        return result
