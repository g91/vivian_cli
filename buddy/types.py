"""Buddy system types — mirrors src/buddy/types.ts."""
from __future__ import annotations

from typing import Final, Literal

RARITIES: Final = ("common", "uncommon", "rare", "epic", "legendary")
Rarity = Literal["common", "uncommon", "rare", "epic", "legendary"]

SPECIES: Final = (
    "duck", "goose", "blob", "cat", "dragon", "octopus", "owl",
    "penguin", "turtle", "snail", "ghost", "axolotl", "capybara",
    "cactus", "robot", "rabbit", "mushroom", "chonk",
)
Species = Literal[
    "duck", "goose", "blob", "cat", "dragon", "octopus", "owl",
    "penguin", "turtle", "snail", "ghost", "axolotl", "capybara",
    "cactus", "robot", "rabbit", "mushroom", "chonk",
]

EYES: Final = ("·", "✦", "×", "◉", "@", "°")
Eye = Literal["·", "✦", "×", "◉", "@", "°"]

HATS: Final = ("none", "crown", "tophat", "propeller", "halo", "wizard", "beanie", "tinyduck")
Hat = Literal["none", "crown", "tophat", "propeller", "halo", "wizard", "beanie", "tinyduck"]

STAT_NAMES: Final = ("DEBUGGING", "PATIENCE", "CHAOS", "WISDOM", "SNARK")
StatName = Literal["DEBUGGING", "PATIENCE", "CHAOS", "WISDOM", "SNARK"]

RARITY_WEIGHTS: dict[str, int] = {
    "common": 60,
    "uncommon": 25,
    "rare": 10,
    "epic": 4,
    "legendary": 1,
}

RARITY_STARS: dict[str, str] = {
    "common": "★",
    "uncommon": "★★",
    "rare": "★★★",
    "epic": "★★★★",
    "legendary": "★★★★★",
}

RARITY_COLORS: dict[str, str] = {
    "common": "white",
    "uncommon": "green",
    "rare": "blue",
    "epic": "magenta",
    "legendary": "yellow",
}


class CompanionBones:
    """Deterministic parts derived from hash(user_id)."""

    def __init__(
        self,
        rarity: str,
        species: str,
        eye: str,
        hat: str,
        shiny: bool,
        stats: dict[str, int],
    ) -> None:
        self.rarity = rarity
        self.species = species
        self.eye = eye
        self.hat = hat
        self.shiny = shiny
        self.stats = stats

    def to_dict(self) -> dict:
        return {
            "rarity": self.rarity,
            "species": self.species,
            "eye": self.eye,
            "hat": self.hat,
            "shiny": self.shiny,
            "stats": self.stats,
        }


class StoredCompanion:
    """What actually persists in config — bones are regenerated on each read."""

    def __init__(self, name: str, personality: str, hatched_at: int) -> None:
        self.name = name
        self.personality = personality
        self.hatched_at = hatched_at

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "personality": self.personality,
            "hatchedAt": self.hatched_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StoredCompanion":
        return cls(
            name=d.get("name", ""),
            personality=d.get("personality", ""),
            hatched_at=d.get("hatchedAt", 0),
        )


class Companion(CompanionBones):
    """Full companion — bones + generated soul."""

    def __init__(
        self,
        rarity: str,
        species: str,
        eye: str,
        hat: str,
        shiny: bool,
        stats: dict[str, int],
        name: str,
        personality: str,
        hatched_at: int,
    ) -> None:
        super().__init__(rarity, species, eye, hat, shiny, stats)
        self.name = name
        self.personality = personality
        self.hatched_at = hatched_at

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "name": self.name,
            "personality": self.personality,
            "hatchedAt": self.hatched_at,
        }
