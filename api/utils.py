from __future__ import annotations
from typing import Dict, Any, Tuple

from api.search import Search
from api.fetch import FetchDrama, FetchPerson


def error(code: int, description: str) -> Dict[str, Any]:
    return {
        "error": True,
        "code": code,
        "description": description,
    }


# search function
async def search_func(query: str) -> Tuple[int, Dict[str, Any]]:
    f = await Search.scrape(query=query, t="search")
    code, ok = f.check()
    if not ok:
        return code, error(code, "An unexpected error occurred.")

    return code, f.search()


fs = {"drama": FetchDrama, "person": FetchPerson}

# fetch function
async def fetch_func(query: str, t: str) -> Tuple[int, Dict[str, Any]]:
    if not t in fs.keys():
        raise Exception("Invalid Error")

    f = await fs[t].scrape(query=query, t="page")
    code, ok = f.check()
    if not ok:
        return code, error(code, "An unexpected error occurred.")

    return code, f.fetch()
