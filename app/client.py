import asyncio
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote
from weakref import WeakKeyDictionary

import primp
from starlette.exceptions import HTTPException

from app import MYDRAMALIST_WEBSITE

# one shared async client: no per-request TLS setup and no blocking of the event loop
client = primp.AsyncClient(
    impersonate="chrome",
    impersonate_os="linux",
    headers={"Referer": MYDRAMALIST_WEBSITE},
    timeout=30,
)

# at most this many MDL requests in flight at once; the rest queue. A burst of
# distinct URLs then can't hit MDL (and its Cloudflare) hard enough to get us blocked
MAX_CONCURRENT_REQUESTS = 8

# how long a request may wait for a free slot before giving up with MDLBusy
QUEUE_TIMEOUT = 10


class MDLBusy(Exception):
    """Every MDL request slot stayed busy for QUEUE_TIMEOUT seconds."""


# asyncio primitives bind to one event loop, so keep one semaphore per loop
# (there's one loop in production; tests start several)
_limits: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = (
    WeakKeyDictionary()
)


def _limit() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if (sem := _limits.get(loop)) is None:
        sem = _limits[loop] = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    return sem


def segment(value: str) -> str:
    """Encode a route param for use as one MDL path segment, so a decoded
    `?`, `#` or `/` in it can't add a query, fragment or extra path.

    `.` and `..` are refused (404): encoding can't help, since URL parsers treat
    `%2E%2E` as `..` too, and they'd make the request land on another MDL page."""
    if value in (".", ".."):
        raise HTTPException(404)
    return quote(value, safe="")


def mdl_url(path: str) -> str:
    """`path` -> an MDL URL. Plain concatenation, not urljoin: a slug like
    `http:127.0.0.1` or `//evil.com` must stay a path on MDL, never become its own URL."""
    return MYDRAMALIST_WEBSITE + path.lstrip("/")


async def get(
    path: str, params: Mapping[str, Any] | None = None
) -> primp.AsyncResponse:
    query = (
        {k: str(v) for k, v in params.items()} if params else None
    )  # primp wants str
    sem = _limit()
    try:
        async with asyncio.timeout(QUEUE_TIMEOUT):
            await sem.acquire()
    except TimeoutError:
        raise MDLBusy from None

    try:
        resp = await client.get(mdl_url(path), params=query)
        # primp returns once the headers arrive and would download the body
        # *synchronously* on `.text`, freezing the event loop. Read it here instead:
        # async, inside the slot, and where callers already catch PrimpError
        await resp.aread()
        return resp
    finally:
        sem.release()
