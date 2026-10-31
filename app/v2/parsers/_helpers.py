"""Shared, None-safe extractors used by every v2 page parser.

A missing element yields None / "" / [] instead of an exception. Slugs never
carry a leading slash and match the v2 route params.
"""

import re
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from app import MYDRAMALIST_WEBSITE

LIST_KEYS = {
    "also_known_as",
    "genres",
    "tags",
    "screenwriter",
    "director",
    "screenwriter_and_director",
    "original_network",
    "aired_on",
}
INT_KEYS = {"episodes", "ranked", "popularity", "watchers", "favorites", "age"}


# --- primitives ---


def _text(el: Tag | None) -> str:
    return el.get_text(" ", strip=True) if el is not None else ""


def _int(s: str | None) -> int | None:
    digits = re.sub(r"[^\d]", "", s or "")
    return int(digits) if digits else None


def _float(s: str | None) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", s or "")
    return float(m.group()) if m else None


def _year(s: str | None) -> int | None:
    m = re.search(r"\b(\d{4})\b", s or "")
    return int(m.group(1)) if m else None


def _key(s: str) -> str:
    return re.sub(r"\W+", "_", s.lower().replace("&", "and")).strip("_")


def _link(href: Any) -> str:
    return urljoin(MYDRAMALIST_WEBSITE, str(href)) if href else ""


def _slug(href: Any) -> str:
    # "/people/440-gong-yoo" -> "440-gong-yoo", "/18452-goblin" -> "18452-goblin"
    return urlparse(str(href or "")).path.rstrip("/").rsplit("/", 1)[-1]


def _img(el: Tag | None) -> str:
    img = el if el is None or el.name == "img" else el.find("img")
    if not isinstance(img, Tag):
        return ""

    src = img.get("data-src") or img.get("data-cfsrc") or img.get("src") or ""
    return _link(src)


def _meta(soup: BeautifulSoup, prop: str) -> str:
    m = soup.find("meta", property=prop)
    return str(m.get("content", "")) if isinstance(m, Tag) else ""


def _split(raw: str) -> list[str]:
    # AKA titles may contain ", " themselves, MDL separates them with " ,"
    sep = r"\s+," if " ," in raw else ","
    return [s.strip() for s in re.split(sep, raw) if s.strip()]


# --- shared blocks ---


def _details(items: list[Tag]) -> dict[str, Any]:
    """`<li><b>Key:</b> value</li>` rows -> typed dict (first occurrence wins)."""
    out: dict[str, Any] = {}

    for li in items:
        b = li.find("b")
        if b is None:
            continue

        key = _key(b.get_text().replace(":", ""))
        if not key or key in out:
            continue

        b.extract()
        raw = li.get_text().strip()

        if key == "score":
            out["rating"] = _float(raw)
            out["scored_by"] = _int(raw.split("by", 1)[-1]) if "by" in raw else None
        elif key in LIST_KEYS:
            anchors = [_text(a) for a in li.find_all("a")]
            values = anchors or _split(raw)
            out[key] = [v for v in values if v and "vote tags" not in v.lower()]
        elif key in INT_KEYS:
            out[key] = _int(raw)
        else:
            out[key] = " ".join(raw.split())

    return out


def _person_card(li: Tag) -> dict[str, Any] | None:
    """cast / credits card: name, image, character and role."""
    a = li.select_one("a.text-primary")
    if a is None:
        return None

    char = li.select_one("small a, div.text-ellipsis small")
    role = li.select_one("small.text-muted")

    return {
        "name": _text(a.find("b") or a),
        "slug": _slug(a.get("href")),
        "link": _link(a.get("href")),
        # `_5s` (small) -> `_5m` (medium)
        "image": _img(li).replace("s.jpg", "m.jpg"),
        "character": _text(char) or None,
        "role": _text(role) or None,
    }


def _title_meta(meta: str) -> dict[str, Any]:
    """`"Korean Drama - 2016, 16 episodes"` -> type, year and episode count."""
    kind, _, rest = meta.partition(" - ")
    eps = re.search(r"(\d+)\s+episodes?", rest)

    return {
        "type": kind.strip() or None,
        "year": _year(rest),
        "episodes": int(eps.group(1)) if eps else None,
    }


def pagination(soup: BeautifulSoup) -> dict[str, int]:
    pages = [1]
    for a in soup.select("ul.pagination a.page-link[href]"):
        query = parse_qs(urlparse(str(a["href"])).query)
        pages += [int(p) for p in query.get("page", [])]

    current = _int(_text(soup.select_one("ul.pagination li.active"))) or 1
    return {"page": current, "total_pages": max(pages + [current])}


def error_info(soup: BeautifulSoup) -> dict[str, str]:
    box = soup.select_one("div.app-body div.box-body")
    if box is None:
        return {}

    return {"title": _text(box.find("h1")), "info": _text(box.find("p"))}
