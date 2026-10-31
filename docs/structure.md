# Project Structure

How the code is laid out and where to make changes.

```
app/
├── __init__.py            MYDRAMALIST_WEBSITE base URL
├── main.py                FastAPI app: middleware, v1 routes, mounts v2
├── client.py              one shared async HTTP client (primp) for MDL requests
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
└── fixture/               saved MDL pages for offline parser tests
docs/                      API docs (v1, v2, wrapper guide) and nginx config
```

## v2 request flow

```
GET /v2/dramas/18452-goblin
  -> routes.drama()
  -> scraper.scrape("18452-goblin", parsers.parse_drama)
       -> client.get()                 fetch the MDL page
       -> non-200?  raise MDLError     (errors.py turns it into the error body)
       -> parse_drama(soup)            pure function: soup -> dict
  -> {"success": true, "data": ..., "link": ..., "scraped_at": ...}
```

Each module has one job:

- **routes.py** only declares URLs and query params, then calls `scrape()`.
- **scraper.py** does the network call and the status-code handling. It knows nothing about any page's layout.
- **parsers/** are pure functions that take a `BeautifulSoup` and return a dict. They never do network calls or raise HTTP errors, so they can be tested against saved HTML in `tests/fixture/`.
- **errors.py** formats every error under `/v2` as `{success: false, data: null, message}`. Routes outside `/v2` keep FastAPI's default error responses.

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
       return await scrape(f"{slug}/photos", parsers.parse_photos)
   ```

4. Add a test in `tests/test_v2.py`. Prefer a saved page in `tests/fixture/` so the test doesn't depend on the live site.
5. Document the endpoint in [v2.md](v2.md).

## Checks

```sh
uv run ruff format app
uv run ruff check app
uv run mypy app
uv run pytest
```

Most tests call the live MyDramaList site, so they need network access and can break when MDL changes its pages.
