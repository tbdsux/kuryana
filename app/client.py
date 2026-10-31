from typing import Any
from collections.abc import Mapping
from urllib.parse import urljoin

import primp

from app import MYDRAMALIST_WEBSITE

# one shared async client: no per-request TLS setup and no blocking of the event loop
client = primp.AsyncClient(
    impersonate="chrome",
    impersonate_os="linux",
    headers={"Referer": MYDRAMALIST_WEBSITE},
    timeout=30,
)


async def get(
    path: str, params: Mapping[str, Any] | None = None
) -> primp.AsyncResponse:
    query = (
        {k: str(v) for k, v in params.items()} if params else None
    )  # primp wants str
    return await client.get(urljoin(MYDRAMALIST_WEBSITE, path), params=query)

