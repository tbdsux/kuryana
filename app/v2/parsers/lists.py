from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.v2.parsers._helpers import (
    _float,
    _img,
    _int,
    _link,
    _meta,
    _slug,
    _text,
    _title_meta,
    pagination,
)


def _item(li: Tag) -> dict[str, Any] | None:
    a = li.select_one(".title a") or li.select_one("div.content a")
    if a is None:
        return None

    href = a.get("href")
    meta = _text(li.select_one(".text-muted"))
    base: dict[str, Any] = {
        "slug": _slug(href),
        "link": _link(href),
        "image": _img(li).replace("t.jpg", "c.jpg"),
        "note": _text(li.select_one("div.desc")) or None,
    }

    if "/people/" in str(href):
        return {
            **base,
            "kind": "person",
            "name": _text(a),
            "nationality": meta or None,
        }

    # "12. Goblin" -> 12
    rank = _text(li.select_one("h2.title")).split(".", 1)[0]

    return {
        **base,
        "kind": "title",
        "rank": _int(rank),
        "title": _text(a),
        **_title_meta(meta),
        "rating": _float(_text(li.select_one("div.group-item-rating span"))),
    }


def parse_list(soup: BeautifulSoup) -> dict[str, Any]:
    items = [i for li in soup.select("div.collection-list li") if (i := _item(li))]
    header = soup.select_one("div.box-header")

    return {
        "title": _text(header.find("h1")) if header else _meta(soup, "og:title"),
        "description": _text(header.select_one("div.description")) if header else "",
        "items": items,
        "pagination": pagination(soup),
    }
