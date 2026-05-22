"""Spinner verbs — mirrors src/constants/spinnerVerbs.ts."""
from __future__ import annotations

SPINNER_VERBS = [
    "Accomplishing", "Actioning", "Actualizing", "Architecting",
    "Baking", "Beaming", "Beboppin'", "Befuddling", "Billowing",
    "Blanching", "Bloviating", "Boogieing", "Boondoggling", "Booping",
    "Bootstrapping", "Brewing", "Bunning", "Burrowing",
    "Calculating", "Canoodling", "Caramelizing", "Cascading",
    "Catapulting", "Cerebrating", "Channeling", "Channelling",
    "Choreographing", "Churning", "Clauding", "Coalescing",
    "Cogitating", "Combobulating", "Composing", "Computing",
    "Concocting", "Considering", "Contemplating", "Cooking",
    "Crafting", "Creating", "Crunching", "Crystallizing",
    "Cultivating", "Deciphering", "Deliberating", "Determining",
    "Dilly-dallying", "Discombobulating", "Doing", "Drizzling",
    "Ebbing", "Effecting", "Elucidating", "Embellishing",
    "Enchanting", "Envisioning", "Evaporating", "Fermenting",
    "Fiddle-faddling", "Finagling", "Flambéing", "Flibbertigibbeting",
    "Flowing", "Flummoxing", "Fluttering", "Forging", "Forming",
    "Frolicking", "Frosting", "Gallivanting", "Galloping",
    "Garnishing", "Generating", "Gesticulating", "Germinating",
    "Gitifying", "Gleaming", "Glistening", "Glittering",
    "Grokking", "Hallucinating", "Harmonizing", "Hatching",
    "Hibernating", "Honing", "Hoodwinking", "Hornswoggling",
    "Hullaballooing", "Humming", "Hustling", "Illuminating",
    "Imagining", "Improvising", "Incubating", "Innovating",
    "Iterating", "Jazzing", "Jiving", "Juggling", "Kernelizing",
    "Kindling", "Laminating", "Lev Morphing", "Lollygagging",
    "Manifesting", "Marinating", "Materializing", "Moseying",
    "Mulling", "Mustering", "Navigating", "Noodling",
    "Optimizing", "Orchestrating", "Percolating", "Piloting",
    "Pioneering", "Pitter-pattering", "Pondering", "Prepping",
    "Processing", "Prognosticating", "Puttering", "Rambling",
    "Razzy-dazzling", "Reasoning", "Refactoring", "Reticulating",
    "Riffing", "Ruminating", "Sauntering", "Schmoozing",
    "Scintillating", "Sculpting", "Sequencing", "Simmering",
    "Synthesizing", "Tinkering", "Transmogrifying", "Triangulating",
    "Unfurling", "Venturing", "Wandering", "Whimsifying",
    "Wizardizing", "Wondering", "Yarn-spinning", "Zesting",
    "Zigzagging",
]


def getSpinnerVerbs() -> list[str]:
    """Get spinner verbs, possibly customized by settings."""
    try:
        from ..utils.settings.settings import get_initial_settings
        settings = get_initial_settings()
        config = settings.get("spinnerVerbs")
        if config:
            if config.get("mode") == "replace":
                return config.get("verbs", []) or SPINNER_VERBS
            return list(SPINNER_VERBS) + config.get("verbs", [])
    except Exception:
        pass
    return list(SPINNER_VERBS)


get_spinner_verbs = getSpinnerVerbs
