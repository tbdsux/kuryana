from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

import primp
from bs4 import BeautifulSoup

from app import client
from app.v2.errors import MDLError
from app.v2.parsers import error_info


async def scrape(
    path: str,
    parse: Callable[[BeautifulSoup], dict[str, Any]],
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        resp = await client.get(path, params=params)
    except primp.PrimpError as e:
        raise MDLError(502, "Failed to reach MyDramaList", str(e)) from e

    soup = BeautifulSoup(resp.text, "lxml")

    if resp.status_code != 200:
        # MDL answers unknown drama ids with an empty 500 instead of a 404 page
        empty_500 = resp.status_code == 500 and not resp.text.strip()
        raise MDLError(404 if empty_500 else resp.status_code, **error_info(soup))

    return {
        "success": True,
        "data": parse(soup),
        "link": resp.url,
        "scraped_at": datetime.now(UTC),
    }
