from api.parser import BaseFetch

from bs4 import BeautifulSoup


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
        # scrape each
        self._get_main_container()
        self._get_details(classname="list m-a-0 hidden-md-up")
        self._get_other_info()


class FetchPerson(BaseFetch):
    def __init__(self, soup: BeautifulSoup, query: str, code: int, ok: bool) -> None:
        super().__init__(soup, query, code, ok)
