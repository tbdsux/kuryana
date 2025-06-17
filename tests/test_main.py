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
                "title": "Guardian: The Lonely and Great God",
                "complete_title": "Guardian: The Lonely and Great God",
            },
        },
        {
            "id": "58953-mouse",
            "expected": {"title": "Mouse", "complete_title": "Mouse"},
        },
    ]

    for i in dramas:
        r = client.get(f"/id/{i['id']}")

        assert r.status_code == 200

        print(r.json()["data"])

        assert r.json()["data"]["title"] == i["expected"]["title"]
        assert r.json()["data"]["complete_title"] == i["expected"]["complete_title"]


def test_unknown_drama() -> None:
    response = client.get("/id/alkdjaklsdjklasd")
    assert response.status_code == 404
    assert response.json() == {
        "error": True,
        "code": 404,
        "description": {
            "title": "The requested page was not found",
            "info": "You can see this page because the URL you are accessing cannot be found.",
        },
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
