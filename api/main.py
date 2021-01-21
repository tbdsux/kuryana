from fastapi import FastAPI, Response, status
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from api.utils import search_func, fetch_func

app = FastAPI()


@app.get("/")
async def index():
    return "A Simple and Basic MDL Scraper API"


@app.get("/search/q/{query}")
async def search(query: str, response: Response):
    search = await search_func(query=query)

    # there was a problem with the scraper
    if not search:
        # return 500 [Internal Server Error]
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return "There was a problem with the search function. Please try again later."

    return search


@app.get("/id/{drama_id}")
async def fetch(drama_id: str, response: Response):
    ok, fetch = await fetch_func(drama_id=drama_id)

    # both are false, meaning
    # there was a problem with the scraper
    if not ok and not fetch:
        # return 500 [Internal Server Error]
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return "There was a problem with the fetch function. Please try again later."

    # ok is false but the err has value
    if not ok and fetch:
        # return 404 [Not Found]
        response.status_code = status.HTTP_404_NOT_FOUND
        return fetch

    return fetch