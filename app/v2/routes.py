from typing import Any

from fastapi import APIRouter, Query

from app.v2 import PREFIX, parsers
from app.v2.scraper import scrape

router = APIRouter(prefix=PREFIX, tags=["v2"])

Page = Query(1, ge=1)


@router.get("/search")
async def search(q: str = Query(..., min_length=1), page: int = Page) -> dict[str, Any]:
    return await scrape("search", parsers.parse_search, {"q": q, "page": page})


@router.get("/dramas/{slug}")
async def drama(slug: str) -> dict[str, Any]:
    return await scrape(slug, parsers.parse_drama)


@router.get("/dramas/{slug}/cast")
async def drama_cast(slug: str) -> dict[str, Any]:
    return await scrape(f"{slug}/cast", parsers.parse_cast)


@router.get("/dramas/{slug}/episodes")
async def drama_episodes(slug: str) -> dict[str, Any]:
    return await scrape(f"{slug}/episodes", parsers.parse_episodes)


@router.get("/dramas/{slug}/reviews")
async def drama_reviews(slug: str, page: int = Page) -> dict[str, Any]:
    return await scrape(f"{slug}/reviews", parsers.parse_reviews, {"page": page})


@router.get("/people/{slug}")
async def person(slug: str) -> dict[str, Any]:
    return await scrape(f"people/{slug}", parsers.parse_person)


@router.get("/lists/{list_id}")
async def mdl_list(list_id: str, page: int = Page) -> dict[str, Any]:
    return await scrape(f"list/{list_id}", parsers.parse_list, {"page": page})


@router.get("/users/{username}/dramalist")
async def dramalist(username: str) -> dict[str, Any]:
    return await scrape(f"dramalist/{username}", parsers.parse_dramalist)
