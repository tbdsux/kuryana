import json
import re
from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from app import MYDRAMALIST_WEBSITE
from app.handlers.parser import BaseFetch


class FetchDrama(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)

    # get the main html container for the each search results
    def _get_main_container(self) -> None:
        if self.soup is None:
            return

        container = self.soup.find("div", class_="app-body")
        if container is None:
            return

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        # Example: Goblin (2016)
        # Title = Goblin
        # Complete Title = Goblin (2016)
        film_title = container.find("h1", class_="film-title")
        if film_title is None:
            return
        self.info["title"] = film_title.get_text().strip()
        self.info["complete_title"] = film_title.get_text().strip()

        film_subtitle = container.find("div", class_="film-subtitle")
        if film_subtitle is None:
            return

        sub_title = film_subtitle.get_text().strip()

        if sub_title:
            self.info["sub_title"] = sub_title

            # Split the string by the separator '‧'
            parts = sub_title.split("‧")
            print(parts)

            # The year is the last part, remove any leading/trailing whitespace
            year_str = parts[-1].strip()
            print(year_str)

            # Year could be a range, so we keep it as a string
            self.info["year"] = year_str.strip()

        # RATING (could be either N/A or with number)
        _rating_container = container.find("div", class_="col-film-rating")
        self.info["rating"] = self._handle_rating(
            _rating_container.find("div") if _rating_container is not None else None
        )

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # SYNOPSIS
        _synopsis_container = container.find("div", class_="show-synopsis")
        synopsis = _synopsis_container.find("p") if _synopsis_container is not None else None
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
            if __temp_cast is None:
                continue
            __temp_cast_slug = str(__temp_cast.get("href", "")).strip()
            _b = __temp_cast.find("b")
            casts.append(
                {
                    "name": _b.text.strip() if _b is not None else "",
                    "profile_image": self._get_poster(i),
                    "slug": __temp_cast_slug,
                    "link": urljoin(MYDRAMALIST_WEBSITE, __temp_cast_slug),
                }
            )
        self.info["casts"] = casts

        # Extract nextEpisodeAiring
        scripts = self.soup.find_all("script", type="text/javascript")
        for script in scripts:
            if script.string and "var nextEpisodeAiring =" in script.string:
                match = re.search(r"var nextEpisodeAiring = ({.*});", script.string)
                if match:
                    next_airing = json.loads(match.group(1))
                    self.info["next_episode_airing"] = next_airing
                    current_episode = float(next_airing["episode_number"]) - 1
                    self.info["current_episode"] = (
                        "0"
                        if current_episode < 0
                        else str(float(next_airing["episode_number"]) - 1).replace(
                            ".0", ""
                        )
                    )
                break

    # get other info
    def _get_other_info(self) -> None:
        if self.soup is None:
            return

        others_container = self.soup.find("div", class_="show-detailsxss")
        if others_container is None:
            return
        others = others_container.find("ul", class_="list m-a-0")
        if others is None:
            return

        try:
            self.info["others"] = {}
            all_others = others.find_all("li")
            for i in all_others:
                # get each li from <ul>
                _b = i.find("b")
                if _b is None:
                    continue
                _title = _b.text.strip()
                _title_key = _title.replace(":", "").replace(" ", "_").lower()

                if _title_key == "related_content":
                    _related_content_titles = i.find_all("div", class_="title")
                    for rl in _related_content_titles:
                        rl_href = rl.find("a")
                        if rl_href is None:
                            # If no link, just get the text and continue
                            rl_title = rl.text.strip()
                            rl_extra_text = ""
                            rl_link = ""
                            rl_slug = ""
                        else:
                            rl_title = rl_href.text.strip()
                            rl_extra_text = rl.text.replace(rl_title, "").strip()
                            rl_slug = str(rl_href.get("href", "")).strip()
                            rl_link = urljoin(MYDRAMALIST_WEBSITE, rl_slug)

                        if "related_content" not in self.info["others"]:
                            self.info["others"]["related_content"] = []
                        self.info["others"]["related_content"].append(
                            {
                                "title": rl_title,
                                "link": rl_link,
                                "description": rl_extra_text,
                                "slug": rl_slug.replace("/", "")
                            }
                        )
                    continue
                else:
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
        if self.soup is None:
            return

        container = self.soup.find("div", class_="app-body")
        if container is None:
            return

        # append scraped data
        # these are the most important drama infos / details

        # NAME
        _film_title = container.find("h1", class_="film-title")
        if _film_title is None:
            return
        self.info["name"] = _film_title.get_text().strip()

        # ABOUT?
        _col_container = container.find("div", class_="col-lg-8 col-md-8")
        if _col_container is None:
            return
        __temp_about = _col_container.find("div", class_="col-sm-8 col-lg-12 col-md-12")
        if __temp_about is None:
            return
        _hidden = __temp_about.find("div", class_="hidden-md-up")
        self.info["about"] = (
            __temp_about.text.replace(
                _hidden.text.strip() if _hidden is not None else "", ""
            )
            .replace("Remove ads\n\n", "")
            .strip()
        )

        # IMAGE
        self.info["profile"] = self._get_poster(container)

        # WORKS
        self.info["works"] = {}

        # container
        _works_container = _col_container.find_all(
            "div", class_="box-body"
        )[1]

        # get all headers
        _work_headers = [i.text.strip() for i in _works_container.find_all("h5")]
        _work_tables = _works_container.find_all("table")

        for j, k in zip(_work_headers, _work_tables, strict=False):
            # theaders = ['episodes' if i.text.strip() == '#' else i.text.strip() for i in k.find("thead").find_all("th")]
            bare_works: List[Dict[str, Any]] = []

            _tbody = k.find("tbody")
            if _tbody is None:
                continue
            for i in _tbody.find_all("tr"):
                _td_year = i.find("td", class_="year")
                if _td_year is None:
                    continue
                _raw_year = _td_year.text
                _td_title = i.find("td", class_="title")
                if _td_title is None:
                    continue
                _raw_title = _td_title.find("a")
                if _raw_title is None:
                    continue

                _td_center = i.find("td", class_="text-center")
                r = {
                    "_slug": i["class"][0],
                    "year": _raw_year if _raw_year == "TBA" else int(_raw_year),
                    "title": {
                        "link": urljoin(MYDRAMALIST_WEBSITE, str(_raw_title.get("href", ""))),
                        "name": _raw_title.text,
                    },
                    "rating": self._handle_rating(
                        _td_center.find(class_="text-sm") if _td_center is not None else None
                    ),
                }

                _raw_role = i.find("td", class_="role")

                # applicable only on dramas / tv-shows (this is different for non-actors)
                try:
                    _role_name_tag = _raw_role.find("div", class_="name") if _raw_role is not None else None
                    _raw_role_name = _role_name_tag.text.strip() if _role_name_tag is not None else None
                except Exception:
                    _raw_role_name = None

                # use `type` for non-dramas, etc while `role` otherwise
                try:
                    if _raw_role is not None:
                        if j in FetchPerson.non_actors:
                            _roleid_tag = _raw_role.find(class_="roleid")
                            if _roleid_tag is not None:
                                r["type"] = _roleid_tag.text.strip()
                        else:
                            _roleid_tag = _raw_role.find("div", class_="roleid")
                            r["role"] = {
                                "name": _raw_role_name,
                                "type": _roleid_tag.text.strip() if _roleid_tag is not None else "",
                            }
                except Exception:
                    pass

                # not applicable for movies
                try:
                    _episodes_td = i.find("td", class_="episodes")
                    if _episodes_td is not None:
                        r["episodes"] = int(_episodes_td.text)
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
        if self.soup is None:
            return

        container = self.soup.find("div", class_="app-body")
        if container is None:
            return

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        _film_title = container.find("h1", class_="film-title")
        if _film_title is None:
            return
        self.info["title"] = _film_title.get_text().strip()

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # CASTS?
        self.info["casts"] = {}
        _cast_credits = container.find("div", class_="box cast-credits")
        if _cast_credits is None:
            return
        __casts_container = _cast_credits.find("div", class_="box-body")
        if __casts_container is None:
            return

        __temp_cast_headers = __casts_container.find_all("h3")
        __temp_cast_lists = __casts_container.find_all("ul")

        for j, k in zip(__temp_cast_headers, __temp_cast_lists, strict=False):
            casts = []
            for i in k.find_all("li"):
                __temp_cast = i.find("a", class_="text-primary")
                if __temp_cast is None:
                    continue
                __temp_cast_slug = str(__temp_cast.get("href", "")).strip()
                _b = __temp_cast.find("b")
                __temp_cast_data = {
                    "name": _b.text.strip() if _b is not None else "",
                    "profile_image": self._get_poster(i).replace(
                        "s.jpg", "m.jpg"
                    ),  # replaces the small images to a link with a bigger one
                    "slug": __temp_cast_slug,
                    "link": urljoin(MYDRAMALIST_WEBSITE, __temp_cast_slug),
                }

                try:
                    _small = i.find("small")
                    _small_muted = i.find("small", class_="text-muted")
                    if _small is not None and _small_muted is not None:
                        __temp_cast_data["role"] = {
                            "name": _small.text.strip(),
                            "type": _small_muted.text.strip(),
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

    def _get_main_container(self) -> None:  # noqa: C901
        if self.soup is None:
            return

        container = self.soup.find("div", class_="app-body")
        if container is None:
            return

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        _film_title = container.find("h1", class_="film-title")
        if _film_title is None:
            return
        self.info["title"] = _film_title.get_text().strip()

        # POSTER
        self.info["poster"] = self._get_poster(container)

        # REVIEWS?
        self.info["reviews"] = []
        __temp_reviews = container.find_all("div", class_="review")

        for i in __temp_reviews:
            __temp_review: Dict[str, Any] = {}

            try:
                # reviewer / person
                _reviewer_a = i.find("a")
                if _reviewer_a is None:
                    raise ValueError("no reviewer anchor")
                _user_stats = i.find("div", class_="user-stats")
                __temp_review["reviewer"] = {
                    "name": _reviewer_a.text.strip(),
                    "user_link": urljoin(MYDRAMALIST_WEBSITE, str(_reviewer_a.get("href", ""))),
                    "user_image": self._get_poster(i).replace(
                        "1t", "1c"
                    ),  # replace 1t to 1c so that it will return a bigger image than the smaller one
                    "info": _user_stats.text.strip() if _user_stats is not None else "",
                }

                __temp_review_ratings = i.find(
                    "div", class_="box pull-right text-sm m-a-sm"
                )
                if __temp_review_ratings is None:
                    raise ValueError("no review ratings")
                __temp_review_ratings_overall = __temp_review_ratings.find(
                    "div", class_="rating-overall"
                )
                if __temp_review_ratings_overall is None:
                    raise ValueError("no review ratings overall")

                # start parsing the review section
                __temp_review_contents = []

                __temp_review_container = i.find(
                    "div", class_=re.compile("review-body")
                )
                if __temp_review_container is None:
                    raise ValueError("no review body")

                __temp_review_spoiler = __temp_review_container.find(
                    "div", class_="review-spoiler"
                )
                if __temp_review_spoiler is not None:
                    __temp_review_contents.append(__temp_review_spoiler.text.strip())

                __temp_review_strong = __temp_review_container.find("strong")
                if __temp_review_strong is not None:
                    __temp_review_contents.append(__temp_review_strong.text.strip())

                __temp_review_read_more = __temp_review_container.find(
                    "p", class_="read-more"
                )
                _read_more_text = __temp_review_read_more.text.strip() if __temp_review_read_more is not None else ""
                __temp_review_vote = __temp_review_container.find(
                    "div", class_="review-helpful"
                )
                _vote_text = __temp_review_vote.text.strip() if __temp_review_vote is not None else ""

                for i in __temp_review_container.find_all("br"):
                    i.replace_with("\n")

                __temp_review_content = (
                    __temp_review_container.text.replace(
                        __temp_review_ratings.text.strip(), ""
                    )
                    .replace(_read_more_text, "")
                    .replace(_vote_text, "")
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

                _overall_span = __temp_review_ratings_overall.find("span")
                __temp_review["ratings"] = {
                    "overall": float(_overall_span.text.strip()) if _overall_span is not None else 0.0
                }
                _review_rating_div = __temp_review_ratings.find(
                    "div", class_="review-rating"
                )
                __temp_review_ratings_others = _review_rating_div.find_all("div") if _review_rating_div is not None else []

                # other review ratings, it might be different in each box?
                for k in __temp_review_ratings_others:
                    _span = k.find("span")
                    if _span is None:
                        continue
                    __temp_review["ratings"][
                        k.text.replace(_span.text.strip(), "").strip()
                    ] = float(_span.text.strip())

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
        if self.soup is None:
            return

        container = self.soup.find_all("div", class_="mdl-style-list")
        if container is None:
            return

        titles = [self._parse_title(item) for item in container]
        dramas = [self._parse_drama(item) for item in container]
        stats = [self._parse_total_stats(item) for item in container]

        items = {}
        for title, drama, stat in zip(titles, dramas, stats, strict=False):
            items[title] = {"items": drama, "stats": stat}

        self.info["list"] = items

    def _parse_title(self, item: Tag) -> str:
        label = item.find("h3", class_="mdl-style-list-label")
        if label is None:
            return ""

        return label.get_text(strip=True)

    def _parse_total_stats(self, item: Tag) -> Dict[str, str]:
        drama_stats = item.find("label", class_="mdl-style-dramas")
        tvshows_stats = item.find("label", class_="mdl-style-tvshows")
        episodes_stats = item.find("label", class_="mdl-style-episodes")
        movies_stats = item.find("label", class_="mdl-style-movies")
        days_stats = item.find("label", class_="mdl-style-days")

        result: Dict[str, str] = {}
        for label in [drama_stats, tvshows_stats, episodes_stats, movies_stats, days_stats]:
            if label is None:
                continue
            name_span = label.find("span", class_="name")
            cnt_span = label.find("span", class_="cnt")
            if name_span is None or cnt_span is None:
                continue
            result[name_span.get_text(strip=True)] = cnt_span.get_text(strip=True)
        return result

    def _parse_drama(self, item: Tag) -> List[Dict[str, str]]:
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
            strict=False,
        ):
            parsed_item = {
                "name": name.get_text(strip=True),
                "id": str(name.get("href", "")).split("/")[-1],
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
        if self.soup is None:
            return

        container = self.soup.find("div", class_="app-body")
        if container is None:
            return

        # get list title
        header = container.find("div", class_="box-header")
        if header is None:
            return
        _h1 = header.find("h1")
        if _h1 is None:
            return
        self.info["title"] = _h1.get_text().strip()

        description = header.find("div", class_="description")
        self.info["description"] = (
            description.get_text().strip() if description is not None else ""
        )

        # get list
        container_list = container.find("div", class_="collection-list")
        if container_list is None:
            return
        all_items = container_list.find_all("li")
        list_items = []
        for i in all_items:
            _a = i.find("a")
            if _a is None:
                continue
            i_url = str(_a.get("href", ""))
            if "/people/" in i_url:
                list_items.append(self._parse_person(i))
                continue

            list_items.append(self._parse_show(i))

        self.info["list"] = list_items

    def _parse_person(self, item: Tag) -> Dict[str, Any]:
        # parse person image
        person_img_container = item.find("img", class_="img-responsive")
        if person_img_container is None:
            person_img_container = {}
        person_img_src = str(person_img_container.get("data-src", "")).split("/1280/")
        person_img = ""
        if len(person_img_src) > 1:
            person_img = person_img_src[1]
        else:
            person_img = person_img_src[0]

        person_img = person_img.replace(
            "s.jpg", "m.jpg"
        )  # replace image url to give the bigger size

        item_header = item.find("div", class_="content")
        if item_header is None:
            return {
                "name": "",
                "type": "person",
                "image": person_img,
                "slug": "",
                "url": "",
            }
        _person_a = item_header.find("a")
        if _person_a is None:
            return {
                "name": "",
                "type": "person",
                "image": person_img,
                "slug": "",
                "url": "",
            }
        person_name = _person_a.get_text().strip()
        person_slug = str(_person_a.get("href", ""))
        person_url = urljoin(MYDRAMALIST_WEBSITE, person_slug)

        person_nationality_container = item.find(class_="text-muted")
        person_nationality = (
            person_nationality_container.get_text().strip()
            if person_nationality_container
            else ""
        )
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

    def _parse_show(self, item: Tag) -> Dict[str, Any]:
        # parse list image
        list_img_container = item.find("img", class_="img-responsive")
        if list_img_container is None:
            list_img_container = {}
        list_img_src = str(list_img_container.get("data-src", "")).split("/1280/")
        list_img = ""
        if len(list_img_src) > 1:
            list_img = list_img_src[1]
        else:
            list_img = list_img_src[0]

        list_img = list_img.replace(
            "t.jpg", "c.jpg"
        )  # replace image url to give the bigger size

        list_header = item.find("h2")
        if list_header is None:
            return {
                "title": "",
                "image": list_img,
                "rank": "",
                "url": "",
                "slug": "",
                "type": "",
                "year": "",
                "episodes": None,
                "short_summary": "",
            }
        _list_a = list_header.find("a")
        if _list_a is None:
            return {
                "title": "",
                "image": list_img,
                "rank": "",
                "url": "",
                "slug": "",
                "type": "",
                "year": "",
                "episodes": None,
                "short_summary": "",
            }
        list_title = _list_a.get_text().strip()
        list_title_rank = (
            list_header.get_text().replace(list_title, "").strip().strip(".")
        )
        list_url = urljoin(MYDRAMALIST_WEBSITE, str(_list_a.get("href", "")))
        list_slug = _list_a.get("href")

        # parse example: `Korean Drama - 2020, 16 episodes`
        list_details_container = item.find(class_="text-muted")  # could be `p` or `div`
        list_details_xx = (
            list_details_container.get_text().split(",")
            if list_details_container
            else ""
        )
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


class FetchEpisodes(BaseFetch):
    def __init__(self, soup, query, code, ok):
        super().__init__(soup, query, code, ok)

    def _get_main_container(self) -> None:
        if self.soup is None:
            return

        container = self.soup.find("div", class_="app-body")
        if container is None:
            return

        title = self._parse_title(container)
        episodes = self._parse_episodes(container)

        self.info = {
            "title": title,
            "episodes": episodes,
        }

    def _parse_episodes(self, item: Tag) -> List[Dict[str, Any]]:
        episodes_container = item.find("div", class_="episodes")
        if episodes_container is None:
            return []

        epi_list = episodes_container.find_all(
            "div", class_="col-xs-12 col-sm-6 col-md-4 p-a episode"
        )

        episodes = []
        for epi in epi_list:
            _title_tag = epi.find("h2", class_="title")
            if _title_tag is None:
                continue
            title = _title_tag.get_text(strip=True)

            cover = epi.find("div", class_="cover")
            if cover is None:
                continue
            _img_tag = cover.find("img")
            img = str(_img_tag.get("data-src", "")) if _img_tag is not None else ""
            _a_tag = cover.find("a")
            link = urljoin(MYDRAMALIST_WEBSITE, str(_a_tag.get("href", ""))) if _a_tag is not None else ""

            _rating_panel = epi.find("div", class_="rating-panel m-b-0")
            _rating_div = _rating_panel.find("div") if _rating_panel is not None else None
            rating = _rating_div.get_text(strip=True) if _rating_div is not None else ""

            air_date: str | None = None
            try:
                _air_date_tag = epi.find("div", class_="air-date")
                if _air_date_tag is not None:
                    air_date = _air_date_tag.get_text(strip=True)
            except Exception:
                pass

            episodes.append(
                {
                    "title": title,
                    "image": img,
                    "link": link,
                    "rating": rating,
                    "air_date": air_date,
                }
            )

        return episodes

    def _parse_title(self, item: Tag) -> str:
        title_container = item.find("h1", class_="film-title")

        return title_container.get_text(strip=True) if title_container else ""

    def _get(self):
        self._get_main_container()
