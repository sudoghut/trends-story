# from serpapi import GoogleSearch
import serpapi
import json
import sqlite3
import asyncio
import websockets
import time
from datetime import datetime
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import time

SERP_API_TOKEN_FILE = "serp_token.txt"
MAX_RETRIES = 4
NUM_STORIES_TO_CREATE = 1
TODAY_YYYYMMDD = time.strftime("%Y%m%d")
TODAY_HHMMSS = time.strftime("%H%M%S")
NEWS_TO_KEYWORDS_PROMPT = '''
### **Refined Prompt Template**

**Objective:** Analyze the following story to generate a comma-separated list of keywords for an AI image generation model (Flux.1). The keywords must represent the abstract emotional summary of the narrative, avoiding all specific, concrete details.

**Instructions:**

1.  **Identify Core Emotions:** Read the story to determine its central emotional themes, underlying mood, and the emotional journey it portrays.
2.  **Translate to Abstract Concepts:** Convert these emotions into abstract, symbolic, and conceptual keywords. Focus on feelings, atmospheres, and intangible ideas.
3.  **Generate Keyword List:** Create a single, comma-separated list of these keywords. They should be evocative and suitable for creating a metaphorical and artistic image.
4. The image should be in the style of a flat illustration with crosshatching.

**Strict Constraints (What to Exclude):**

* **Absolutely NO specific entities:** Do not include names of people, characters, brands, or organizations. Do not include any people, characters, brands, or organizations.
* **Absolutely NO specific objects or places:** Do not mention any concrete items, locations, cities, or countries.
* The goal is to capture the *feeling* of the story, not its literal appearance.

**Example of a good output for a story about overcoming grief:**
`melancholic solitude, emerging hope, quiet resilience, the weight of memory, a fragile dawn, inner turmoil, cathartic release, profound connection, bittersweet reflection.`

**Final Output Format:**
Provide only the final, comma-separated list of keywords.

**Source Story:**\n
'''

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

def load_trending_searches(file_path):
    with open(file_path, "r") as file:
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

def create_prompt_for_story_generation(serpapi_record):
    """Create a prompt for story generation based on serpapi record"""
    story_parts = []
    if serpapi_record.get("query"):
        story_parts.append(f"You are given Google Trends search keywords: `{serpapi_record['query']}`")
    if serpapi_record.get("categories"):
        story_parts.append(f"their corresponding categories: `{serpapi_record['categories']}`")
    if serpapi_record.get("trend_breakdown"):
        story_parts.append(f"and related details: `{serpapi_record['trend_breakdown']}`")
    
    if story_parts:
        story = ", ".join(story_parts) + ". Based on this information and real-world context, explain in plain, simple words the background and reasons why these keywords are trending, so that someone with no prior knowledge can easily understand. Do not repeat the information that I provided; instead, generate only the background and reasons directly."
        return story
    else:
        print("No relevant fields found in the record.")
        return None

async def ws_send_prompt(prompt, system_prompt):
    """Send prompt to websocket API and return the response"""
    ws_url = "wss://queue.oopus.info"
    response_content = None
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # Send the request
            request = {
                "type": "request",
                "parameters": {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "llm": "gemini",
                    "search": 1,
                },
            }
            await websocket.send(json.dumps(request))
            print("Sent to server:", json.dumps(request, ensure_ascii=False))

            # Collect all responses from the server
            async for message in websocket:
                print("Received:", message)
                try:
                    parsed_message = json.loads(message)
                    if parsed_message.get("type") == "result":
                        data = parsed_message.get("data", {})
                        if "Ok" in data:
                            response_content = data["Ok"].get("content", "")
                            break
                except json.JSONDecodeError:
                    continue
                
    except websockets.exceptions.ConnectionClosed:
        # Normal connection closure after receiving data is not an error
        pass
    except Exception as e:
        if response_content is None:  # Only raise if we didn't get valid content
            print("WebSocket error:", str(e))
            raise e
    
    if response_content is None:
        raise Exception("No valid response content received")
    
    return response_content

async def call_api_with_retry(prompt, system_prompt="You are a helpful assistant."):
    """Create a story with retry logic"""
    if not prompt:
        return None
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Attempt {attempt + 1} for query: {prompt}")
            story = await ws_send_prompt(prompt, system_prompt)
            return story
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:  # Don't wait after the last attempt
                if attempt < 3:  # First 3 attempts: wait 5 seconds
                    print("Waiting 5 seconds before retry...")
                    await asyncio.sleep(5)
                else:  # 4th attempt: wait 5 minutes
                    print("Waiting 5 minutes before retry...")
                    await asyncio.sleep(300)
    
    print(f"Failed to create story after {MAX_RETRIES} attempts")
    return None

def save_story_to_database(story, serpapi_id):
    """Save the generated story to main_news_data table"""
    conn = sqlite3.connect('trends_data.db')
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO main_news_data (news, date, serpapi_id)
        VALUES (?, ?, ?)
    ''', (story, current_date, serpapi_id))
    
    conn.commit()
    conn.close()
    print(f"Successfully saved story for serpapi_id: {serpapi_id}.")

def save_to_database(data, db_name):
    """Save trending searches data to the database"""
    conn = sqlite3.connect(db_name)
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

async def create_stories(db_name):
    """Create stories for trending searches"""
    
    # Get the specified number of records from the database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM serpapi_data ORDER BY id ASC LIMIT ?', (NUM_STORIES_TO_CREATE,))
    rows = cursor.fetchall()
    
    # Get column names
    col_names = [desc[0] for desc in cursor.description]

    counter = 0
    
    for row in rows:
        record = dict(zip(col_names, row))
        serpapi_id = record['id']

        counter += 1
        print(f"Processing record {counter}/{len(rows)} with serpapi_id: {serpapi_id}")
        
        # Check if story already exists
        cursor.execute('SELECT id FROM main_news_data WHERE serpapi_id = ?', (serpapi_id,))
        if cursor.fetchone():
            print(f"Story already exists for serpapi_id: {serpapi_id}, skipping...")
            continue
        prompt_for_generating_story = create_prompt_for_story_generation(record)
        # Create story
        story = await call_api_with_retry(prompt_for_generating_story)
        prompt_for_generating_image_prompts = NEWS_TO_KEYWORDS_PROMPT + story
        # Create image prompts
        image_prompts = await call_api_with_retry(prompt_for_generating_image_prompts)
        # Create image
        if story:
            save_story_to_database(story, serpapi_id)
        else:
            print(f"Failed to create story for serpapi_id: {serpapi_id}")
    
    conn.close()


# res = get_trending_searches()
# res_json = json.dumps(res, indent=2)
# with open("trending_searches.json", "w") as file:
#     file.write(res_json)
data = load_trending_searches("trending_searches.json")
trends_data_db_name = 'trends_data.db'
save_to_database(data, trends_data_db_name)
asyncio.run(create_stories(trends_data_db_name))