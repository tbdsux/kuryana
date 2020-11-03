from .parser import Parser
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
                container.find("div", class_="show-synopsis").find("span").get_text()
            )
            drama["casts"] = [
                i.find("a", class_="text-primary text-ellipsis").find("b").get_text()
                for i in container.find_all("li", class_="list-item col-sm-4")
            ]

            return drama

        except Exception:
            # if the page was not found,
            # or there was a problem with scraping,
            # return the err message
            err = {}
            err["status"] = "404 Not Found"
            err["error"] = (
                container.find("div", class_="box-body").find("h1").get_text()
            )
            err["info"] = container.find("div", class_="box-body").find("p").get_text()

            return err