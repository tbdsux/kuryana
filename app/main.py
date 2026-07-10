import logging
from typing import Any, Dict, List

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.handlers.calendar import FetchSchedule, FetchSeasonal
from app.lib.msgspec_json import MsgSpecJSONResponse
from app.schemas import (
    CastResponse,
    DramaResponse,
    DramalistResponse,
    EpisodesResponse,
    ErrorResponse,
    ListResponse,
    PersonResponse,
    PhotosResponse,
    ReviewsResponse,
    ScheduleResponse,
    SearchResponse,
    SeasonalItem,
)
from app.utils import fetch_func, search_func

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kuryana",
    description="A simple MyDramaList.com scraper API.",
    default_response_class=MsgSpecJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_error_responses = {
    400: {"model": ErrorResponse, "description": "Page error returned by MDL"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


@app.get("/")
async def index() -> Dict[str, Any]:
    return {"message": "A Simple and Basic MDL Scraper API"}


@app.get(
    "/health",
    tags=["health"],
    summary="Liveness check",
    description="Confirms the process is up and the event loop is responsive. Does not call MDL.",
)
async def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get(
    "/search/q/{query}",
    response_model=SearchResponse,
    tags=["search"],
    summary="Search dramas and people",
)
async def search(query: str, response: Response) -> Dict[str, Any]:
    code, r = await search_func(query=query)
    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}",
    response_model=DramaResponse,
    tags=["drama"],
    summary="Drama details",
    responses=_error_responses,
)
async def fetch(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=drama_id, t="drama")
    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/cast",
    response_model=CastResponse,
    tags=["drama"],
    summary="Drama full cast",
    responses=_error_responses,
)
async def fetch_cast(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/cast", t="cast")
    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/episodes",
    response_model=EpisodesResponse,
    tags=["drama"],
    summary="Drama episodes",
    responses=_error_responses,
)
async def fetch_episodes(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/episodes", t="episodes")
    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/reviews",
    response_model=ReviewsResponse,
    tags=["drama"],
    summary="Drama reviews",
    responses=_error_responses,
)
async def fetch_reviews(
    drama_id: str, response: Response, page: int = 1
) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/reviews?page={page}", t="reviews")
    response.status_code = code
    return r


@app.get(
    "/id/{drama_id}/photos",
    response_model=PhotosResponse,
    tags=["drama"],
    summary="Drama photos",
    responses=_error_responses,
)
async def fetch_drama_photos(drama_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"{drama_id}/photos", t="photos")
    response.status_code = code
    return r


@app.get(
    "/people/{person_id}",
    response_model=PersonResponse,
    tags=["people"],
    summary="Person details",
    responses=_error_responses,
)
async def person(person_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"people/{person_id}", t="person")
    response.status_code = code
    return r


@app.get(
    "/people/{person_id}/photos",
    response_model=PhotosResponse,
    tags=["people"],
    summary="Person photos",
    responses=_error_responses,
)
async def fetch_person_photos(person_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"people/{person_id}/photos", t="photos")
    response.status_code = code
    return r


@app.get(
    "/dramalist/{user_id}",
    response_model=DramalistResponse,
    tags=["user"],
    summary="User drama list",
    responses=_error_responses,
)
async def dramalist(user_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"dramalist/{user_id}", t="dramalist")
    response.status_code = code
    return r


@app.get(
    "/list/{list_id}",
    response_model=ListResponse,
    tags=["list"],
    summary="MDL curated list",
    responses=_error_responses,
)
async def lists(list_id: str, response: Response) -> Dict[str, Any]:
    code, r = await fetch_func(query=f"list/{list_id}", t="lists")
    response.status_code = code
    return r


@app.get(
    "/seasonal/{year}/{quarter}",
    response_model=List[SeasonalItem],
    tags=["calendar"],
    summary="Seasonal drama list",
    description="Dramas airing in the given quarter. `quarter`: 1 = Jan–Mar · 2 = Apr–Jun · 3 = Jul–Sep · 4 = Oct–Dec.",
)
async def mdlSeasonal(year: int, quarter: int, response: Response) -> Any:
    try:
        status, data = await FetchSeasonal.scrape(
            f"https://mydramalist.com/episode-calendar/q{quarter}-{year}"
        )
    except Exception as exc:
        logger.error("FetchSeasonal failed: %s", exc)
        response.status_code = 502
        return []
    response.status_code = status
    return data


@app.get(
    "/schedule",
    response_model=ScheduleResponse,
    tags=["calendar"],
    summary="Current week episode schedule",
    description="Episode schedule for the current week, one entry per day.",
)
async def mdlSchedule(response: Response) -> Any:
    try:
        status, data = await FetchSchedule.scrape(
            "https://mydramalist.com/episode-calendar"
        )
    except Exception as exc:
        logger.error("FetchSchedule failed: %s", exc)
        response.status_code = 502
        return {"days": []}
    response.status_code = status
    return data
