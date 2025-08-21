# from serpapi import GoogleSearch
import serpapi
import json
import sqlite3
from datetime import datetime

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

def load_trending_searches():
    with open("trending_searches.json", "r") as file:
        data = json.load(file)
        return data

def format_categories(categories):
    """Format categories as {id1}-{name1}|{id2}-{name2}"""
    if not categories:
        return ""
    return "|".join([f"{cat['id']}-{cat['name']}" for cat in categories])

def format_trend_breakdown(trend_breakdown):
    """Format trend_breakdown as {term1}|{term2}..."""
    if not trend_breakdown:
        return ""
    return "|".join(trend_breakdown)

def save_to_database(data):
    """Save trending searches data to the database"""
    conn = sqlite3.connect('trends_data.db')
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for trend in data.get('trending_searches', []):
        categories_str = format_categories(trend.get('categories', []))
        trend_breakdown_str = format_trend_breakdown(trend.get('trend_breakdown', []))
        
        cursor.execute('''
            INSERT INTO serpapi_data (
                query, start_timestamp, active, search_volume, increase_percentage,
                categories, trend_breakdown, serpapi_google_trends_link,
                news_page_token, serpapi_news_link, date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trend.get('query'),
            trend.get('start_timestamp'),
            trend.get('active'),
            trend.get('search_volume'),
            trend.get('increase_percentage'),
            categories_str,
            trend_breakdown_str,
            trend.get('serpapi_google_trends_link'),
            trend.get('news_page_token'),
            trend.get('serpapi_news_link'),
            current_date
        ))
    
    conn.commit()
    conn.close()
    print(f"Successfully saved {len(data.get('trending_searches', []))} trending searches to database")

# Load data from trending_searches.json and save to database
data = load_trending_searches()
save_to_database(data)