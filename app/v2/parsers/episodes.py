from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.v2.parsers._helpers import _float, _img, _int, _link, _meta, _slug, _text


def _episode(ep: Tag) -> dict[str, Any] | None:
    a = ep.select_one("h2.title a")
    if a is None:
        return None

    summary = ep.select_one("div.summary")
    if summary is not None:
        for more in summary.find_all("a"):  # "read more"
            more.decompose()

    panel = ep.select_one("div.rating-panel div")

    return {
        "number": _int(_slug(a.get("href"))),
        "title": _text(a),
        "link": _link(a.get("href")),
        "image": _img(ep.select_one("div.cover")),
        "rating": _float(_text(panel.find("b"))) if panel else None,
        "votes": _int(_text(panel).split("from", 1)[-1]) if panel else None,
        "air_date": _text(ep.select_one("div.air-date")) or None,
        "summary": _text(summary) or None,
    }


def parse_episodes(soup: BeautifulSoup) -> dict[str, Any]:
    episodes = [
        e for ep in soup.select("div.episodes div.episode") if (e := _episode(ep))
    ]

    return {
        "title": _meta(soup, "og:title"),
        "poster": _meta(soup, "og:image"),
        "episodes": episodes,
    }
