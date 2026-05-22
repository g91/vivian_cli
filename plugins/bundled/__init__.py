"""Bundled plugin init — mirrors src/plugins/bundled/index.ts.

The bundled plugin is a no-op stub; all built-in skill registrations happen
in each feature's own module via registerBuiltinPlugin / registerBundledSkill.
"""


def initBuiltinPlugins() -> None:
    """Initialise built-in plugins. No-op stub — individual modules self-register."""
    pass
