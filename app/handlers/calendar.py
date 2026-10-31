from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag


def _text(el: Tag | None) -> str | None:
    return el.get_text(" ", strip=True) if el else None


def _paren(el: Tag | None) -> str | None:
    # "(October 30, 2026 10:00 AM)" -> "October 30, 2026 10:00 AM"
    return el.get_text(strip=True).strip("()") if el else None


def _href(el: Tag | None) -> str | None:
    return str(el["href"]) if el and el.has_attr("href") else None


def _rank(card: Tag, cls: str) -> int | None:
    el = card.select_one(f".{cls} .stats-num")
    return int(el.get_text(strip=True).lstrip("#")) if el else None


def _base(card: Tag) -> dict[str, Any]:
    btn = card.select_one("[data-id]")
    img = card.select_one("img")
    return {
        "id": int(str(btn["data-id"])) if btn else None,
        "cover": str(img["src"]) if img and img.has_attr("src") else None,
    }


def parse_quarter(html: str) -> list[dict[str, Any]]:
    """Parse an `/episode-calendar/qN-YYYY?fragment=1` page."""
    items: list[dict[str, Any]] = []
    category = None
    # section headers (Drama / Movie / TV Show) are siblings of their cards
    for el in BeautifulSoup(html, "lxml").select("h2, .episode-card-large"):
        if el.name == "h2":
            category = el.get_text(strip=True)
            continue

        title = el.select_one(".cover-content .title a")
        score = el.select_one(".score")
        items.append(
            {
                **_base(el),
                "title": _text(title),
                "url": _href(title),
                "category": category,
                "type": _text(el.select_one(".content-type")),
                "released": _text(el.select_one(".release-time")),
                "rating": float(score.get_text(strip=True)) if score else None,
                "ranked": _rank(el, "ranking"),
                "popularity": _rank(el, "popularity"),
                "synopsis": _text(el.select_one(".synopsis")),
                "genres": [g.get_text(strip=True) for g in el.select(".genre")],
            }
        )
    return items


def parse_schedule(html: str) -> list[dict[str, Any]]:
    """Parse an `/episode-calendar?fragment=1` page: the next 7 days of releases."""
    days = []
    for day in BeautifulSoup(html, "lxml").select("div[id^=d]:has(> h2)"):
        items = []
        for card in day.select(".el-card"):
            title = card.select_one("a._600")
            items.append(
                {
                    **_base(card),
                    "title": _text(title),
                    "url": _href(title),
                    "time": _text(card.select_one(".release-time")),
                    "timezone": _text(card.select_one(".calendar-popover-title")),
                    "info": _text(card.select_one(".episode-card-sm > div:last-child")),
                    "episodes": [
                        {
                            "title": _text(line.a),
                            "url": _href(line.a),
                            "time": _text(line.b),
                            "date": _paren(line.select_one(".text-muted")),
                        }
                        for line in card.select(".calendar-popover-line")
                    ],
                }
            )
        days.append(
            {"date": _text(day.small), "weekday": _text(day.h2), "items": items}
        )
    return days
