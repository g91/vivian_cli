"""Number formatter — mirrors src/hooks/useNumberFormatter.ts."""
from __future__ import annotations

def useNumberFormatter(locale: str = "en-US") -> dict:
    """Format numbers for locale."""
    return {"locale": locale}

use_number_formatter = useNumberFormatter
