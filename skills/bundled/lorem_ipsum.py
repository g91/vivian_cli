"""Lorem ipsum skill — mirrors src/skills/bundled/loremIpsum.ts."""
from __future__ import annotations

import random
from typing import Any

from ..bundled_skills import BundledSkillDefinition, register_bundled_skill

_ONE_TOKEN_WORDS = [
    "the", "a", "an", "I", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them", "my", "your", "his", "its", "our",
    "this", "that", "what", "who", "is", "are", "was", "were", "be",
    "been", "have", "has", "had", "do", "does", "did", "will", "would",
    "can", "could", "may", "might", "must", "shall", "should", "make",
    "made", "get", "got", "go", "went", "come", "came", "see", "saw",
    "use", "used", "find", "found", "give", "gave", "take", "took",
    "know", "knew", "think", "thought", "want", "need", "feel", "felt",
    "and", "or", "but", "so", "if", "then", "than", "as", "at", "by",
    "for", "in", "of", "on", "to", "up", "out", "with", "from", "into",
    "not", "no", "yes", "just", "now", "new", "old", "big", "small",
    "good", "bad", "right", "left", "first", "last", "long", "little",
    "own", "same", "each", "much", "more", "most", "other", "some",
    "such", "even", "also", "only", "back", "over", "after", "before",
    "very", "well", "still", "here", "there", "where", "when", "how",
    "all", "both", "few", "many", "next", "open", "set", "sure", "work",
    "day", "way", "time", "year", "hand", "part", "place", "case",
    "week", "point", "group", "end", "fact", "help", "home", "life",
    "line", "name", "long", "move", "next", "once", "look",
]


def _generate_lorem(token_count: int) -> str:
    words = random.choices(_ONE_TOKEN_WORDS, k=token_count)
    # Capitalize first word and add sentence structure
    sentences = []
    i = 0
    while i < len(words):
        sent_len = random.randint(8, 16)
        chunk = words[i:i + sent_len]
        if chunk:
            chunk[0] = chunk[0].capitalize()
            sentences.append(" ".join(chunk) + ".")
        i += sent_len
    return " ".join(sentences)


def register_lorem_ipsum_skill() -> None:
    register_bundled_skill(BundledSkillDefinition(
        name="loremIpsum",
        description="Generate placeholder text with a specified token count.",
        aliases=["lorem"],
        argument_hint="<token count>",
        user_invocable=True,
        get_prompt_for_command=_get_prompt,
    ))


def _get_prompt(args: str = "", ctx: Any = None) -> list[dict]:
    try:
        count = int(args.strip())
    except (ValueError, AttributeError):
        count = 100
    text = _generate_lorem(count)
    return [{"type": "text", "text": text}]
