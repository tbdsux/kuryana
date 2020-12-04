from api.parser import Parser
import requests
from bs4 import BeautifulSoup


class Fetch(Parser):
    def __init__(self) -> None:
        super().__init__()

    async def get(self, title):
        # get the website and soup
        soup = BeautifulSoup(
            requests.get(self.website + title, headers=self.headers).text, "html.parser"
        )

        # get the container
        container = soup.find("div", class_="app-body")

        # get the details
        details = soup.find("ul", class_="list m-a-0 hidden-md-up")

        # others
        others = soup.find("div", class_="show-detailsxss").find(
            "ul", class_="list m-a-0"
        )

        try:
            drama = {}

            # extract useful information
            drama["title"] = (
                container.find("h1", class_="film-title").find("a").get_text()
            )
            drama["rating"] = (
                container.find("div", class_="col-film-rating").find("div").get_text()
            )
            drama["poster"] = container.find("img", class_="img-responsive")[
                "data-cfsrc"
            ]
            drama["synopsis"] = (
                container.find("div", class_="show-synopsis")
                .find("span")
                .get_text()
                .replace("\n", " ")
            )
            drama["casts"] = [
                i.find("a", class_="text-primary text-ellipsis").find("b").get_text()
                for i in container.find_all("li", class_="list-item col-sm-4")
            ]

            # get the details
            drama["details"] = {}
            all_details = details.find_all("li")
            for i in all_details:
                # get each li from <ul>
                _title = i.find("b").get_text()
                drama["details"][_title.replace(":", "").replace(" ", "_").lower()] = (
                    i.get_text().replace(_title + " ", "").strip()
                )  # remove leading and trailing white spaces

            # get other details
            drama["others"] = {}
            all_others = others.find_all("li")
            for i in all_others:
                # get each li from <ul>
                _title = i.find("b").get_text()
                drama["others"][_title.replace(":", "").replace(" ", "_").lower()] = (
                    i.get_text().replace(_title + " ", "").strip()
                )  # remove leading and trailing white spaces

            return drama

        except Exception:
            # if the page was not found,
            # or there was a problem with scraping,
            # try to get the error and return the err message
            err = {}
            err["status"] = "404 Not Found"
            err["error"] = (
                container.find("div", class_="box-body").find("h1").get_text()
            )
            err["info"] = container.find("div", class_="box-body").find("p").get_text()

            return err

    async def cache(self, result):
        pass