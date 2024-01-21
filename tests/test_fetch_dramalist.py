from api.fetch import FetchDramaList
from pathlib import Path
import pytest
from bs4 import BeautifulSoup


@pytest.fixture
def sample_obj():
    dramalist = Path(__file__).parent / "fixture" / "dramalist.html"
    html_content = dramalist.read_text()
    sample_soup = BeautifulSoup(html_content, "html.parser")
    return FetchDramaList(sample_soup, "query", 200, True)


def test_fetch_drama_list(sample_obj):
    sample_obj._get_main_container()
    assert sample_obj.info == {
        "link": "https://mydramalist.com/query",
        "list": {
            "Currently Watching": {
                "items": [
                    {
                        "name": "Death's Game",
                        "id": "733445-i-will-die-soon",
                        "score": "0.0",
                        "episode_seen": "4",
                        "episode_total": "4",
                    },
                    {
                        "name": "Tomorrow",
                        "id": "695963-tomorrow",
                        "score": "0.0",
                        "episode_seen": "4",
                        "episode_total": "16",
                    },
                    {
                        "name": "Welcome to Samdal-ri",
                        "id": "743267-welcome-to-samdalri",
                        "score": "0.0",
                        "episode_seen": "14",
                        "episode_total": "16",
                    },
                ],
                "stats": {
                    "Dramas": "10",
                    "TV Shows": "0",
                    "Episodes": "59",
                    "Movies": "0",
                    "Days": "2.6",
                },
            }
        },
    }
