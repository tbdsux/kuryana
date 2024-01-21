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
        # Example: Goblin (2016)
        # Title = Goblin
        # Complete Title = Goblin (2016)
        film_title = container.find("h1", class_="film-title")
        self.info["title"] = film_title.find("a").get_text().strip()
        self.info["complete_title"] = film_title.get_text().strip()

        # RATING (could be either N/A or with number)
        self.info["rating"] = self._handle_rating(
            container.find("div", class_="col-film-rating").find("div")
        )

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # SYNOPSIS
        synopsis = container.find("div", class_="show-synopsis").find("p")
        self.info["synopsis"] = (
            synopsis.get_text().replace("Edit Translation", "").strip()
            if synopsis
            else ""
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
                ] = [
                    i.strip()
                    for i in i.text.replace(_title + " ", "").strip().split(", ")
                ]

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
        _work_headers = [i.text.strip() for i in _works_container.find_all("h5")]
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
                    "rating": self._handle_rating(
                        i.find("td", class_="text-center").find(class_="text-sm")
                    ),
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
                            "type": _raw_role.find("div", class_="roleid").text.strip(),
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
                    "profile_image": self._get_poster(i).replace(
                        "s.jpg", "m.jpg"
                    ),  # replaces the small images to a link with a bigger one
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
            __temp_review: Dict[str, Any] = {}

            try:
                # reviewer / person
                __temp_review["reviewer"] = {
                    "name": i.find("a").text.strip(),
                    "user_link": urljoin(MYDRAMALIST_WEBSITE, i.find("a")["href"]),
                    "user_image": self._get_poster(i).replace(
                        "1t", "1c"
                    ),  # replace 1t to 1c so that it will return a bigger image than the smaller one
                    "info": i.find("div", class_="user-stats").text.strip(),
                }

                __temp_review_ratings = i.find(
                    "div", class_="box pull-right text-sm m-a-sm"
                )
                __temp_review_ratings_overall = __temp_review_ratings.find(
                    "div", class_="rating-overall"
                )

                # start parsing the review section
                __temp_review_contents = []

                __temp_review_container = i.find(
                    "div", class_=re.compile("review-body")
                )

                __temp_review_spoiler = __temp_review_container.find(
                    "div", "review-spoiler"
                )
                if __temp_review_spoiler is not None:
                    __temp_review_contents.append(__temp_review_spoiler.text.strip())

                __temp_review_strong = __temp_review_container.find("strong")
                if __temp_review_strong is not None:
                    __temp_review_contents.append(__temp_review_strong.text.strip())

                __temp_review_read_more = __temp_review_container.find(
                    "p", class_="read-more"
                ).text.strip()
                __temp_review_vote = __temp_review_container.find(
                    "div", class_="review-helpful"
                ).text.strip()

                for i in __temp_review_container.find_all("br"):
                    i.replace_with("\n")

                __temp_review_content = (
                    __temp_review_container.text.replace(
                        __temp_review_ratings.text.strip(), ""
                    )
                    .replace(__temp_review_read_more, "")
                    .replace(__temp_review_vote, "")
                )

                if __temp_review_spoiler is not None:
                    __temp_review_content = __temp_review_content.replace(
                        __temp_review_spoiler.text.strip(), ""
                    )
                if __temp_review_strong is not None:
                    __temp_review_content = __temp_review_content.replace(
                        __temp_review_strong.text.strip(), ""
                    )

                __temp_review_contents.append(__temp_review_content.strip())
                __temp_review["review"] = __temp_review_contents
                # end parsing the review section

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


class FetchDramaList(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    def _get_main_container(self) -> None:
        container = self.soup.find_all("div", class_="mdl-style-list")
        titles = [self._parse_title(item) for item in container]
        dramas = [self._parse_drama(item) for item in container]
        stats = [self._parse_total_stats(item) for item in container]

        items = dict()
        for title, drama, stat in zip(titles, dramas, stats):
            items[title] = {"items": drama, "stats": stat}

        self.info["list"] = items

    def _parse_title(self, item: BeautifulSoup) -> str:
        return item.find("h3", class_="mdl-style-list-label").get_text(strip=True)

    def _parse_total_stats(self, item: BeautifulSoup) -> Dict[str, str]:
        drama_stats = item.find("label", class_="mdl-style-dramas")
        tvshows_stats = item.find("label", class_="mdl-style-tvshows")
        episodes_stats = item.find("label", class_="mdl-style-episodes")
        movies_stats = item.find("label", class_="mdl-style-movies")
        days_stats = item.find("label", class_="mdl-style-days")
        return {
            label.find("span", class_="name")
            .get_text(strip=True): label.find("span", class_="cnt")
            .get_text(strip=True)
            for label in [
                drama_stats,
                tvshows_stats,
                episodes_stats,
                movies_stats,
                days_stats,
            ]
        }

    def _parse_drama(self, item: BeautifulSoup) -> Dict[str, str]:
        item_names = item.find_all("a", class_="title")
        item_scores = item.find_all("span", class_="score")
        item_episode_seens = item.find_all("span", class_="episode-seen")
        item_episode_totals = item.find_all("span", class_="episode-total")

        parsed_data = []
        for name, score, seen, total in zip(
            item_names,
            item_scores,
            item_episode_seens,
            item_episode_totals,
        ):
            parsed_item = {
                "name": name.get_text(strip=True),
                "id": name.get("href", "").split("/")[-1],
                "score": score.get_text(strip=True),
                "episode_seen": seen.get_text(strip=True),
                "episode_total": total.get_text(strip=True),
            }
            parsed_data.append(parsed_item)

        return parsed_data

    def _get(self) -> None:
        self._get_main_container()


class FetchList(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    def _get_main_container(self) -> None:
        container = self.soup.find("div", class_="app-body")

        # get list title
        header = container.find("div", class_="box-header")
        self.info["title"] = header.find("h1").get_text().strip()

        description = header.find("div", class_="description")
        self.info["description"] = (
            description.get_text().strip() if description is not None else ""
        )

        # get list
        container_list = container.find("div", class_="collection-list")
        all_items = container_list.find_all("li")
        list_items = []
        for i in all_items:
            i_url = i.find("a").get("href")
            if "/people/" in i_url:
                list_items.append(self._parse_person(i))
                continue

            list_items.append(self._parse_show(i))

        self.info["list"] = list_items

    def _parse_person(self, item: BeautifulSoup) -> Dict[str, Any]:
        # parse person image
        person_img_container = str(
            item.find("img", class_="img-responsive")["data-src"]
        ).split("/1280/")
        person_img = ""
        if len(person_img_container) > 1:
            person_img = person_img_container[1]
        else:
            person_img = person_img_container[0]

        person_img = person_img.replace(
            "s.jpg", "m.jpg"
        )  # replace image url to give the bigger size

        item_header = item.find("div", class_="content")
        person_name = item_header.find("a").get_text().strip()
        person_slug = item_header.find("a").get("href")
        person_url = urljoin(MYDRAMALIST_WEBSITE, person_slug)

        person_nationality = item.find(class_="text-muted").get_text().strip()
        person_details_xx = item.find_all("p")
        person_details = ""
        if len(person_details_xx) > 1:
            person_details = person_details_xx[-1].get_text().strip()

        return {
            "name": person_name,
            "type": "person",  # todo: change this
            "image": person_img,
            "slug": person_slug,
            "url": person_url,
            "nationality": person_nationality,
            "details": person_details,
        }

    def _parse_show(self, item: BeautifulSoup) -> Dict[str, Any]:
        # parse list image
        list_img_container = str(
            item.find("img", class_="img-responsive")["data-src"]
        ).split("/1280/")
        list_img = ""
        if len(list_img_container) > 1:
            list_img = list_img_container[1]
        else:
            list_img = list_img_container[0]

        list_img = list_img.replace(
            "t.jpg", "c.jpg"
        )  # replace image url to give the bigger size

        list_header = item.find("h2")
        list_title = list_header.find("a").get_text().strip()
        list_title_rank = (
            list_header.get_text().replace(list_title, "").strip().strip(".")
        )
        list_url = urljoin(MYDRAMALIST_WEBSITE, list_header.find("a").get("href"))
        list_slug = list_header.find("a").get("href")

        # parse example: `Korean Drama - 2020, 16 episodes`
        list_details_container = item.find(class_="text-muted")  # could be `p` or `div`
        list_details_xx = list_details_container.get_text().split(",")
        list_details_type = list_details_xx[0].split("-")[0].strip()
        list_details_year = list_details_xx[0].split("-")[1].strip()

        list_details_episodes = None
        if len(list_details_xx) > 1:
            list_details_episodes = int(
                list_details_xx[1].replace("episodes", "").strip()
            )

        # try to get description, it is missing on some lists
        list_short_summary = ""
        list_short_summary_container = item.find("div", class_="col-xs-12 m-t-sm")
        if list_short_summary_container is not None:
            list_short_summary = (
                list_short_summary_container.get_text()
                .replace("...more", "...")
                .strip()
            )

        return {
            "title": list_title,
            "image": list_img,
            "rank": list_title_rank,
            "url": list_url,
            "slug": list_slug,
            "type": list_details_type,
            "year": list_details_year,
            "episodes": list_details_episodes,
            "short_summary": list_short_summary,
        }

    def _get(self) -> None:
        self._get_main_container()
