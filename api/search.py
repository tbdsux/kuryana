from typing import Any, Tuple, Union, Optional

from api import MYDRAMALIST_WEBSITE
from api.parser import BaseSearch

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString, ResultSet
from urllib.parse import urljoin


class Search(BaseSearch):
    """Search"""

    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)
        self.url = "search?q=" + self.query.replace(" ", "+")
        self.mdl_container_id = "mdl-"

    # get the main html container for the each search results
    def _get_container(self) -> ResultSet:
        return self.soup.find("div", class_="col-lg-8 col-md-8").find_all(
            "div", class_="box"
        )

    # get the search result ranking
    def _res_get_ranking(self, result_container: BeautifulSoup) -> Any:
        try:
            ranking = result_container.find("div", class_="ranking pull-right").find(
                "span"
            )
        except AttributeError:
            return None  # return None if the result doesn't have it

        return ranking.text

    # get the year info of the result
    def _res_get_year_info(
        self, result_container: Union[NavigableString, Tag]
    ) -> Tuple[Union[str, None], Union[int, None], Union[str, bool]]:
        # extract the type and year
        _typeyear = result_container.find("span", class_="text-muted").text
        _year_eps = _typeyear.split("-")[1]

        year: Optional[int] = None  # type error below

        # get the drama type [movie / series]
        try:
            t = _typeyear.split("-")[0].strip()
        except Exception:
            t = None

        # get the year
        try:
            year = int(_year_eps.split(",")[0].strip())
        except Exception:
            year = None

        # get the # of eps if series
        try:
            series_ep = _year_eps.split(",")[1].strip()
        except Exception:
            series_ep = False

        return t, year, series_ep

    # extract the urls of the search result
    def _res_get_url(self, result_container: Union[Tag, NavigableString]) -> str:
        return urljoin(
            MYDRAMALIST_WEBSITE,
            result_container.find("h6", class_="text-primary title")
            .find("a")["href"]
            .replace("/", ""),
        )

    # search results handler
    def _get_search_results(self) -> None:
        results = self._get_container()  # get the search results

        _dramas = []
        _people = []

        for result in results:
            r = {}

            title = result.find("h6", class_="text-primary title").find("a")

            r["slug"] = title["href"].replace("/", "", 1)
            # get the thumbnail
            r["thumb"] = result.find("img", class_="img-responsive")["data-src"]

            if result.has_attr("id"):
                r["mdl_id"] = result["id"]

                # extract drama title
                r["title"] = title.text.strip()

                # drama ranking
                r["ranking"] = self._res_get_ranking(result)

                # specific drama info
                r["type"], r["year"], r["series"] = self._res_get_year_info(result)

                _dramas.append(r)
                continue

            # it can only be a person otherwise,
            r["name"] = title.text.strip()
            r["nationality"] = result.find("div", class_="text-muted").text.strip()
            _people.append(r)

        self.search_results["dramas"] = _dramas
        self.search_results["people"] = _people
