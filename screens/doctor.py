"""Doctor screen — mirrors src/screens/Doctor.tsx.

Diagnostics screen: checks settings, MCP, plugins, versions, etc.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class DiagnosticSection:
    title: str
    items: list[tuple[str, str]]  # (label, value/status)
    errors: list[str] = field(default_factory=list)


@dataclass
class DoctorResult:
    sections: list[DiagnosticSection]
    has_errors: bool = False


class DoctorScreen:
    """Gathers and renders diagnostic information about the vivian Code environment."""

    def __init__(self, on_done: Optional[Callable[[Optional[str]], None]] = None) -> None:
        self._on_done = on_done

    def run(self) -> DoctorResult:
        """Run all diagnostic checks and return results."""
        sections: list[DiagnosticSection] = []
        has_errors = False

        # Version info
        version_section = self._check_versions()
        sections.append(version_section)
        if version_section.errors:
            has_errors = True

        # Settings
        settings_section = self._check_settings()
        sections.append(settings_section)
        if settings_section.errors:
            has_errors = True

        # Environment
        env_section = self._check_environment()
        sections.append(env_section)

        result = DoctorResult(sections=sections, has_errors=has_errors)
        if self._on_done:
            self._on_done(None)
        return result

    def render(self) -> str:
        """Run diagnostics and render as a string report."""
        result = self.run()
        lines: list[str] = ["=== vivian Code Doctor ===", ""]
        for section in result.sections:
            lines.append(f"## {section.title}")
            for label, value in section.items:
                lines.append(f"  {label}: {value}")
            for err in section.errors:
                lines.append(f"  ✗ {err}")
            lines.append("")
        if result.has_errors:
            lines.append("Some issues were found. See above for details.")
        else:
            lines.append("Everything looks good!")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private checks
    # ------------------------------------------------------------------

    def _check_versions(self) -> DiagnosticSection:
        items: list[tuple[str, str]] = []
        errors: list[str] = []

        try:
            import importlib.metadata
            version = importlib.metadata.version("vivian-cli")
        except Exception:
            version = "unknown"
        items.append(("vivian-cli version", version))

        # Python version
        import sys
        items.append(("Python", sys.version.split()[0]))

        # Check for updates (non-blocking)
        try:
            result = subprocess.run(
                ["pip", "index", "versions", "vivian-cli"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                items.append(("Latest available", result.stdout.strip().split()[-1]))
        except Exception:
            pass

        return DiagnosticSection(title="Version", items=items, errors=errors)

    def _check_settings(self) -> DiagnosticSection:
        items: list[tuple[str, str]] = []
        errors: list[str] = []

        vivian_home = os.path.expanduser("~/.vivian")
        items.append(("Config home", vivian_home))
        items.append((
            "Config dir exists",
            "yes" if os.path.isdir(vivian_home) else "no",
        ))

        settings_path = os.path.join(vivian_home, "settings.json")
        if os.path.exists(settings_path):
            items.append(("Global settings", "found"))
            try:
                import json
                with open(settings_path) as f:
                    json.load(f)
                items.append(("Global settings valid", "yes"))
            except Exception as e:
                errors.append(f"Invalid global settings JSON: {e}")
        else:
            items.append(("Global settings", "not found"))

        project_settings = os.path.join(".vivian", "settings.json")
        if os.path.exists(project_settings):
            items.append(("Project settings", "found"))
        else:
            items.append(("Project settings", "not found"))

        return DiagnosticSection(title="Settings", items=items, errors=errors)

    def _check_environment(self) -> DiagnosticSection:
        items: list[tuple[str, str]] = []
        errors: list[str] = []

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        items.append(("ANTHROPIC_API_KEY", "set" if api_key else "not set"))
        if not api_key:
            errors.append("ANTHROPIC_API_KEY is not set — API calls will fail")

        items.append(("USER_TYPE", os.environ.get("USER_TYPE", "(not set)")))
        items.append(("vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
                       os.environ.get("vivian_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "(not set)")))

        return DiagnosticSection(title="Environment", items=items, errors=errors)
