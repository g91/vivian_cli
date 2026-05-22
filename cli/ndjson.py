"""NDJSON safe serialisation — mirrors src/cli/ndjsonSafeStringify.ts.

JSON.dumps may emit U+2028 / U+2029 raw (valid per ECMA-404 / RFC 8259).
When the output is a single NDJSON line, any receiver that splits on
JavaScript line-terminator semantics (U+2028 LINE SEPARATOR, U+2029
PARAGRAPH SEPARATOR) will cut the JSON mid-string.  Escaping these two
code-points produces equivalent JSON that can never be misread as a
line-break by any receiver.
"""
from __future__ import annotations

import json
import re
from typing import Any

_JS_LINE_TERMINATORS = re.compile("[\u2028\u2029]")


def _escape_js_line_terminators(text: str) -> str:
    def _repl(m: re.Match) -> str:
        return "\\u2028" if m.group() == "\u2028" else "\\u2029"

    return _JS_LINE_TERMINATORS.sub(_repl, text)


def ndjson_safe_stringify(value: Any, **kwargs: Any) -> str:
    """Serialise *value* to a JSON string safe for one-message-per-line transports.

    Escapes U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR so the
    output cannot be broken by a line-splitting receiver.  The result is
    still valid JSON and parses to the same value.
    """
    return _escape_js_line_terminators(json.dumps(value, **kwargs))
