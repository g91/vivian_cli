"""First token date fetching — mirrors src/services/api/firstTokenDate.ts."""
from __future__ import annotations


async def fetchAndStorevivianCodeFirstTokenDate() -> None:
    """Fetch the user's first vivian Code token date and store in config.

    Mirrors fetchAndStorevivianCodeFirstTokenDate() from firstTokenDate.ts.
    """
    try:
        from ...utils.config import get_global_config, save_global_config
        config = get_global_config()
        if config.get("vivianCodeFirstTokenDate") is not None:
            return

        from ...utils.http import get_auth_headers
        auth = get_auth_headers()
        if auth.get("error"):
            return

        from ...constants.oauth import get_oauth_config
        import urllib.request
        import json

        oauth_config = get_oauth_config()
        url = f"{oauth_config['BASE_API_URL']}/api/organization/vivian_code_first_token_date"

        req = urllib.request.Request(
            url,
            headers={**auth.get("headers", {}), "User-Agent": "vivianCode/Python"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        first_token_date = data.get("first_token_date")
        if first_token_date is not None:
            from datetime import datetime
            try:
                datetime.fromisoformat(first_token_date)
            except ValueError:
                return

        save_global_config(lambda c: {**c, "vivianCodeFirstTokenDate": first_token_date})
    except Exception:
        pass


fetch_and_store_vivian_code_first_token_date = fetchAndStorevivianCodeFirstTokenDate
