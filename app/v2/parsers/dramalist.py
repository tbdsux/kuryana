from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.v2.parsers._helpers import _float, _int, _key, _link, _slug, _text, _year


def _entry(tr: Tag) -> dict[str, Any] | None:
    a = tr.select_one("a.title")
    if a is None:
        return None

    return {
        "title": _text(a),
        "slug": _slug(a.get("href")),
        "link": _link(a.get("href")),
        "country": _text(tr.select_one("td.mdl-style-col-country")) or None,
        "year": _year(_text(tr.select_one("td.mdl-style-col-year"))),
        "type": _text(tr.select_one("td.mdl-style-col-type")) or None,
        "score": _float(_text(tr.select_one("span.score"))),
        "episodes_seen": _int(_text(tr.select_one("span.episode-seen"))),
        "episodes_total": _int(_text(tr.select_one("span.episode-total"))),
    }


def _stats(section: Tag) -> dict[str, int | float | None]:
    stats: dict[str, int | float | None] = {}

    for label in section.select("label[class^='mdl-style-']"):
        name = label.select_one("span.name")
        if name is None:
            continue

        count = _text(label.select_one("span.cnt"))
        # counts are ints, only `days` is fractional
        stats[_key(_text(name))] = _float(count) if "." in count else _int(count)

    return stats


def parse_dramalist(soup: BeautifulSoup) -> dict[str, Any]:
    lists: dict[str, Any] = {}

    for section in soup.select("div.mdl-style-list"):
        name = _text(section.select_one("h3.mdl-style-list-label"))
        items = [e for tr in section.select("tbody tr") if (e := _entry(tr))]

        lists[_key(name)] = {"name": name, "items": items, "stats": _stats(section)}

    return {"lists": lists}
