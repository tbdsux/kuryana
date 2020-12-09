from api.parser import Parser
from bs4 import BeautifulSoup

# TBU -> for searching dramas
class Search(Parser):
    def __init__(self, query) -> None:
        super().__init__(query)
        self.url = "search?q=" + self.query.replace(" ", "+")
        self.mdl_container_id = "mdl-"

    # get the main html container for the each search results
    def get_container(self):
        boxes = self.soup.find("div", class_="col-lg-8 col-md-8").find_all(
            "div", class_="box"
        )

        raw = []
        for i in boxes:
            try:
                if i["id"].startswith(self.mdl_container_id):
                    raw.append(i)
            except Exception:
                pass  # do nothing with other search results

        # return the raw search results
        return raw

    # get the search result ranking
    def res_get_ranking(self, result_container):
        try:
            ranking = result_container.find("div", class_="ranking pull-right").find(
                "span"
            )
        except AttributeError:
            return None  # return None if the result doesn't have it

        return ranking.get_text()

    # get the year info of the result
    def res_get_year_info(self, result_container):
        # extract the type and year
        _typeyear = result_container.find("span", class_="text-muted").get_text()
        _year_eps = _typeyear.split("-")[1]

        # get the drama type [movie / series]
        try:
            type = _typeyear.split("-")[0].strip()
        except Exception:
            type = None

        # get the year
        try:
            year = int(_year_eps.split(",")[0].strip())
        except Exception:
            year = None

        # get the # of eps if series
        try:
            series_ep = _year_eps.split(",")[1].strip()
        except Exception:
            series_ep = False

        return type, year, series_ep

    # extract the urls of the search result
    def res_get_url(self, result_container):
        return self.website + result_container.find(
            "h6", class_="text-primary title"
        ).find("a")["href"].replace("/", "")

    # search results handler
    def get_search_results(self):
        results = self.get_container()  # get the search results

        for result in results:
            drama = {}
            drama["mdl_id"] = result["id"]

            # extract drama title
            title = result.find("h6", class_="text-primary title").find("a")
            drama["title"] = title.get_text().replace("\n", "")
            drama["slug"] = title["href"].replace("/", "")

            # drama ranking
            drama["ranking"] = self.res_get_ranking(result)

            # specific drama info
            drama["type"], drama["year"], drama["series"] = self.res_get_year_info(
                result
            )

            # get the thumbnail
            drama["thumb"] = result.find("img", class_="img-responsive")["data-src"]

            # append each
            self.search_dramas_output.append(drama)

        # return true after appending each search result
        return True