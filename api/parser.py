# import httpx

# bypassing cloudflare anti-bot
import cloudscraper

from bs4 import BeautifulSoup
from datetime import datetime

# MAIN Parser class
class Parser:
    def __init__(self, query) -> None:
        self.soup = ""
        self.query = query
        self.status_code = 0
        self.url = ""
        self.website = "https://mydramalist.com/"
        self.headers = {
            "Referer": self.website,
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.123 Mobile Safari/537.36",
        }

        # define outputs
        self.drama_info = {}  # fetch
        self.search_dramas_output = []  # search

    # MAIN SEARCH FUNCTION HANDLER
    def SEARCH(self):
        results = {}
        results["query"] = self.query
        results["results"] = self.search_dramas_output
        results["scrape_date"] = datetime.utcnow()  # add date

        return results

    # MAIN FETCH FUNCTION HANDLER
    def FETCH(self):
        result = {}
        result["slug_query"] = self.url
        result["data"] = self.drama_info
        result["scrape_date"] = datetime.utcnow()

        return result

    # status code checker
    def check_status_code(self):
        if self.status_code == 200:
            return True

        return False

    # website getter / page source grabber
    async def scrape(self):
        try:
            # async with httpx.AsyncClient() as client:
            #     resp = await client.get(self.website_def(), timeout=None)

            # bypassing cloudflare anti-bot
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(self.website_def(), headers=self.headers)

            # set the main soup var
            self.soup = BeautifulSoup(resp.text, "lxml")

            # set the status code
            self.status_code = resp.status_code
        except Exception:
            return False

        # return True, signify done
        return True

    # main url website handler
    def website_def(self):
        return self.website + self.url
