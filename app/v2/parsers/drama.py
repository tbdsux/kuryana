import json
import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.v2.parsers._helpers import (
    _details,
    _float,
    _img,
    _int,
    _link,
    _meta,
    _person_card,
    _slug,
    _text,
    _year,
)


def _related(div: Tag) -> dict[str, Any]:
    a = div.find("a")
    if a is None:
        return {"title": _text(div), "slug": "", "link": "", "relation": ""}

    return {
        "title": _text(a),
        "slug": _slug(a.get("href")),
        "link": _link(a.get("href")),
        "relation": _text(div).replace(_text(a), "").strip(" ()"),
    }


def _next_episode(soup: BeautifulSoup) -> dict[str, Any] | None:
    for script in soup.find_all("script"):
        if not (script.string and "var nextEpisodeAiring =" in script.string):
            continue

        m = re.search(r"var nextEpisodeAiring = ({.*?});", script.string)
        if m is None:
            return None

        raw = json.loads(m.group(1))  # MDL sends every value as a string
        return {
            "episode_number": _int(raw.get("episode_number")),
            "total_episodes": _int(raw.get("episodes")),
            "released_at": _int(raw.get("released_at")),  # unix seconds
            "duration": _int(raw.get("duration")),  # minutes
            "timezone": raw.get("timezone"),
        }

    return None


def parse_drama(soup: BeautifulSoup) -> dict[str, Any]:
    body = soup.select_one("div.app-body") or soup

    details = _details(
        body.select("div.show-detailsxss li.list-item")
        + body.select("div.box-body.light-b li.list-item")
    )
    details.pop("related_content", None)

    related = [_related(div) for div in body.select("li.related-content div.title")]

    synopsis = body.select_one("div.show-synopsis p")
    if synopsis is not None:
        for a in synopsis.find_all("a"):  # "Edit Translation"
            a.decompose()

    cast = [c for li in body.select("li.list-item.col-sm-4") if (c := _person_card(li))]
    rating = body.select_one("div.col-film-rating")
    subtitle = _text(body.select_one("div.film-subtitle"))

    return {
        "id": _int(str(rating.get("data-id"))) if rating else None,
        "title": details.pop("title", None) or _meta(soup, "og:title"),
        "complete_title": _text(body.select_one("h1.film-title")),
        "year": _year(subtitle.split("‧")[-1]),
        **details,
        "rating": _float(_text(rating)) if rating else details.get("rating"),
        "poster": _img(body.select_one("div.film-cover")) or _meta(soup, "og:image"),
        "synopsis": synopsis.get_text().strip() if synopsis else "",
        "cast": cast,
        "related": related,
        "next_episode": _next_episode(soup),
    }
