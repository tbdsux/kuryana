from api.parser import Parser
import httpx
from bs4 import BeautifulSoup


class Fetch(Parser):
    def __init__(self, query) -> None:
        super().__init__(query)
        self.url = self.query

    # get the main html container for the each search results
    def get_main_container(self):
        container = self.soup.find("div", class_="app-body")

        # append scraped data
        # these are the most important drama infos / details
        self.drama_info["title"] = (
            container.find("h1", class_="film-title").find("a").get_text()
        )
        self.drama_info["rating"] = float(
            (container.find("div", class_="col-film-rating").find("div").get_text())
        )
        self.drama_info["poster"] = container.find("img", class_="img-responsive")[
            "src"
        ]
        print(container.find("img", class_="img-responsive"))
        self.drama_info["synopsis"] = (
            container.find("div", class_="show-synopsis")
            .find("span")
            .get_text()
            .replace("\n", " ")
        )
        self.drama_info["casts"] = [
            i.find("a", class_="text-primary text-ellipsis")
            .find("b")
            .get_text()
            .strip()
            for i in container.find_all("li", class_="list-item col-sm-4")
        ]

    # get the drama details <= statistics section is added in here
    def get_details(self):
        details = self.soup.find("ul", class_="list m-a-0 hidden-md-up")

        try:
            self.drama_info["details"] = {}
            all_details = details.find_all("li")

            for i in all_details:
                # get each li from <ul>
                _title = i.find("b").get_text().strip()

                # append each to sub object
                self.drama_info["details"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = (
                    i.get_text().replace(_title + " ", "").strip()
                )  # remove leading and trailing white spaces

        except Exception:
            print("Error scraping drama details section.")

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
                _title = i.find("b").get_text().strip()
                self.drama_info["others"][
                    _title.replace(":", "").replace(" ", "_").lower()
                ] = (
                    i.get_text().replace(_title + " ", "").strip()
                )  # remove leading and trailing white spaces

        except Exception:
            print("Error scraping drama others section.")

    # get page err, if possible
    def res_get_err(self):
        container = self.soup.find("div", class_="app-body")

        # if the page was not found,
        # or there was a problem with scraping,
        # try to get the error and return the err message
        err = {}
        err["status"] = "404 Not Found"
        err["status_code"] = self.status_code
        err["error"] = container.find("div", class_="box-body").find("h1").get_text()
        err["info"] = container.find("div", class_="box-body").find("p").get_text()

        return err

    # drama info details handler
    def get_drama(self):
        try:
            # scrape each
            self.get_main_container()
            self.get_details()
            self.get_other_info()

        except Exception:
            try:
                return self.res_get_err()
            except Exception:
                pass

            print("Err scraping the webpage!")

        # return the compiled
        return True