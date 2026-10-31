from pathlib import Path

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from app.main import app
from app.v2.parsers import parse_dramalist

client = TestClient(app)


def test_parse_dramalist_fixture() -> None:
    soup = BeautifulSoup(
        (Path(__file__).parent / "fixture" / "dramalist.html").read_text(), "lxml"
    )
    lists = parse_dramalist(soup)["lists"]
    watching = lists["currently_watching"]

    assert watching["name"] == "Currently Watching"
    assert watching["stats"] == {
        "dramas": 10,
        "tv_shows": 0,
        "episodes": 59,
        "movies": 0,
        "days": 2.6,
    }
    assert watching["items"][1] == {
        "title": "Tomorrow",
        "slug": "695963-tomorrow",
        "link": "https://mydramalist.com/695963-tomorrow",
        "country": "South Korea",
        "year": 2022,
        "type": "Drama",
        "score": 0.0,
        "episodes_seen": 4,
        "episodes_total": 16,
    }


def test_search() -> None:
    r = client.get("/v2/search", params={"q": "goblin"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["pagination"]["page"] == 1
    assert all(d["id"] and d["slug"] for d in data["dramas"])


def test_drama() -> None:
    r = client.get("/v2/dramas/18452-goblin")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["id"] == 18452
    assert data["title"] == "Guardian: The Lonely and Great God"
    assert data["complete_title"] == "Guardian: The Lonely and Great God (2016)"
    assert data["year"] == 2016
    assert data["episodes"] == 16
    assert isinstance(data["rating"], float)
    assert data["cast"][0]["slug"] == "440-gong-yoo"


def test_drama_subpages() -> None:
    cast = client.get("/v2/dramas/18452-goblin/cast").json()["data"]
    assert "Main Role" in cast["cast"]

    episodes = client.get("/v2/dramas/18452-goblin/episodes").json()["data"]
    assert episodes["episodes"][0]["number"] == 1

    reviews = client.get("/v2/dramas/18452-goblin/reviews?page=2").json()["data"]
    assert reviews["pagination"]["page"] == 2
    assert reviews["reviews"][0]["ratings"]["overall"] is not None


def test_unknown_drama() -> None:
    r = client.get("/v2/dramas/alkdjaklsdjklasd")
    assert r.status_code == 404
    assert r.json() == {"success": False, "data": None, "message": "Not Found"}


def test_person() -> None:
    r = client.get("/v2/people/4444-kim-jong-min")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["name"] == "Kim Jong Min"
    assert isinstance(data["age"], int)


def test_unknown_person() -> None:
    r = client.get("/v2/people/asdasdadadasdadasdasdaswerwer")
    assert r.status_code == 404
    assert r.json() == {
        "success": False,
        "data": None,
        "message": "The requested page was not found. "
        "You can see this page because the URL you are accessing cannot be found.",
    }


def test_list() -> None:
    r = client.get("/v2/lists/E1VK0WEL?page=2")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["pagination"]["page"] == 2
    assert data["items"][0]["rank"] > 1


def test_search_requires_query() -> None:
    r = client.get("/v2/search")
    assert r.status_code == 422
    assert r.json() == {"success": False, "data": None, "message": "q: Field required"}


def test_unknown_v2_route() -> None:
    r = client.get("/v2/nope")
    assert r.status_code == 404
    assert r.json() == {"success": False, "data": None, "message": "Not Found"}


def test_success_envelope() -> None:
    body = client.get("/v2/people/4444-kim-jong-min").json()
    assert set(body) == {"success", "data", "link", "scraped_at"}
    assert body["success"] is True
    assert body["link"] == "https://mydramalist.com/people/4444-kim-jong-min"
    assert "link" not in body["data"]


def test_v1_errors_unchanged() -> None:
    assert client.get("/nope").json() == {"detail": "Not Found"}
    assert client.get("/id/x/reviews?page=abc").json()["detail"][0]["loc"] == [
        "query",
        "page",
    ]
