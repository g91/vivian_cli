"""Output style constants — mirrors src/constants/outputStyles.ts."""
from __future__ import annotations

import asyncio
from typing import Any

from ..utils.cwd import get_cwd


OUTPUT_STYLE_DIR_NAME = ".vivian/output-styles"
OUTPUT_STYLE_FILE_EXTENSION = ".md"
DEFAULT_OUTPUT_STYLE_NAME = "default"

EXPLANATORY_FEATURE_PROMPT = (
	"vivian explains its implementation choices and codebase patterns."
)

OUTPUT_STYLE_CONFIG: dict[str, dict[str, Any] | None] = {
	DEFAULT_OUTPUT_STYLE_NAME: None,
	"Explanatory": {
		"name": "Explanatory",
		"source": "built-in",
		"description": "vivian explains its implementation choices and codebase patterns",
		"keepCodingInstructions": True,
		"prompt": EXPLANATORY_FEATURE_PROMPT,
	},
	"Learning": {
		"name": "Learning",
		"source": "built-in",
		"description": "vivian pauses and asks for small hands-on contributions where useful",
		"keepCodingInstructions": True,
		"prompt": "vivian balances task completion with targeted learning prompts.",
	},
}


def _run_sync(awaitable: Any, fallback: Any) -> Any:
	try:
		asyncio.get_running_loop()
	except RuntimeError:
		return asyncio.run(awaitable)
	return fallback


def getAllOutputStyles(cwd: str | None = None) -> dict[str, dict[str, Any] | None]:
	resolved_cwd = cwd or get_cwd()
	custom_styles: list[dict[str, Any]] = []
	plugin_styles: list[dict[str, Any]] = []

	try:
		from ..output_styles.load_output_styles_dir import getOutputStyleDirStyles

		custom_styles = _run_sync(getOutputStyleDirStyles(resolved_cwd), [])
	except Exception:
		custom_styles = []

	try:
		from ..utils.plugins.loadPluginOutputStyles import loadPluginOutputStyles

		plugin_styles = _run_sync(loadPluginOutputStyles(), [])
	except Exception:
		plugin_styles = []

	all_styles: dict[str, dict[str, Any] | None] = dict(OUTPUT_STYLE_CONFIG)
	for style in [*plugin_styles, *custom_styles]:
		name = str(style.get("name", "")).strip()
		if not name:
			continue
		all_styles[name] = {
			"name": name,
			"description": str(style.get("description", "")),
			"prompt": str(style.get("prompt", "")),
			"source": style.get("source", "built-in"),
			"keepCodingInstructions": bool(style.get("keepCodingInstructions", False)),
			"forceForPlugin": bool(style.get("forceForPlugin", False)),
		}
	return all_styles


__all__ = [
	"DEFAULT_OUTPUT_STYLE_NAME",
	"EXPLANATORY_FEATURE_PROMPT",
	"OUTPUT_STYLE_CONFIG",
	"OUTPUT_STYLE_DIR_NAME",
	"OUTPUT_STYLE_FILE_EXTENSION",
	"getAllOutputStyles",
]
