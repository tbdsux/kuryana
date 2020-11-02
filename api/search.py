from .parser import Parser
import requests
from bs4 import BeautifulSoup

# TBU -> for searching dramas
class Search(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.url = "search?q="

    async def get(self, query):

        # search the website with the query and get the soup
        soup = BeautifulSoup(
            requests.get(
                self.website + self.url + query.replace(" ", "+"), headers=self.headers
            ).text,
            "html.parser",
        ).find("div", class_="col-lg-8 col-md-8")

        # get the results
        results = soup.find_all("div", class_="box")

        dramas = {}

        # parse each to dramas dictionary
        for i, result in enumerate(results):
            drama = {}

            # extract drama title
            title = result.find("h6", class_="text-primary title").find("a").get_text()
            drama["title"] = title.replace("\n", "")

            drama["slug"] = (
                result.find("h6", class_="text-primary title")
                .find("a")["href"]
                .replace("/", "")
            )

            # extract the url
            drama["url"] = self.website + result.find(
                "h6", class_="text-primary title"
            ).find("a")["href"].replace("/", "")

            # extract the thumbnail
            drama["thumb"] = result.find("img", class_="img-responsive")["data-cfsrc"]

            # append to the dramas
            dramas[i] = drama

        return dramas