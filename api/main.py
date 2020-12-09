from fastapi import FastAPI

from api.utils import search_func, fetch_func

app = FastAPI()


@app.get("/")
async def index():
    return "A Simple and Basic MDL Scraper API"


@app.get("/search/q/{query}")
async def search(query: str):
    search = await search_func(query=query)

    # ! FALSE OUTPUT
    if not search:
        return "There was a problem with the search function. Please try again later."

    return search


@app.get("/id/{drama_id}")
async def fetch(drama_id: str):
    fetch = await fetch_func(drama_id=drama_id)

    # ! FALSE OUTPUT
    if not fetch:
        return "There was a problem with the fetch function. Please try again later."

    return fetch