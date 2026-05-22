"""Port of src/utils/shell/outputLimits.ts."""
from __future__ import annotations

import os

from ..envValidation import validateBoundedIntEnvVar


BASH_MAX_OUTPUT_UPPER_LIMIT = 150_000
BASH_MAX_OUTPUT_DEFAULT = 30_000


def getMaxOutputLength() -> int:
	result = validateBoundedIntEnvVar(
		"BASH_MAX_OUTPUT_LENGTH",
		os.environ.get("BASH_MAX_OUTPUT_LENGTH"),
		BASH_MAX_OUTPUT_DEFAULT,
		BASH_MAX_OUTPUT_UPPER_LIMIT,
	)
	return int(result["effective"])

