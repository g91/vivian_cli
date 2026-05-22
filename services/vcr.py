"""VCR (Video Cassette Recorder) test fixture caching — mirrors src/services/vcr.ts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def shouldUseVCR() -> bool:
    """Check if VCR fixture caching should be used.

    Mirrors shouldUseVCR() from vcr.ts.
    """
    if os.environ.get("NODE_ENV") == "test":
        return True
    if os.environ.get("USER_TYPE") == "ant" and os.environ.get("FORCE_VCR", "").lower() in (
        "1", "true", "yes"
    ):
        return True
    return False


async def withFixture(
    input_data: Any,
    fixture_name: str,
    fn: Callable,
) -> Any:
    """Cache the result of fn() in a fixture file keyed by input_data hash.

    Mirrors withFixture() from vcr.ts.
    """
    if not shouldUseVCR():
        return await fn()

    input_json = json.dumps(input_data, sort_keys=True, default=str)
    digest = hashlib.sha1(input_json.encode()).hexdigest()[:12]
    fixtures_root = os.environ.get("vivian_CODE_TEST_FIXTURES_ROOT") or os.getcwd()
    filename = Path(fixtures_root) / "fixtures" / f"{fixture_name}-{digest}.json"

    if filename.exists():
        return json.loads(filename.read_text(encoding="utf-8"))

    is_ci = os.environ.get("CI") or os.environ.get("CONTINUOUS_INTEGRATION")
    vcr_record = os.environ.get("VCR_RECORD", "").lower() in ("1", "true", "yes")
    if is_ci and not vcr_record:
        raise FileNotFoundError(
            f"Fixture missing: {filename}. Re-run tests with VCR_RECORD=1, then commit the result."
        )

    result = await fn()
    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result


async def withVCR(messages: list, fn: Callable) -> list:
    """VCR wrapper for streaming message responses.

    Mirrors withVCR() from vcr.ts.
    """
    if not shouldUseVCR():
        return await fn()
    try:
        from ..utils.messages import normalize_messages_for_api
        messages_for_api = normalize_messages_for_api(
            [m for m in messages if not (m.get("type") == "user" and m.get("isSideEffect"))]
        )
    except Exception:
        messages_for_api = messages
    return await withFixture(messages_for_api, "messages", fn)


async def withStreamingVCR(messages: list, fn: Callable) -> Any:
    """VCR wrapper for streaming responses.

    Mirrors withStreamingVCR() from vcr.ts.
    """
    return await withVCR(messages, fn)


async def withTokenCountVCR(input_data: Any, fn: Callable) -> Any:
    """VCR wrapper for token count requests.

    Mirrors withTokenCountVCR() from vcr.ts.
    """
    if not shouldUseVCR():
        return await fn()
    return await withFixture(input_data, "token-count", fn)


should_use_vcr = shouldUseVCR
with_fixture = withFixture
with_vcr = withVCR
with_streaming_vcr = withStreamingVCR
with_token_count_vcr = withTokenCountVCR
