from api.parser import Parser


class Fetch(Parser):
    def __init__(self, query) -> None:
        super().__init__(query)
        self.url = self.query
        self._img_attrs = ["src", "data-cfsrc", "data-src"]

    # get the main html container for the each search results
    def get_main_container(self):
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details

        # TITLE
        self.drama_info["title"] = (
            container.find("h1", class_="film-title").find("a").text
        )

        # RATING
        self.drama_info["rating"] = float(
            (container.find("div", class_="col-film-rating").find("div").text)
        )

        # POSTER
        self.drama_info["poster"] = self._get_drama_poster(container)

        # SYNOPSIS
        self.drama_info["synopsis"] = (
            container.find("div", class_="show-synopsis")
            .find("span")
            .text
            .replace("\n", " ")
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
        self.drama_info["casts"] = casts

    def _get_drama_poster(self, container) -> str:
        poster = container.find("img", class_="img-responsive")

        for i in self._img_attrs:
            if poster.has_attr(i):
                return poster[i]

        # blank if none
        return ""

    # get the drama details <= statistics section is added in here
    def get_details(self):
        details = self.soup.find("ul", class_="list m-a-0 hidden-md-up")

        try:
            self.drama_info["details"] = {}
            all_details = details.find_all("li")

            for i in all_details:
                # get each li from <ul>
                _title = i.find("b").text.strip()

                # append each to sub object
                self.drama_info["details"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = (
                    i.text.replace(_title + " ", "").strip()
                )  # remove leading and trailing white spaces

        except Exception:
            # do nothing, if there was a problem
            pass

    # get other info
    def get_other_info(self):
        others = self.soup.find("div", class_="show-detailsxss").find(
            "ul", class_="list m-a-0"
        )

        try:
            self.drama_info["others"] = {}
            all_others = others.find_all("li")
            for i in all_others:
                # get each li from <ul>
                _title = i.find("b").text.strip()
                self.drama_info["others"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = (
                    i.text.replace(_title + " ", "").strip()
                )  # remove leading and trailing white spaces

        except Exception:
            # there was a problem while trying to parse
            # the :> other info section
            pass

    # get page err, if possible
    def res_get_err(self):
        container = self.soup.find("div", class_="app-body")

        # if the page was not found,
        # or there was a problem with scraping,
        # try to get the error and return the err message
        err = {}

        try:
            err["status"] = "404 Not Found"
            err["status_code"] = self.status_code
            err["error"] = (
                container.find("div", class_="box-body").find("h1").text
            )
            err["info"] = container.find("div", class_="box-body").find("p").text
        except Exception:
            pass

        return err

    # drama info details handler
    def get_drama(self):
        try:
            # scrape each
            self.get_main_container()
            self.get_details()
            self.get_other_info()

        except Exception:
            # there was a problem with one of
            # the functions above
            return False

        # return the compiled
        return True
