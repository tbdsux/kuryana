from fastapi import FastAPI, Response, status

from api.utils import search_func, fetch_func

# bypassing cloudflare anti-bot
import cloudscraper

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


# get seasonal drama list -- official api available, use it with cloudflare bypass
@app.get("/seasonal/{year}/{quarter}")
async def mdlSeasonal(year: int, quarter: int):
    scraper = cloudscraper.create_scraper()
    return scraper.post(
        "https://mydramalist.com/v1/quarter_calendar",
        data={"quarter": quarter, "year": year},
    ).json()
    # year -> ex. ... / 2019 / 2020 / 2021 / ...
    # quarter -> every 3 months (Jan-Mar=1, Apr-Jun=2, Jul-Sep=3, Oct-Dec=4)
    # --- seasonal information --- winter --- spring --- summer --- fall ---
