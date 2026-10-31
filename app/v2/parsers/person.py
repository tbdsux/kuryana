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
    _slug,
    _text,
    _year,
)


def _work(tr: Tag) -> dict[str, Any] | None:
    a = tr.select_one("td.title b a") or tr.select_one("td.title a")
    if a is None:
        return None

    role = tr.select_one("td.role")
    character = _text(role.select_one("div.name")) if role else ""
    role_type = _text(role.select_one("div.roleid")) if role else ""

    return {
        "title": _text(a),
        "slug": _slug(a.get("href")),
        "link": _link(a.get("href")),
        "year": _year(_text(tr.select_one("td.year"))),
        "episodes": _int(_text(tr.select_one("td.episodes"))),
        "rating": _float(_text(tr.select_one("td.text-center div.text-sm"))),
        "character": character or None,
        "role": role_type or None,
    }


def _works(col: Tag) -> dict[str, list[dict[str, Any]]]:
    works: dict[str, list[dict[str, Any]]] = {}

    # pair each table with the heading right before it; some headings (e.g. "Photos") have no table
    for table in col.find_all("table"):
        h5 = table.find_previous("h5")
        if h5 is None:
            continue

        works[_text(h5)] = [w for tr in table.select("tbody tr") if (w := _work(tr))]

    return works


def parse_person(soup: BeautifulSoup) -> dict[str, Any]:
    body = soup.select_one("div.app-body") or soup
    col = body.select_one("div.col-lg-8.col-md-8") or body
    details = _details(body.select("ul.list.m-b-0 li.list-item"))

    about = col.select_one("div.col-sm-8.col-lg-12.col-md-12")
    if about is not None:
        for hidden in about.select("div.hidden-md-up"):
            hidden.decompose()

    return {
        **details,
        "name": _text(body.select_one("h1.film-title")) or details.get("name"),
        "image": _img(body.select_one("div.cover")) or _meta(soup, "og:image"),
        "about": about.get_text().replace("Remove ads", "").strip() if about else "",
        "works": _works(col),
    }
