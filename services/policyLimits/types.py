"""Policy limits types — mirrors src/services/policyLimits/types.ts."""
from __future__ import annotations

from typing import Optional


PolicyLimitsResponse = dict  # {restrictions: {str: {allowed: bool}}}

PolicyLimitsFetchResult = dict  # {success, restrictions?, etag?, error?, skipRetry?}
