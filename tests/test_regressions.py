"""Offline regression tests: MDL is faked, so these don't need the network."""

import asyncio
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

import httpx
import primp
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app import client as app_client
from app import main
from app.cache import TTLCache
from app.handlers.calendar import parse_quarter
from app.handlers.fetch import FetchDramaList, FetchList
from app.main import app
from app.v2 import routes
from app.v2.errors import MDLError
from app.v2.parsers._helpers import _int
from app.v2.parsers.drama import _next_episode

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "cache", TTLCache(ttl=60))


def fake_response(status: int, text: str, url: str) -> SimpleNamespace:
    """Stands in for a primp response, including the `aread()` the client awaits."""

    async def aread() -> bytes:
        return text.encode()

    return SimpleNamespace(status_code=status, text=text, url=url, aread=aread)


def fake_mdl(
    monkeypatch: pytest.MonkeyPatch, status: int = 200, text: str = "<html></html>"
) -> list[tuple[str, Any]]:
    """Replace the primp client; returns the (url, params) of every request."""
    calls: list[tuple[str, Any]] = []

    async def get(url: str, params: Any = None) -> SimpleNamespace:
        calls.append((url, params))
        return fake_response(status, text, url)

    monkeypatch.setattr(app_client, "client", SimpleNamespace(get=get))
    return calls


@pytest.mark.parametrize(
    "path",
    [
        "http:127.0.0.1:8080",
        "HTTP:169.254.169.254",
        "//evil.com",
        "http://evil.com",
        "/people/x",
    ],
)
def test_mdl_url_never_leaves_mdl(path: str) -> None:
    assert urlparse(app_client.mdl_url(path)).hostname == "mydramalist.com"


@pytest.mark.parametrize("url", ["/v2/dramas/http:127.0.0.1:1", "/id/http:127.0.0.1:1"])
def test_slug_cannot_redirect_scrape(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    calls = fake_mdl(monkeypatch)
    client.get(url)
    assert urlparse(calls[0][0]).hostname == "mydramalist.com"


def test_v1_search_query_is_encoded(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_mdl(monkeypatch)
    client.get("/search/q/Love & War")
    assert calls == [("https://mydramalist.com/search", {"q": "Love & War"})]


def test_nonstandard_upstream_status(monkeypatch: pytest.MonkeyPatch) -> None:
    assert MDLError(522).message == "MyDramaList returned HTTP 522"

    fake_mdl(monkeypatch, status=522)
    r = client.get("/v2/dramas/x")
    assert r.status_code == 522
    assert r.json()["message"] == "MyDramaList returned HTTP 522"


def test_unhandled_error_keeps_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_mdl(monkeypatch)

    def boom(soup: BeautifulSoup) -> dict[str, Any]:
        raise ValueError("parser bug")

    monkeypatch.setattr(routes.parsers, "parse_cast", boom)

    r = client.get("/v2/dramas/x/cast", headers={"Origin": "https://example.com"})
    assert r.status_code == 500
    assert r.headers["access-control-allow-origin"]
    assert r.json() == {
        "success": False,
        "data": None,
        "message": "Internal Server Error",
    }


def test_v1_calendar_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def get(url: str, params: Any = None) -> None:
        raise primp.PrimpError("connection refused")

    monkeypatch.setattr(app_client, "client", SimpleNamespace(get=get))
    r = client.get("/schedule")
    assert r.status_code == 502
    assert r.json()["code"] == 502


def test_cache_is_bounded() -> None:
    cache: TTLCache[int] = TTLCache(ttl=60, max_size=3)
    for i in range(10):
        cache.set(i, i)

    assert len(cache._data) == 3
    assert [cache.get(i) for i in (6, 7, 8, 9)] == [None, 7, 8, 9]


def test_cache_reset_moves_key_to_newest() -> None:
    cache: TTLCache[str] = TTLCache(ttl=60, max_size=2)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("a", "3")  # "a" is now the newest, so "b" goes first
    cache.set("c", "4")
    assert (cache.get("a"), cache.get("b"), cache.get("c")) == ("3", None, "4")


def test_int_takes_first_number() -> None:
    assert _int("#1,234") == 1234
    assert _int("12.5") == 12
    assert _int("scored by 123,456 users") == 123456
    assert _int("N/A") is None


def test_next_episode_bad_json() -> None:
    soup = BeautifulSoup("<script>var nextEpisodeAiring = {not json};</script>", "lxml")
    assert _next_episode(soup) is None


def test_v1_list_single_episode() -> None:
    li = BeautifulSoup(
        '<li><h2><a href="/1-x">X</a></h2>'
        '<div class="text-muted">Korean Special - 2020, 1 episode</div></li>',
        "html.parser",
    ).li
    assert li is not None
    show = FetchList(None, "list/1", 200, True)._parse_show(li)  # type: ignore[arg-type]
    assert (show["type"], show["year"], show["episodes"]) == (
        "Korean Special",
        "2020",
        1,
    )

    li = BeautifulSoup('<li><h2><a href="/1-x">X</a></h2></li>', "html.parser").li
    assert li is not None
    show = FetchList(None, "list/1", 200, True)._parse_show(li)  # type: ignore[arg-type]
    assert (show["type"], show["year"], show["episodes"]) == ("", "", None)


def test_v1_dramalist_rows_stay_aligned() -> None:
    # the first row has no score span: its neighbours must keep their own values
    html = (
        '<div class="mdl-style-list"><table><tbody>'
        '<tr><td><a class="title" href="/1-a">A</a></td>'
        '<td><span class="episode-seen">1</span><span class="episode-total">2</span></td></tr>'
        '<tr><td><a class="title" href="/2-b">B</a></td><td><span class="score">9.0</span>'
        '<span class="episode-seen">3</span><span class="episode-total">4</span></td></tr>'
        "</tbody></table></div>"
    )
    f = FetchDramaList(BeautifulSoup(html, "html.parser"), "dramalist/x", 200, True)
    f._get_main_container()
    a, b = f.info["list"][""]["items"]
    assert (a["score"], a["episode_seen"]) == ("", "1")
    assert (b["score"], b["episode_seen"]) == ("9.0", "3")


def test_calendar_numbers_with_commas() -> None:
    html = (
        '<div class="episode-card-large"><div class="score">N/A</div>'
        '<div class="ranking"><span class="stats-num">#1,234</span></div></div>'
    )
    [item] = parse_quarter(html)
    assert item["ranked"] == 1234
    assert item["rating"] is None


# --- round 2 ---


def test_v1_search_result_without_link() -> None:
    from app.handlers.search import Search

    html = (
        '<div class="col-lg-8 col-md-8"><div class="box">'
        '<h6 class="text-primary title">No link</h6></div></div>'
    )
    s = Search(BeautifulSoup(html, "html.parser"), "x", 200, True)
    s._get_search_results()
    assert s.search_results == {"dramas": [], "people": []}


@pytest.mark.parametrize(
    ("url", "mdl"),
    [
        ("/v2/dramas/a%3Fx=1", "https://mydramalist.com/a%3Fx%3D1"),
        ("/v2/dramas/a%23b/cast", "https://mydramalist.com/a%23b/cast"),
        ("/id/a%3Fx=1", "https://mydramalist.com/a%3Fx%3D1"),
        ("/v2/dramas/18452-goblin", "https://mydramalist.com/18452-goblin"),
    ],
)
def test_slug_is_one_encoded_segment(
    monkeypatch: pytest.MonkeyPatch, url: str, mdl: str
) -> None:
    calls = fake_mdl(monkeypatch)
    client.get(url)
    assert calls[0][0] == mdl


def test_v2_405_keeps_allow_header() -> None:
    r = client.post("/v2/search")
    assert r.status_code == 405
    assert r.headers["allow"] == "GET"
    assert r.json()["success"] is False


def test_bare_v2_prefix_uses_v2_errors() -> None:
    r = client.get("/v2")
    assert r.json() == {"success": False, "data": None, "message": "Not Found"}


def test_cdn_ttl_matches_memory_ttl_left(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_mdl(monkeypatch)
    first = client.get("/v2/dramas/x")
    assert first.headers["cache-control"] == "public, max-age=0, s-maxage=60"

    # age the stored entry by 45s: the CDN may only keep it for the 15s left
    [(key, (stored_at, value, size))] = main.cache._data.items()
    main.cache._data[key] = (stored_at - 45, value, size)

    hit = client.get("/v2/dramas/x")
    assert hit.headers["cache-control"] == "public, max-age=0, s-maxage=15"
    assert hit.content == first.content


def test_route_cache_control_is_kept() -> None:
    from fastapi import Response

    cache: TTLCache[Response] = main.cache
    cache.set("/?", Response(b"{}", headers={"cache-control": "no-store"}))
    assert client.get("/").headers["cache-control"] == "no-store"


def test_cache_get_entry() -> None:
    cache: TTLCache[str] = TTLCache(ttl=60)
    assert cache.get_entry("a") is None
    cache.set("a", "1")
    entry = cache.get_entry("a")
    assert entry is not None and entry[0] == "1" and 59 < entry[1] <= 60


def test_v1_drama_without_subtitle_keeps_other_fields() -> None:
    from app.handlers.fetch import FetchDrama

    html = (
        '<div class="app-body"><h1 class="film-title">X</h1>'
        '<div class="col-film-rating"><div>8.5</div></div>'
        '<img src="https://i.mydramalist.com/p.jpg"></div>'
    )
    f = FetchDrama(BeautifulSoup(html, "html.parser"), "1-x", 200, True)
    f._get_main_container()
    assert (f.info["title"], f.info["rating"]) == ("X", 8.5)
    assert f.info["poster"] == "https://i.mydramalist.com/p.jpg"
    assert "year" not in f.info


def test_v1_person_without_about_keeps_profile() -> None:
    from app.handlers.fetch import FetchPerson

    html = (
        '<div class="app-body"><h1 class="film-title">Y</h1>'
        '<img src="https://i.mydramalist.com/y.jpg"></div>'
    )
    f = FetchPerson(BeautifulSoup(html, "html.parser"), "people/1-y", 200, True)
    f._get_main_container()
    assert f.info["profile"] == "https://i.mydramalist.com/y.jpg"
    assert f.info["works"] == {}


# --- round 3 ---


def test_cache_byte_budget() -> None:
    cache: TTLCache[bytes] = TTLCache(ttl=60, max_size=100, max_bytes=10, sizeof=len)
    cache.set("a", b"1234")
    cache.set("b", b"1234")
    cache.set("c", b"1234")  # 12 bytes > 10: the oldest goes
    assert (cache.get("a"), cache.get("b"), cache.get("c")) == (None, b"1234", b"1234")
    assert cache._bytes == 8

    cache.set("b", b"1")  # replacing an entry releases its old size
    assert cache._bytes == 5

    cache.set("huge", b"x" * 11)  # bigger than the whole budget: not kept at all
    assert cache.get("huge") is None and cache._bytes <= 10


def _slow_mdl(
    monkeypatch: pytest.MonkeyPatch, status: int = 200
) -> tuple[list[str], dict[str, int]]:
    calls: list[str] = []
    stats = {"running": 0, "peak": 0}

    async def get(url: str, params: Any = None) -> SimpleNamespace:
        calls.append(url)
        stats["running"] += 1
        stats["peak"] = max(stats["peak"], stats["running"])
        await asyncio.sleep(0.05)
        stats["running"] -= 1
        return fake_response(status, "<html></html>", url)

    monkeypatch.setattr(app_client, "client", SimpleNamespace(get=get))
    return calls, stats


async def _burst(urls: list[str]) -> list[httpx.Response]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
        return list(await asyncio.gather(*[ac.get(u) for u in urls]))


def test_identical_requests_share_one_scrape(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, _ = _slow_mdl(monkeypatch)
    responses = asyncio.run(_burst(["/v2/dramas/x"] * 10))

    assert len(calls) == 1
    assert {r.status_code for r in responses} == {200}
    assert len({r.content for r in responses}) == 1
    assert main._inflight == {}


def test_shared_errors_are_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, _ = _slow_mdl(monkeypatch, status=503)
    responses = asyncio.run(_burst(["/v2/dramas/x"] * 5))

    assert len(calls) == 1
    assert {r.status_code for r in responses} == {503}
    assert main.cache.get("/v2/dramas/x?") is None


def test_mdl_requests_are_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, stats = _slow_mdl(monkeypatch)
    asyncio.run(_burst([f"/v2/dramas/x{i}" for i in range(30)]))

    assert len(calls) == 30
    assert stats["peak"] == app_client.MAX_CONCURRENT_REQUESTS


# --- round 4 ---


def test_body_is_read_inside_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    sem = asyncio.Semaphore(1)
    monkeypatch.setattr(app_client, "_limit", lambda: sem)

    async def aread() -> bytes:
        events.append(f"aread, slot taken: {sem.locked()}")
        return b""

    async def get(url: str, params: Any = None) -> SimpleNamespace:
        return SimpleNamespace(status_code=200, text="", url=url, aread=aread)

    monkeypatch.setattr(app_client, "client", SimpleNamespace(get=get))
    client.get("/v2/dramas/x")
    assert events == ["aread, slot taken: True"]


@pytest.mark.parametrize(
    ("url", "status"), [("/v2/dramas/x", 502), ("/schedule", 502), ("/id/x", 500)]
)
def test_body_read_error_is_handled(
    monkeypatch: pytest.MonkeyPatch, url: str, status: int
) -> None:
    async def aread() -> bytes:
        raise primp.BodyError("connection reset mid-body")

    async def get(url: str, params: Any = None) -> SimpleNamespace:
        return SimpleNamespace(status_code=200, text="", url=url, aread=aread)

    monkeypatch.setattr(app_client, "client", SimpleNamespace(get=get))
    r = client.get(url)
    # v2 and the calendar say 502; v1 pages report any fetch failure as 500, as before
    assert r.status_code == status
    assert r.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("url", ["/v2/dramas/x", "/schedule", "/id/x"])
def test_busy_queue_returns_503(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    fake_mdl(monkeypatch)
    no_slots = asyncio.Semaphore(0)
    monkeypatch.setattr(app_client, "_limit", lambda: no_slots)
    monkeypatch.setattr(app_client, "QUEUE_TIMEOUT", 0.01)

    r = client.get(url)
    assert r.status_code == 503


@pytest.mark.parametrize("url", ["/v2/people/%2E%2E", "/v2/dramas/%2E", "/id/%2E%2E"])
def test_dot_slugs_are_refused(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    calls = fake_mdl(monkeypatch)
    assert client.get(url).status_code == 404
    assert calls == []


def test_cache_key_ignores_undeclared_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = fake_mdl(monkeypatch)
    for u in ["/v2/dramas/x", "/v2/dramas/x?cb=1", "/v2/dramas/x?cb=2&page=9"]:
        assert client.get(u).status_code == 200
    assert len(calls) == 1  # none of those params exist on this route

    calls.clear()
    client.get("/v2/search?q=a&page=2")
    client.get("/v2/search?page=2&q=a&junk=1")  # same declared params, reordered
    client.get("/v2/search?q=b&page=2")  # a declared param differs
    assert len(calls) == 2


def test_waiter_takes_over_when_first_request_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls, _ = _slow_mdl(monkeypatch)

    async def run() -> list[Any]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as ac:
            first = asyncio.create_task(ac.get("/v2/dramas/k"))
            await asyncio.sleep(0.01)
            waiters = [asyncio.create_task(ac.get("/v2/dramas/k")) for _ in range(4)]
            await asyncio.sleep(0.01)
            first.cancel()
            return await asyncio.gather(*waiters)

    responses = asyncio.run(run())
    assert [r.status_code for r in responses] == [200] * 4
    assert len(calls) == 2  # the cancelled one, then a single takeover
    assert main._inflight == {}


def test_v1_person_works_skip_tableless_boxes() -> None:
    from app.handlers.fetch import FetchPerson

    html = (
        '<div class="app-body"><h1 class="film-title">Y</h1>'
        '<div class="col-lg-8 col-md-8">'
        '<div class="box-body">bio</div>'
        '<div class="box-body"><h5>Photos</h5><img src="x.jpg"></div>'
        '<div class="box-body"><h5>Drama</h5><table><tbody><tr class="mdl-1">'
        '<td class="year">2016</td><td class="title">'
        '<a href="/1-goblin"><img alt="Goblin"></a><b><a href="/1-goblin">Goblin</a></b>'
        "</td></tr></tbody></table></div></div></div>"
    )
    f = FetchPerson(BeautifulSoup(html, "html.parser"), "people/1-y", 200, True)
    f._get_main_container()
    assert list(f.info["works"]) == ["Drama"]
    [work] = f.info["works"]["Drama"]
    assert work["title"]["name"] == "Goblin"
    assert work["year"] == 2016


def test_non_numeric_ids_and_pages_dont_crash() -> None:
    from app.v2.parsers._helpers import pagination

    html = '<div class="episode-card-large"><button data-id="abc"></button></div>'
    [item] = parse_quarter(html)
    assert item["id"] is None

    soup = BeautifulSoup(
        '<ul class="pagination"><li class="active">1</li>'
        '<a class="page-link" href="?page=x"></a><a class="page-link" href="?page=3"></a></ul>',
        "lxml",
    )
    assert pagination(soup) == {"page": 1, "total_pages": 3}
