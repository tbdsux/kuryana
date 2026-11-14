import asyncio
import functools
import logging
import math
import re
from collections.abc import Awaitable, Callable
from typing import Annotated, Any
from urllib.parse import urlencode

import primp
from fastapi import FastAPI, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.routing import compile_path

from app import client
from app.client import segment
from app.cache import TTLCache
from app.handlers.calendar import parse_quarter, parse_schedule
from app.lib.msgspec_json import MsgSpecJSONResponse
from app.utils import error, fetch_func, search_func
from app.v2.errors import ERROR_TYPES, error_handler
from app.v2.routes import router as v2_router

app = FastAPI(
    title="Kuryana",
    default_response_class=MsgSpecJSONResponse,
)

logger = logging.getLogger(__name__)

# capped by count and by total body size: one /seasonal response is ~330 KB
cache: TTLCache[Response] = TTLCache(
    ttl=60, max_size=1024, max_bytes=64 * 1024 * 1024, sizeof=lambda r: len(r.body)
)

# key -> the response a request is already producing for it (None if it failed outright)
_inflight: dict[str, asyncio.Future[Response | None]] = {}


# innermost middleware: turn unhandled errors into a response here, inside CORS,
# so 500s still carry CORS headers and browsers can read the error body
@app.middleware("http")
async def catch_exceptions(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception("unhandled error on %s", request.url.path)
        return await error_handler(request, exc)


# cache the finished response, not the MDL page, so a hit skips scraping and parsing;
# registered before CORS so CORS headers are still computed per request
@app.middleware("http")
async def cache_responses(
    request: Request, call_next: Callable[[Request], Awaitable[StreamingResponse]]
) -> Response:
    if request.method != "GET":
        return await call_next(request)

    key = _cache_key(request)
    while True:
        if (entry := cache.get_entry(key)) is not None:
            return _with_cdn_header(*entry)

        # the same URL is already being scraped: share that result instead of
        # scraping again, so a burst of identical requests costs MDL one request
        if (pending := _inflight.get(key)) is None:
            break
        # shield: a waiter that gives up must not cancel the shared future
        shared = await asyncio.shield(pending)
        if shared is not None:
            return _share(key, shared)
        # that request was cancelled or failed outright: loop, so the first waiter
        # to wake takes over and the others wait on it, rather than all scraping

    future: asyncio.Future[Response | None] = asyncio.get_running_loop().create_future()
    _inflight[key] = future
    stored: Response | None = None
    try:
        response = await call_next(request)
        # call_next always streams bytes; the type only says it could be str
        body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[misc]
        stored = Response(body, response.status_code, dict(response.headers))
    finally:
        del _inflight[key]
        future.set_result(stored)

    if stored.status_code == 200:  # never cache errors, so MDL hiccups don't stick
        cache.set(key, stored)
    return _share(key, stored)


@functools.cache
def _route_query_params() -> list[tuple[re.Pattern[str], frozenset[str]]]:
    """(path regex, query params the route declares) for every GET route, read
    from the public OpenAPI schema rather than router internals."""
    routes = []
    for path, ops in app.openapi()["paths"].items():
        if "get" in ops:
            params = ops["get"].get("parameters", [])
            names = frozenset(p["name"] for p in params if p["in"] == "query")
            routes.append((compile_path(path)[0], names))
    return routes


def _cache_key(request: Request) -> str:
    """Path plus only the query params its route reads, in a fixed order, so junk
    or reordered params (`?cb=1`, `?cb=2`, ...) share one entry and one scrape."""
    path = request.url.path
    names = next((n for rx, n in _route_query_params() if rx.match(path)), frozenset())
    params = sorted((k, v) for k, v in request.query_params.multi_items() if k in names)
    return f"{path}?{urlencode(params)}"


def _share(key: str, stored: Response) -> Response:
    """A fresh copy of a finished response, for the request that made it or one
    that waited on it. Errors are shared with waiters too, but never cached."""
    if stored.status_code != 200:
        return Response(stored.body, stored.status_code, dict(stored.headers))

    entry = cache.get_entry(key)  # missing if it was too big to keep
    return _with_cdn_header(stored, entry[1] if entry is not None else cache.ttl)


def _with_cdn_header(stored: Response, ttl_left: float) -> Response:
    """A fresh copy of `stored` that lets Vercel's CDN share it for as long as it has
    left in memory, so the two caches together never serve it past one TTL.
    s-maxage is stripped before the browser; a route's own Cache-Control wins."""
    headers = dict(stored.headers)
    if "cache-control" not in headers:
        seconds = max(1, math.ceil(ttl_left))
        headers["cache-control"] = f"public, max-age=0, s-maxage={seconds}"
    return Response(stored.body, stored.status_code, headers)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(v2_router)
for exc in ERROR_TYPES:
    app.add_exception_handler(exc, error_handler)


@app.get("/")
async def index() -> dict[str, Any]:
    return {"message": "A Simple and Basic MDL Scraper API"}


@app.get("/search/q/{query}")
async def search(query: str, response: Response) -> dict[str, Any]:
    code, r = await search_func(query=query)

    response.status_code = code
    return r


@app.get("/id/{drama_id}")
async def fetch(drama_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=segment(drama_id), t="drama")

    response.status_code = code
    return r


@app.get("/id/{drama_id}/cast")
async def fetch_cast(drama_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"{segment(drama_id)}/cast", t="cast")

    response.status_code = code
    return r


@app.get("/id/{drama_id}/episodes")
async def fetch_episodes(drama_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"{segment(drama_id)}/episodes", t="episodes")

    response.status_code = code
    return r


@app.get("/id/{drama_id}/reviews")
async def fetch_reviews(
    drama_id: str, response: Response, page: int = 1
) -> dict[str, Any]:
    code, r = await fetch_func(
        query=f"{segment(drama_id)}/reviews?page={page}", t="reviews"
    )

    response.status_code = code
    return r


@app.get("/people/{person_id}")
async def person(person_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"people/{segment(person_id)}", t="person")

    response.status_code = code
    return r


@app.get("/dramalist/{user_id}")
async def dramalist(user_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"dramalist/{segment(user_id)}", t="dramalist")

    response.status_code = code
    return r


@app.get("/list/{list_id}")
async def lists(list_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"list/{segment(list_id)}", t="lists")

    response.status_code = code
    return r


# get seasonal drama list -- MDL only serves this as HTML now, so it is scraped
@app.get("/seasonal/{year}/{quarter}")
async def mdlSeasonal(
    year: int, quarter: Annotated[int, Path(ge=1, le=4)], response: Response
) -> Any:
    # year -> ex. ... / 2019 / 2020 / 2021 / ...
    # quarter -> every 3 months (Jan-Mar=1, Apr-Jun=2, Jul-Sep=3, Oct-Dec=4)
    # --- seasonal information --- winter --- spring --- summer --- fall ---
    return await _calendar(
        f"episode-calendar/q{quarter}-{year}", response, parse_quarter
    )


# get episode schedule (the next 7 days)
@app.get("/schedule")
async def mdlSchedule(response: Response) -> Any:
    return await _calendar("episode-calendar", response, parse_schedule)


async def _calendar(
    path: str, response: Response, parse: Callable[[str], list[dict[str, Any]]]
) -> Any:
    try:
        r = await client.get(path, params={"fragment": 1})
    except primp.PrimpError:
        # match the rest of v1: an error body rather than a bare 500
        response.status_code = 502
        return error(502, "Failed to reach MyDramaList")
    except client.MDLBusy:
        response.status_code = 503
        return error(503, "Too many requests to MyDramaList in progress.")

    response.status_code = r.status_code
    if r.status_code != 200:
        return error(r.status_code, "An unexpected error occurred.")
    return parse(r.text)
