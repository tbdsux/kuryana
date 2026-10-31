from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert (
        response.json()["message"] == "A Simple and Basic MDL Scraper API"
    )  # this is weird


def test_sample_drama() -> None:
    dramas = [
        {
            "id": "18452-goblin",
            "expected": {
                "title": "Guardian: The Lonely and Great God (2016)",
                "complete_title": "Guardian: The Lonely and Great God (2016)",
            },
        },
        {
            "id": "58953-mouse",
            "expected": {"title": "Mouse (2021)", "complete_title": "Mouse (2021)"},
        },
    ]

    for i in dramas:
        r = client.get(f"/id/{i['id']}")

        assert r.status_code == 200

        print(r.json()["data"])

        assert r.json()["data"]["title"] == i["expected"]["title"]
        assert r.json()["data"]["complete_title"] == i["expected"]["complete_title"]


def test_unknown_drama() -> None:
    # MDL answers unknown drama ids with an empty 500, not a 404 page
    response = client.get("/id/alkdjaklsdjklasd")
    assert response.status_code == 500
    assert response.json() == {
        "error": True,
        "code": 500,
        "description": "An unexpected error occurred.",
    }


def test_sample_people() -> None:
    response = client.get("/people/4444-kim-jong-min")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Kim Jong Min"


def test_unknown_people() -> None:
    response = client.get("/people/asdasdadadasdadasdasdaswerwer")
    assert response.status_code == 404
    assert response.json() == {
        "error": True,
        "code": 404,
        "description": {
            "title": "The requested page was not found",
            "info": "You can see this page because the URL you are accessing cannot be found.",
        },
    }


def test_unknown_endpoint() -> None:
    response = client.get("/unknown")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_seasonal() -> None:
    response = client.get("/seasonal/2026/4")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert {"Drama", "Movie"} <= {i["category"] for i in items}
    assert all(isinstance(i["id"], int) and i["title"] for i in items)


def test_seasonal_invalid() -> None:
    assert client.get("/seasonal/abcd/4").status_code == 422
    assert client.get("/seasonal/2026/9").status_code == 422


def test_schedule() -> None:
    response = client.get("/schedule")
    assert response.status_code == 200
    days = response.json()
    assert len(days) == 7
    items = [i for d in days for i in d["items"]]
    assert len(items) > 0
    assert all(i["title"] and i["episodes"] for i in items)
