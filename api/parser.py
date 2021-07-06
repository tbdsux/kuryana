from typing import Dict, List, Any, Tuple, Type, TypeVar, Union

from api import MYDRAMALIST_WEBSITE

# bypassing cloudflare anti-bot
import cloudscraper

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from datetime import datetime
from urllib.parse import urljoin


T = TypeVar("T", bound="Parser")


ScrapeTypes = {
    "search": urljoin(MYDRAMALIST_WEBSITE, "search?q="),
    "page": MYDRAMALIST_WEBSITE,
}


class Parser:
    """Main Parser"""

    headers: Dict[str, str] = {
        "Referer": MYDRAMALIST_WEBSITE,
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.123 Mobile Safari/537.36",
    }

    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        self.soup = soup
        self.query = query
        self.status_code = code
        self.url = ""

    @classmethod
    async def scrape(cls: Type[T], query: str, t: str) -> T:
        if t not in ScrapeTypes.keys():
            raise Exception("Invalid type")

        # parse url
        url = urljoin(ScrapeTypes[t], query)
        if t == "search":
            url = ScrapeTypes[t] + query

        ok = True
        code = 0
        soup = None

        try:
            # bypassing cloudflare anti-bot
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers=Parser.headers)

            # set the main soup var
            soup = BeautifulSoup(resp.text, "lxml")

            # set the status code
            code = resp.status_code
        except Exception:
            ok = False

        return cls(soup, query, code, ok)

    def check(self) -> Tuple[int, bool]:
        """Checks the status_code and returns it."""
        if self.status_code == 200:
            return 200, True

        return self.status_code, False

    # get page err, if possible
    def res_get_err(self) -> Dict[str, Any]:
        container = self.soup.find("div", class_="app-body")

        # if the page was not found,
        # or there was a problem with scraping,
        # try to get the error and return the err message
        err: Dict[str, Any] = {}

        try:
            err["status_code"] = self.status_code
            err["error"] = container.find("div", class_="box-body").find("h1").text
            err["info"] = container.find("div", class_="box-body").find("p").text
        except Exception:
            pass

        return err


class BaseSearch(Parser):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

        self.search_results: Dict[str, List] = {}  # search

    def search(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": self.search_results,
            "scrapte_date": datetime.utcnow(),
        }


class BaseFetch(Parser):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

        self.info: Dict[str, Any] = {
            "link": urljoin(MYDRAMALIST_WEBSITE, query)  # add `link` first data
        }  # fetch

        self._img_attrs = ["src", "data-cfsrc", "data-src"]

    def fetch(self) -> Dict[str, Any]:
        return {
            "slug_query": self.query,
            "data": self.info,
            "scrape_date": datetime.utcnow(),
        }

    def _get(self) -> None:
        """handler for parser, override in subclass"""

    def _get_poster(self, container: Union[Tag, NavigableString]) -> Union[str, Any]:
        poster = container.find("img")

        for i in self._img_attrs:
            if poster.has_attr(i):
                return poster[i]

        # blank if none
        return ""

    # get the drama details <= statistics section is added in here
    def _get_details(self, classname: str) -> None:
        details = self.soup.find("ul", class_=classname)  # "list m-a-0 hidden-md-up"

        try:
            self.info["details"] = {}
            all_details = details.find_all("li")

            for i in all_details:
                # get each li from <ul>
                _title = i.find("b").text.strip()

                # append each to sub object
                self.info["details"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = i.text.replace(
                    _title + " ", ""
                ).strip()  # remove leading and trailing white spaces

        except Exception:
            # do nothing, if there was a problem
            pass

    # rating handler, (since it could be N/A which is not convertable to float)
    def _handle_rating(
        self, component: Union[Tag, NavigableString]
    ) -> Union[str, float, Any]:
        try:
            return float(component.text)
        except Exception:
            pass

        return component.text
