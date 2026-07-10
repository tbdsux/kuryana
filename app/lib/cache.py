"""In-process TTL cache for MDL HTML responses.

Two tiers:
  - page    : drama/person/cast/episode pages  — TTL 2 h,  max 500 entries
  - calendar: schedule/seasonal pages          — TTL 30 min, max 20 entries

All public functions are async and safe to call from the FastAPI event loop.
The underlying dicts are only touched from async context (never from threads),
so asyncio.Lock is sufficient for serialization.
"""

import asyncio
import time
from typing import Optional

_PAGE_TTL = 7_200.0  # 2 h
_CALENDAR_TTL = 1_800.0  # 30 min
_PAGE_MAXSIZE = 500
_CALENDAR_MAXSIZE = 20

# {url: (html, expires_at_monotonic)}
_page_cache: dict[str, tuple[str, float]] = {}
_calendar_cache: dict[str, tuple[str, float]] = {}
_page_lock = asyncio.Lock()
_calendar_lock = asyncio.Lock()


def _evict(store: dict[str, tuple[str, float]], maxsize: int) -> None:
    """Remove expired entries; evict the soonest-to-expire if still over capacity."""
    now = time.monotonic()
    for k in [k for k, (_, exp) in store.items() if now > exp]:
        del store[k]
    while len(store) >= maxsize:
        del store[min(store, key=lambda k: store[k][1])]


async def get_page(url: str) -> Optional[str]:
    async with _page_lock:
        entry = _page_cache.get(url)
        if entry is None:
            return None
        html, exp = entry
        if time.monotonic() > exp:
            del _page_cache[url]
            return None
        return html


async def set_page(url: str, html: str) -> None:
    async with _page_lock:
        _evict(_page_cache, _PAGE_MAXSIZE)
        _page_cache[url] = (html, time.monotonic() + _PAGE_TTL)


async def get_calendar(url: str) -> Optional[str]:
    async with _calendar_lock:
        entry = _calendar_cache.get(url)
        if entry is None:
            return None
        html, exp = entry
        if time.monotonic() > exp:
            del _calendar_cache[url]
            return None
        return html


async def set_calendar(url: str, html: str) -> None:
    async with _calendar_lock:
        _evict(_calendar_cache, _CALENDAR_MAXSIZE)
        _calendar_cache[url] = (html, time.monotonic() + _CALENDAR_TTL)
