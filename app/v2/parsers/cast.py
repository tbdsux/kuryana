from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.v2.parsers._helpers import _meta, _person_card, _text


def parse_cast(soup: BeautifulSoup) -> dict[str, Any]:
    cast: dict[str, list[dict[str, Any]]] = {}

    box = soup.select_one("div.box.cast-credits div.box-body")
    if box is not None:
        # each "<h3>Main Role</h3>" is followed by the <ul> of its people
        for h3 in box.find_all("h3"):
            ul = h3.find_next_sibling("ul")
            if not isinstance(ul, Tag):
                continue

            cast[_text(h3)] = [c for li in ul.find_all("li") if (c := _person_card(li))]

    return {
        "title": _meta(soup, "og:title"),
        "poster": _meta(soup, "og:image"),
        "cast": cast,
    }
