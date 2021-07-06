from typing import Dict, Any, List

from api import MYDRAMALIST_WEBSITE
from api.parser import BaseFetch

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re


class FetchDrama(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    # get the main html container for the each search results
    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        self.info["title"] = container.find("h1", class_="film-title").find("a").text

        # RATING (could be either N/A or with number)
        self.info["rating"] = self._handle_rating(container.find("div", class_="col-film-rating").find("div"))

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
            __temp_cast_slug = __temp_cast["href"].strip()
            casts.append(
                {
                    "name": __temp_cast.find("b").text.strip(),
                    "profile_image": self._get_poster(i),
                    "slug": __temp_cast_slug,
                    "link": urljoin(MYDRAMALIST_WEBSITE, __temp_cast_slug),
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
    def _get(self) -> None:
        self._get_main_container()
        self._get_details(classname="list m-a-0 hidden-md-up")
        self._get_other_info()


class FetchPerson(BaseFetch):
    non_actors = ["screenwriter", "director", "screenwriter & director"]

    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # NAME
        self.info["name"] = container.find("h1", class_="film-title").text

        # ABOUT?
        __temp_about = container.find("div", class_="col-lg-8 col-md-8").find(
            "div", class_="col-sm-8 col-lg-12 col-md-12"
        )
        self.info["about"] = __temp_about.text.replace(
            __temp_about.find("div", class_="hidden-md-up").text.strip(), ""
        ).strip()

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
            # theaders = ['episodes' if i.text.strip() == '#' else i.text.strip() for i in k.find("thead").find_all("th")]
            bare_works: List[Dict[str, Any]] = []

            for i in k.find("tbody").find_all("tr"):
                _raw_year = i.find("td", class_="year").text
                _raw_title = i.find("td", class_="title").find("a")

                r = {
                    "_slug": i["class"][0],
                    "year": _raw_year if _raw_year == "TBA" else int(_raw_year),
                    "title": {
                        "link": urljoin(MYDRAMALIST_WEBSITE, _raw_title["href"]),
                        "name": _raw_title.text,
                    },
                    "rating": self._handle_rating(i.find("td", class_="text-center").find(class_="text-sm"))
                }

                _raw_role = i.find("td", class_="role")

                # applicable only on dramas / tv-shows (this is different for non-actors)
                try:
                    _raw_role_name = _raw_role.find("div", class_="name").text.strip()
                except Exception:
                    _raw_role_name = None

                # use `type` for non-dramas, etc while `role` otherwise
                try:
                    if j in FetchPerson.non_actors:
                        r["type"] = _raw_role.find(class_="roleid").text.strip()
                    else:
                        r["role"] = {
                            "name": _raw_role_name,
                            "id": _raw_role.find("div", class_="roleid").text.strip(),
                        }
                except Exception:
                    pass

                # not applicable for movies
                try:
                    episodes = i.find("td", class_="episodes").text
                    r["episodes"] = int(episodes)
                except Exception:
                    pass

                bare_works.append(r)

            self.info["works"][j] = bare_works

    def _get(self) -> None:
        self._get_main_container()
        self._get_details(classname="list m-b-0")


class FetchCast(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        self.info["title"] = container.find("h1", class_="film-title").find("a").text

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # CASTS?
        self.info["casts"] = {}
        __casts_container = container.find("div", class_="box cast-credits").find(
            "div", class_="box-body"
        )

        __temp_cast_headers = __casts_container.find_all("h3")
        __temp_cast_lists = __casts_container.find_all("ul")

        for j, k in zip(__temp_cast_headers, __temp_cast_lists):
            casts = []
            for i in k.find_all("li"):
                __temp_cast = i.find("a", class_="text-primary")
                __temp_cast_slug = __temp_cast["href"].strip()
                __temp_cast_data = {
                    "name": __temp_cast.find("b").text.strip(),
                    "profile_image": self._get_poster(i),
                    "slug": __temp_cast_slug,
                    "link": urljoin(MYDRAMALIST_WEBSITE, __temp_cast_slug),
                }

                try:
                    __temp_cast_data["role"] = {
                        "name": i.find("small").text.strip(),
                        "type": i.find("small", class_="text-muted").text.strip(),
                    }
                except Exception:
                    pass

                casts.append(__temp_cast_data)

            self.info["casts"][j.text.strip()] = casts

    def _get(self) -> None:
        self._get_main_container()


class FetchReviews(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        self.info["title"] = container.find("h1", class_="film-title").find("a").text

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # REVIEWS?
        self.info["reviews"] = []
        __temp_reviews = container.find_all("div", class_="review")

        for i in __temp_reviews:
            __temp_review = {}

            try:
                # reviewer / person
                __temp_review["reviewer"] = {
                    "name": i.find("a").text.strip(),
                    "user_link": urljoin(MYDRAMALIST_WEBSITE, i.find("a")["href"]),
                    "user_image": self._get_poster(i),
                    "info": i.find("div", class_="user-stats").text.strip(),
                }

                __temp_review_ratings = i.find(
                    "div", class_="box pull-right text-sm m-a-sm"
                )
                __temp_review_ratings_overall = __temp_review_ratings.find(
                    "div", class_="rating-overall"
                )

                __temp_review["review"] = (
                    i.find("div", class_=re.compile("review-body"))
                    .text.replace(__temp_review_ratings.text.strip(), "")
                    .strip()
                )

                __temp_review["ratings"] = {
                    "overall": float(
                        __temp_review_ratings_overall.find("span").text.strip()
                    )
                }
                __temp_review_ratings_others = __temp_review_ratings.find(
                    "div", class_="review-rating"
                ).find_all("div")

                # other review ratings, it might be different in each box?
                for k in __temp_review_ratings_others:
                    __temp_review["ratings"][
                        k.text.replace(k.find("span").text.strip(), "").strip()
                    ] = float(k.find("span").text.strip())

            except Exception as e:
                print(e)
                # if failed to parse, do nothing
                pass

            # append to list
            self.info["reviews"].append(__temp_review)

    def _get(self) -> None:
        self._get_main_container()
