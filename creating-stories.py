# from serpapi import GoogleSearch
import serpapi
import json

SERP_API_TOKEN_FILE = "serp_token.txt"

with open(SERP_API_TOKEN_FILE, "r") as file:
    api_key = file.read().strip()

def get_trending_searches():
    params = {
        "engine": "google_trends_trending_now",
        "geo": "US",
        "api_key": api_key
    }
    # search = GoogleSearch(params)
    search = serpapi.search(params)
    results = search.as_dict()
    return results

# res = get_trending_searches()
# res_json = json.dumps(res, indent=2)
# with open("trending_searches.json", "w") as file:
#     file.write(res_json)

def mock_get_trending_searches():
    with open("mock_trending_searches.json", "r") as file:
        data = json.load(file)
        return data

res = mock_get_trending_searches()