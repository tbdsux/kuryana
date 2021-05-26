from api.search import Search
from api.fetch import Fetch


# search function
async def search_func(query):
    func = Search(query=query)  # initiate

    # start searching and scrape
    scrape = await func.scrape()
    if scrape:
        # assert the status code
        if func.check_status_code():
            # compile search results
            if func.get_search_results():
                # return the results
                return func.SEARCH()

    return False


# fetch function
async def fetch_func(drama_id):
    func = Fetch(query=drama_id)

    # get the drama_id info
    scrape = await func.scrape()
    if scrape:
        # assert status code
        if func.check_status_code():
            # get the drama data
            if func.get_drama():
                # return the result
                return True, func.FETCH()

        err = func.res_get_err()
        if len(err) > 0:
            # return the 404 error from the website
            return False, err

    return False, False
