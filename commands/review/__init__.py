"""Package compatibility wrapper for the review command module."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "review.py"
_SPEC = spec_from_file_location("vivian_cli.commands._review_impl", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
	raise ImportError(f"Unable to load review command implementation from {_MODULE_PATH}")

_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

call = _MODULE.call
getReviewPrompt = _MODULE.getReviewPrompt
reviewCode = _MODULE.reviewCode
review_code = _MODULE.review_code
get_review_prompt = _MODULE.get_review_prompt

__all__ = [
	"call",
	"getReviewPrompt",
	"get_review_prompt",
	"reviewCode",
	"review_code",
]
