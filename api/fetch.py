from typing import Dict, Any, List

from api import MYDRAMALIST_WEBSITE
from api.parser import BaseFetch

from bs4 import BeautifulSoup
from urllib.parse import urljoin


class FetchDrama(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

        self._get_drama()

    # get the main html container for the each search results
    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        self.info["title"] = container.find("h1", class_="film-title").find("a").text

        # RATING
        self.info["rating"] = float(
            (container.find("div", class_="col-film-rating").find("div").text)
        )

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # SYNOPSIS
        self.info["synopsis"] = (
            container.find("div", class_="show-synopsis")
            .find("span")
            .text.replace("\n", " ")
        )

        # CASTS
        __casts = container.find_all("li", class_="list-item col-sm-4")
        casts = []
        for i in __casts:
            __temp_cast = i.find("a", class_="text-primary text-ellipsis")
            casts.append(
                {
                    "name": __temp_cast.find("b").text.strip(),
                    "slug": __temp_cast["href"].strip(),
                }
            )
        self.info["casts"] = casts

    # get other info
    def _get_other_info(self) -> None:
        others = self.soup.find("div", class_="show-detailsxss").find(
            "ul", class_="list m-a-0"
        )

        try:
            self.info["others"] = {}
            all_others = others.find_all("li")
            for i in all_others:
                # get each li from <ul>
                _title = i.find("b").text.strip()
                self.info["others"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = i.text.replace(
                    _title + " ", ""
                ).strip()  # remove leading and trailing white spaces

        except Exception:
            # there was a problem while trying to parse
            # the :> other info section
            pass

    # drama info details handler
    def _get_drama(self) -> None:
        self._get_main_container()
        self._get_details(classname="list m-a-0 hidden-md-up")
        self._get_other_info()


class FetchPerson(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

        self._get_person()

    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # NAME
        self.info["name"] = container.find("h1", class_="film-title").text

        # ABOUT?
        self.info["about"] = container.find(
            "div", class_="col-sm-8 col-lg-12 col-md-12"
        ).text.strip()

        # IMAGE
        self.info["profile"] = self._get_poster(container)

        # WORKS
        self.info["works"] = {}

        # container
        _works_container = container.find("div", class_="col-lg-8 col-md-8").find_all(
            "div", class_="box-body"
        )[1]

        # get all headers
        _work_headers = [
            i.text.strip().lower() for i in _works_container.find_all("h5")
        ]
        _work_tables = _works_container.find_all("table")

        for j, k in zip(_work_headers, _work_tables):
            bare_works: List[Dict[str, Any]] = []

            for i in k.find("tbody").find_all("tr"):
                _raw_year = i.find("td", class_="year").text
                _raw_title = i.find("td", class_="title").find("a")
                _raw_role = i.find("td", class_="role")
                try:
                    _raw_role_name = _raw_role.find("div", class_="name")
                except Exception:
                    _raw_role_name = None

                r = {
                    "_slug": i["class"][0],
                    "year": _raw_year if _raw_year == "TBA" else int(_raw_year),
                    "title": {
                        "link": urljoin(MYDRAMALIST_WEBSITE, _raw_title["href"]),
                        "name": _raw_title.text,
                    },
                    "role": {
                        "name": _raw_role_name.text.strip(),
                        "id": _raw_role.find("div", class_="roleid").text.strip(),
                    },
                    "rating": float(
                        i.find("td", class_="text-center")
                        .find("div", class_="text-sm")
                        .text
                    ),
                }

                try:
                    episodes = i.find("td", class_="episodes").text
                    r["episodes"] = int(episodes)
                except Exception:
                    pass

                bare_works.append(r)

            self.info["works"][j] = bare_works

    def _get_person(self) -> None:
        self._get_main_container()
        self._get_details(classname="list m-b-0")
