# Project Structure

How the code is laid out and where to make changes.

```
app/
├── __init__.py            MYDRAMALIST_WEBSITE base URL
├── main.py                FastAPI app: middleware, v1 routes, mounts v2
├── client.py              one shared async HTTP client (primp) for MDL requests, mdl_url(), segment()
├── cache.py               TTLCache, the in-memory response cache used in main.py
├── utils.py               v1 glue: search_func, fetch_func, error
├── lib/
│   └── msgspec_json.py    MsgSpecJSONResponse, the default JSON response class
├── handlers/              v1 scrapers (legacy, class based)
│   ├── parser.py          Parser, BaseSearch, BaseFetch
│   ├── search.py          Search
│   └── fetch.py           FetchDrama, FetchPerson, FetchCast, ...
└── v2/
    ├── __init__.py        PREFIX = "/v2"
    ├── routes.py          endpoint definitions only
    ├── scraper.py         scrape(): fetch a page, map errors, wrap the response
    ├── errors.py          MDLError and the exception handler
    └── parsers/
        ├── __init__.py    re-exports every parse_* function
        ├── _helpers.py    shared None-safe helpers used by all parsers
        ├── search.py      parse_search
        ├── drama.py       parse_drama
        ├── cast.py        parse_cast
        ├── episodes.py    parse_episodes
        ├── reviews.py     parse_reviews
        ├── person.py      parse_person
        ├── lists.py       parse_list
        └── dramalist.py   parse_dramalist
tests/
├── test_main.py           v1 endpoints
├── test_fetch_dramalist.py
├── test_v2.py             v2 endpoints and parsers
├── test_regressions.py    offline tests with MDL faked (URL safety, errors, cache, parser edge cases)
├── conftest.py            blocks real MDL requests in any test not marked `live`
└── fixture/               saved MDL pages for offline parser tests
docs/                      API docs (v1, v2, wrapper guide) and nginx config
```

## v2 request flow

```
GET /v2/dramas/18452-goblin
  -> routes.drama()
  -> scraper.scrape(segment("18452-goblin"), parsers.parse_drama)
       -> client.get()                 fetch the MDL page
       -> non-200?  raise MDLError     (errors.py turns it into the error body)
       -> parse_drama(soup)            pure function: soup -> dict
  -> {"success": true, "data": ..., "link": ..., "scraped_at": ...}
```

Each module has one job:

- **routes.py** only declares URLs and query params, then calls `scrape()`. Wrap every path param in `segment()` (see [Requests to MDL](#requests-to-mdl)).
- **scraper.py** does the network call and the status-code handling. It knows nothing about any page's layout.
- **parsers/** are pure functions that take a `BeautifulSoup` and return a dict. They never do network calls or raise HTTP errors, so they can be tested against saved HTML in `tests/fixture/`.
- **errors.py** formats every error under `/v2` as `{success: false, data: null, message}`. Routes outside `/v2` keep FastAPI's default error responses.

## Requests to MDL

Every request goes through `client.get(path)`. At most `MAX_CONCURRENT_REQUESTS` (8) run at once and the rest wait their turn, so a burst of traffic can't hit MDL, and its Cloudflare, hard enough to get the server's IP blocked. A request that waits more than `QUEUE_TIMEOUT` (10 s) for a slot gets `503` instead of queueing forever.

`client.get` also downloads the body (`await resp.aread()`) before it returns. Keep that: primp returns as soon as the headers arrive, and reading `.text` before the body is downloaded fetches it *synchronously*, which freezes every other request until it finishes. Reading it in `client.get` keeps it async, inside the request slot, and inside the callers' `except PrimpError`. `client.get` builds the URL with `mdl_url()`: the base URL plus the path, by plain concatenation. Don't use `urljoin` for this. It treats a slug like `http:127.0.0.1` or `//evil.com` as a URL of its own, which would let a caller make the server fetch any address.

Route params are decoded before they reach the route, so `%3F` arrives as `?`. Pass each one through `segment()`, which percent-encodes it, so it can't add a query string, fragment or extra path to the MDL URL. `segment()` returns `404` for `.` and `..`: encoding can't neutralise those, because URL parsers treat `%2E%2E` as `..` as well. Send query values as `params=`, not by building the query string by hand.

## Caching

There are two layers, both 60 seconds.

**In-memory, in the `cache_responses` middleware (`main.py`).** It stores the finished response of every successful `GET` (v1, v2, seasonal, schedule) in a `TTLCache` (`app/cache.py`), keyed by the path plus only the query params its route declares, in a fixed order (read from the OpenAPI schema). So `?cb=1`, `?cb=2` or reordered params share one entry and one scrape, instead of each forcing a fresh scrape. A hit is returned before any route runs, so it skips both the MDL request and the parsing, and `scraped_at` still says when the page was really scraped. Only `200` responses are stored, so an MDL error or outage is never served from the cache. The cache holds at most 1024 entries and 64 MB of response bodies (one `/seasonal` response is about 330 KB). When either limit is reached, or entries expire, the oldest go first, so distinct URLs (such as junk query params) can't grow memory without bound. A response larger than the whole budget is served but not stored. The cache lives in the process: it's lost on restart and not shared between workers or instances. Change the TTL and limits in `main.py` (`TTLCache(ttl=60, max_size=1024, max_bytes=...)`).

Identical requests that arrive while the first one is still scraping don't scrape again. They wait for that response and share it (`_inflight` in `main.py`), so ten requests for the same uncached page cost MDL one request. If the shared response is an error, every waiter gets it, but it still isn't cached. If the first request is cancelled before it finishes (e.g. its client disconnects), the first waiter to wake takes over and the rest wait on it.

Middleware order matters. From innermost to outermost:

1. `catch_exceptions` turns any unhandled exception into the normal error response (`errors.error_handler`) and logs it. It sits inside CORS so 500s still carry CORS headers and browsers can read them. Don't register a handler for bare `Exception` instead: that one runs outside CORS.
2. `cache_responses` sees that 500 as a non-`200` and doesn't store it.
3. `CORSMiddleware` is outermost, so CORS headers are worked out per request, even on a cache hit.

Keep that order when adding middleware. With `@app.middleware`, the first one registered is the innermost.

**CDN, via `Cache-Control`.** The same middleware adds `Cache-Control: public, max-age=0, s-maxage=N` to every response it caches. `N` is the time the entry has left in memory: `60` on a fresh scrape, less on a hit. That way a response cached by both layers is never served more than 60 seconds after it was scraped. On Vercel the CDN then serves repeat requests without running the function. Vercel strips `s-maxage` before the response reaches the browser, and `max-age=0` keeps browsers from caching on their own. Errors get no header, so they're never cached. A route can set its own `Cache-Control`; the middleware won't override it. On a self-hosted deploy the header does nothing unless a CDN or caching proxy sits in front.

To check the CDN cache on Vercel, look at the `x-vercel-cache` response header (`HIT`, `MISS`, `STALE`).

## Parser conventions

- Use the helpers in `_helpers.py` (`_text`, `_int`, `_float`, `_year`, `_slug`, `_link`, `_img`, ...). They are None-safe: a missing element gives `None`, `""` or `[]` instead of an exception.
- Numbers come back as numbers or `None`, never strings like `"N/A"`.
- Slugs have no leading slash, so they work directly in other v2 routes.
- Keep each `parse_*` function short. Move per-row logic into a small private helper (`_episode`, `_work`, `_item`, ...) and put blank lines between steps.
- Some parsers delete elements from the soup (for example the "read more" links). Read anything you need from those elements first. `reviews.py` reads `ratings` and `spoiler` before `_body()` strips the body.

## Adding a v2 endpoint

1. Create `app/v2/parsers/<page>.py` with `parse_<page>(soup) -> dict[str, Any]`.
2. Export it from `app/v2/parsers/__init__.py`.
3. Add the route in `app/v2/routes.py`:

   ```python
   @router.get("/dramas/{slug}/photos")
   async def drama_photos(slug: str) -> dict[str, Any]:
       return await scrape(f"{segment(slug)}/photos", parsers.parse_photos)
   ```

4. Add a test in `tests/test_v2.py`. Prefer a saved page in `tests/fixture/` so the test doesn't depend on the live site.
5. Document the endpoint in [v2.md](v2.md).

## Checks

```sh
uv run ruff format
uv run ruff check
uv run mypy app
uv run pytest -m "not live"   # offline: MDL is faked
uv run pytest -m live         # calls the real MyDramaList site
```

Tests marked `@pytest.mark.live` call the real MyDramaList site, so they need network access and can break when MDL changes its pages. Every other test must fake MDL: `tests/conftest.py` makes any real MDL request fail in an unmarked test.

CI (`ci.yml`) runs the lint, format, mypy and offline-test steps above on every push and PR, and a passing run on `main` triggers the deploy. The live tests run separately (`live.yml`): daily, on PRs and on demand, so an MDL outage or redesign shows up there without blocking a deploy, including the deploy of a fix for it.
