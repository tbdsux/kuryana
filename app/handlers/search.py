from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import NavigableString, ResultSet, Tag

from app import MYDRAMALIST_WEBSITE
from app.handlers.parser import BaseSearch


class Search(BaseSearch):
    """Search"""

    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)
        self.mdl_container_id = "mdl-"

    # get the main html container for the each search results
    def _get_container(self) -> ResultSet | None:
        if self.soup is None:
            return None

        results_container = self.soup.find("div", class_="col-lg-8 col-md-8")

        if results_container is None:
            return None

        return results_container.find_all("div", class_="box")

    # get the search result ranking
    def _res_get_ranking(self, result_container: BeautifulSoup) -> Any:
        try:
            ranking_container = result_container.find(
                "div", class_="ranking pull-right"
            )
            if ranking_container is None:
                return None

            ranking = ranking_container.find("span")
            if ranking is None:
                return None
        except AttributeError:
            return None  # return None if the result doesn't have it

        return ranking.text.strip()

    # get the year info of the result
    def _res_get_year_info(
        self, result_container: Tag
    ) -> tuple[str | None, int | None, str | bool]:
        # extract the type and year, e.g. "Korean Drama - 2016, 16 episodes"
        _typeyear_tag = result_container.find("span", class_="text-muted")
        if _typeyear_tag is None:
            return None, None, False
        _typeyear = _typeyear_tag.text
        _parts = _typeyear.split("-")
        _year_eps = _parts[1] if len(_parts) > 1 else ""

        year: int | None = None  # type error below

        # get the drama type [movie / series]
        try:
            t = _typeyear.split("-")[0].strip()
        except Exception:
            t = None

        # get the year
        try:
            year = int(_year_eps.split(",")[0].strip())
        except ValueError:
            year = None

        # get the # of eps if series
        series_ep: str | bool
        try:
            series_ep = _year_eps.split(",")[1].strip()
        except IndexError:
            series_ep = False

        return t, year, series_ep

    # extract the urls of the search result
    def _res_get_url(self, result_container: Tag | NavigableString) -> str:
        return urljoin(
            MYDRAMALIST_WEBSITE,
            str(
                result_container.find("h6", class_="text-primary title").find("a")[  # type: ignore
                    "href"
                ]
            ).replace("/", ""),
        )

    # search results handler
    def _get_search_results(self) -> None:
        results = self._get_container()  # get the search results
        if results is None:
            return

        _dramas = []
        _people = []

        for result in results:
            title_elem = result.find("h6", class_="text-primary title")
            if title_elem is None:
                continue  # skip if title is not found

            r = {}
            title = title_elem.text.strip()

            # extract the URL slug
            _title_a = title_elem.find("a")
            url_slug = _title_a.get("href") if _title_a is not None else None
            if url_slug is not None:
                r["slug"] = url_slug.replace("/", "", 1)
            else:
                continue  # skip this result if URL slug is not found

            # get the thumbnail
            _img = result.find("img", class_="img-responsive")
            _thumb = str(_img.get("data-src", "") if _img is not None else "").split(
                "/1280/"
            )
            if len(_thumb) > 1:
                r["thumb"] = _thumb[1]
            else:
                r["thumb"] = _thumb[0]

            if result.has_attr("id"):
                r["mdl_id"] = result["id"]

                # extract drama title
                r["title"] = title.strip()

                # drama ranking
                r["ranking"] = self._res_get_ranking(result)

                # specific drama info
                r["type"], r["year"], r["series"] = self._res_get_year_info(result)

                # extract drama rating (could be empty, "N/A" or a number)
                _score = result.find("span", class_="score")
                try:
                    r["rating"] = float(_score.text)
                except (AttributeError, ValueError):
                    pass  # no score, empty or "N/A": leave it out, as before

                _dramas.append(r)
                continue

            # it can only be a person otherwise,
            r["name"] = title.strip()
            _nationality = result.find("div", class_="text-muted")
            r["nationality"] = (
                _nationality.text.strip() if _nationality is not None else ""
            )
            _people.append(r)

        self.search_results["dramas"] = _dramas
        self.search_results["people"] = _people
