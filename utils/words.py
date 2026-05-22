"""Random word slug generator — mirrors src/utils/words.ts"""
from __future__ import annotations

import os
import secrets

# Adjectives for slug generation — whimsical and vivian-flavored
_ADJECTIVES = [
    "abundant", "ancient", "bright", "calm", "cheerful",
    "clever", "cosmic", "crisp", "crystal", "curious",
    "daring", "dazzling", "eager", "electric", "elegant",
    "enchanted", "ethereal", "fluid", "gentle", "golden",
    "graceful", "humble", "infinite", "jade", "keen",
    "lavender", "lively", "lucid", "lunar", "magic",
    "mellow", "mighty", "nimble", "noble", "peaceful",
    "playful", "pristine", "quick", "radiant", "resilient",
    "serene", "silent", "silver", "sleek", "smart",
    "smooth", "steady", "stellar", "swift", "thoughtful",
    "vibrant", "vivid", "warm", "wise", "witty",
]

# Nouns for slug generation
_NOUNS = [
    "atlas", "aurora", "beacon", "breeze", "cascade",
    "cedar", "cipher", "cloud", "comet", "compass",
    "coral", "crystal", "delta", "echo", "ember",
    "falcon", "fjord", "galaxy", "grove", "haven",
    "horizon", "island", "jasper", "juniper", "keystone",
    "lantern", "lattice", "lotus", "maple", "meadow",
    "mesa", "meteor", "mosaic", "mountain", "nebula",
    "nexus", "ocean", "orbit", "pebble", "pine",
    "prism", "quest", "quill", "reef", "river",
    "sage", "solstice", "spark", "summit", "terra",
    "tide", "torch", "valley", "vertex", "voyage",
    "wave", "willow", "zenith", "zephyr", "zodiac",
]


def generate_word_slug(num_words: int = 3, separator: str = "-") -> str:
    """Generate a random slug of ``num_words`` words.

    First words are adjectives (cycling back if more than one adjective needed),
    last word is a noun.
    """
    if num_words <= 0:
        return ""
    parts: list[str] = []
    for i in range(num_words - 1):
        parts.append(secrets.choice(_ADJECTIVES))
    parts.append(secrets.choice(_NOUNS))
    return separator.join(parts)
