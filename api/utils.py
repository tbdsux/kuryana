from typing import Dict, Any, Tuple

from api.search import Search
from api.fetch import FetchDrama, FetchPerson, FetchCast, FetchReviews


def error(code: int, description: str) -> Dict[str, Any]:
    return {
        "error": True,
        "code": code,
        "description": "404 Not Found"
        if code == 404
        else description,  # prioritize error 404
    }


# search function
async def search_func(query: str) -> Tuple[int, Dict[str, Any]]:
    f = await Search.scrape(query=query, t="search")
    if not f.ok:
        return f.status_code, error(f.status_code, "An unexpected error occurred.")
    else:
        f._get_search_results()

    return f.status_code, f.search()


fs = {
    "drama": FetchDrama,
    "person": FetchPerson,
    "cast": FetchCast,
    "reviews": FetchReviews,
}


# fetch function
async def fetch_func(query: str, t: str) -> Tuple[int, Dict[str, Any]]:
    if t not in fs.keys():
        raise Exception("Invalid Error")

    f = await fs[t].scrape(query=query, t="page")
    if not f.ok:
        return f.status_code, error(f.status_code, "An unexpected error occurred.")
    else:
        f._get()

    return f.status_code, f.fetch()
