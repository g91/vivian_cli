"""Port of src/utils/sandbox/sandbox-ui-utils.ts."""
from __future__ import annotations

import re


def removeSandboxViolationTags(text: str) -> str:
	return re.sub(r"<sandbox_violations>[\s\S]*?</sandbox_violations>", "", text)


remove_sandbox_violation_tags = removeSandboxViolationTags
