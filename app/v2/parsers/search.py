from typing import Any

from bs4 import BeautifulSoup

from app.v2.parsers._helpers import (
    _float,
    _img,
    _int,
    _link,
    _slug,
    _text,
    _title_meta,
    pagination,
)


def parse_search(soup: BeautifulSoup) -> dict[str, Any]:
    dramas: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []

    for box in soup.select("div.col-lg-8.col-md-8 div.box"):
        a = box.select_one("h6.title a")
        if a is None:
            continue

        href = str(a.get("href"))
        is_person = "/people/" in href
        if not (is_person or str(box.get("id", "")).startswith("mdl-")):
            continue  # news / article boxes

        base = {"slug": _slug(href), "link": _link(href), "image": _img(box)}

        if is_person:
            people.append(
                {
                    **base,
                    "name": _text(a),
                    "nationality": _text(box.select_one("div.text-muted")) or None,
                }
            )
            continue

        dramas.append(
            {
                **base,
                "id": _int(str(box.get("id", ""))),
                "title": _text(a),
                **_title_meta(_text(box.select_one("span.text-muted"))),
                "ranking": _int(_text(box.select_one("div.ranking span"))),
                "rating": _float(_text(box.select_one("span.score"))),
            }
        )

    return {"dramas": dramas, "people": people, "pagination": pagination(soup)}
