from .parser import Parser
import requests
from bs4 import BeautifulSoup

# TBU -> for searching dramas
class Search(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.url = "search?q="

    def get(self, query):
        # search the website with the query and get the soup
        soup = BeautifulSoup(
            requests.get(
                self.website + self.url + query.replace(" ", "+"), headers=self.headers
            ).text,
            "html.parser",
        ).find("div", class_="col-lg-8 col-md-8")

        # get the results
        results = soup.find_all("div", class_="box")

        try:
            # contain the results in a list
            res = {}
            res["results"] = []

            # parse each to dramas dictionary
            for i, result in enumerate(results):
                try:
                    # get the ranking
                    # if there is, it can be a series or a movie,
                    # persons have likes so, all shows / movies should have a ranking
                    ranking = result.find("div", class_="ranking pull-right").find(
                        "span"
                    )

                    drama = {}

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

                    drama["ranking"] = ranking.get_text()

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
                        "data-cfsrc"
                    ]

                    # append to the dramas
                    res["results"].append(drama)

                except Exception:
                    # do nothing is the ranking doesn't exist
                    pass

            return res

        except Exception:
            # if there are no search results,
            # get the err message
            error = results[0]

            err = {}
            err["status"] = "Nothing was found..."
            err["error"] = error.find("div", class_="box-header").get_text()
            err["info"] = [i.get_text() for i in error.find("ul").find_all("li")]

            return err