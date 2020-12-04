from api.parser import Parser
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

        # contain the results in a list
        res = {}
        res["results"] = []

        # parse each to dramas dictionary
        for result in results:
            try:
                # get the MDL-ID
                # if there is, it can be a series or a movie,
                # persons have likes so, all shows / movies should have a ranking
                if result["id"].startswith("mdl-"):
                    drama = {}

                    drama["mdl_id"] = result["id"]

                    # extract drama title
                    title = (
                        result.find("h6", class_="text-primary title")
                        .find("a")
                        .get_text()
                    )
                    drama["title"] = title.replace("\n", "")

                    drama["slug"] = (
                        result.find("h6", class_="text-primary title")
                        .find("a")["href"]
                        .replace("/", "")
                    )

                    # get the ranking if it exists
                    try:
                        ranking = result.find("div", class_="ranking pull-right").find(
                            "span"
                        )
                        drama["ranking"] = ranking.get_text()
                    except AttributeError:
                        drama["ranking"] = None

                    try:
                        # extract the type and year
                        _typeyear = result.find("span", class_="text-muted").get_text()
                        drama["type"] = _typeyear.split("-")[0].strip()

                        _year_eps = _typeyear.split("-")[1]
                        drama["year"] = _year_eps.split(",")[0].strip()
                        drama["series"] = _year_eps.split(",")[1].strip()
                    except Exception:
                        pass

                    # extract the url
                    drama["url"] = self.website + result.find(
                        "h6", class_="text-primary title"
                    ).find("a")["href"].replace("/", "")

                    # extract the thumbnail
                    drama["thumb"] = result.find("img", class_="img-responsive")[
                        "data-src"
                    ]

                    # append to the dramas
                    res["results"].append(drama)
            except Exception:
                pass

        return res