from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.v2.parsers._helpers import (
    _float,
    _img,
    _int,
    _key,
    _link,
    _meta,
    _slug,
    _text,
    pagination,
)

REVIEW_JUNK = "div.box, p.read-more, div.review-helpful, div.review-spoiler, strong"


def _ratings(div: Tag) -> dict[str, float | None]:
    ratings: dict[str, float | None] = {
        "overall": _float(_text(div.select_one("div.rating-overall span.score")))
    }

    # "Story 9.0", "Acting/Cast 8.5", ...
    for row in div.select("div.review-rating > div"):
        span = row.find("span")
        if span is None:
            continue

        name = row.get_text().replace(span.get_text(), "")
        ratings[_key(name)] = _float(_text(span))

    return ratings


def _body(div: Tag) -> tuple[str | None, str]:
    """-> (headline, body text) with the UI clutter stripped."""
    body = div.select_one("div.review-body")
    if body is None:
        return None, ""

    headline = _text(body.find("strong")) or None

    for junk in body.select(REVIEW_JUNK):
        junk.decompose()
    for br in body.find_all("br"):
        br.replace_with("\n")

    return headline, body.get_text().strip()


def _review(div: Tag) -> dict[str, Any]:
    user = div.select_one("b a[href*='/profile/']")
    seen = div.select("div.episodes-seen b")
    avatar = _img(div.select_one("span.avatar"))

    # read ratings and the spoiler flag before `_body` decomposes them
    ratings = _ratings(div)
    spoiler = div.select_one("div.review-spoiler") is not None
    headline, body = _body(div)

    return {
        "id": _int(str(div.get("id", ""))),
        "reviewer": {
            "name": _text(user),
            "slug": _slug(user.get("href")) if user else "",
            "link": _link(user.get("href")) if user else "",
            "image": avatar.replace("1t.jpg", "1c.jpg"),
        },
        "helpful": _int(_text(div.select_one("div.user-stats b"))) or 0,
        "date": _text(div.select_one("small.datetime")) or None,
        "status": _text(div.select_one("span.review-tag")) or None,
        "episodes_seen": _int(_text(seen[0])) if seen else None,
        "episodes_total": _int(_text(seen[1])) if len(seen) > 1 else None,
        "spoiler": spoiler,
        "headline": headline,
        "body": body,
        "ratings": ratings,
    }


def parse_reviews(soup: BeautifulSoup) -> dict[str, Any]:
    return {
        "title": _meta(soup, "og:title"),
        "poster": _meta(soup, "og:image"),
        "reviews": [_review(d) for d in soup.select("div.review")],
        "pagination": pagination(soup),
    }
