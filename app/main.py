from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import FastAPI, Path, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app import client
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

cache: TTLCache[Response] = TTLCache(ttl=60)


# cache the finished response, not the MDL page, so a hit skips scraping and parsing;
# registered before CORS so CORS headers are still computed per request
@app.middleware("http")
async def cache_responses(
    request: Request, call_next: Callable[[Request], Awaitable[StreamingResponse]]
) -> Response:
    if request.method != "GET":
        return await call_next(request)

    key = f"{request.url.path}?{request.url.query}"
    if (hit := cache.get(key)) is not None:
        return hit

    response = await call_next(request)
    if response.status_code != 200:  # never cache errors, so MDL hiccups don't stick
        return response

    # call_next always streams bytes; the type only says it could be str
    body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[misc]
    cached = Response(body, response.status_code, dict(response.headers))
    # let Vercel's CDN share it for 60s too; s-maxage is stripped before the browser
    cached.headers.setdefault("Cache-Control", "public, max-age=0, s-maxage=60")
    cache.set(key, cached)
    return cached


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
    code, r = await fetch_func(query=drama_id, t="drama")

    response.status_code = code
    return r


@app.get("/id/{drama_id}/cast")
async def fetch_cast(drama_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/cast", t="cast")

    response.status_code = code
    return r


@app.get("/id/{drama_id}/episodes")
async def fetch_episodes(drama_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/episodes", t="episodes")

    response.status_code = code
    return r


@app.get("/id/{drama_id}/reviews")
async def fetch_reviews(
    drama_id: str, response: Response, page: int = 1
) -> dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/reviews?page={page}", t="reviews")

    response.status_code = code
    return r


@app.get("/people/{person_id}")
async def person(person_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"people/{person_id}", t="person")

    response.status_code = code
    return r


@app.get("/dramalist/{user_id}")
async def dramalist(user_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"dramalist/{user_id}", t="dramalist")

    response.status_code = code
    return r


@app.get("/list/{list_id}")
async def lists(list_id: str, response: Response) -> dict[str, Any]:
    code, r = await fetch_func(query=f"list/{list_id}", t="lists")

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
    r = await client.get(f"episode-calendar/q{quarter}-{year}", params={"fragment": 1})
    return _html_or_error(r, response, parse_quarter)


# get episode schedule (the next 7 days)
@app.get("/schedule")
async def mdlSchedule(response: Response) -> Any:
    r = await client.get("episode-calendar", params={"fragment": 1})
    return _html_or_error(r, response, parse_schedule)


def _html_or_error(
    r: Any, response: Response, parse: Callable[[str], list[dict[str, Any]]]
) -> Any:
    response.status_code = r.status_code
    if r.status_code != 200:
        return error(r.status_code, "An unexpected error occurred.")
    return parse(r.text)
