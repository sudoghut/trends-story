import serpapi
import json
import sqlite3
import asyncio
import websockets
import time
import os
import re
import random
from datetime import datetime
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import time

SERP_API_TOKEN_FILE = "serp_token.txt"
SERVER_ADDRESS = "127.0.0.1:8188"
MAX_RETRIES = 4
NUM_STORIES_TO_CREATE = 10
TODAY_YYYYMMDD = time.strftime("%Y%m%d")
TODAY_HHMMSS = time.strftime("%H%M%S")
IMAGE_DIR = f"images/{TODAY_YYYYMMDD}"
NEWS_TO_KEYWORDS_PROMPT = '''
**Task:** Generate a set of `keywords` for an AI image generation model (**Flux.1**) to create **WordArt**.
**Goal:** Design artistic text for the phrase **"{keywords}"**, visually expressing the **themes, emotions, and atmosphere** of the given story.
**Guidelines:**
* Focus on **aesthetic composition** and **emotional resonance** aligned with the story’s mood.
* Include references to **art styles, materials, textures, color palettes, or lighting** to enrich the visual concept.
* Do not include any explanations, introductions, or sentences — output only the keyword list.
* Avoid any **prompt-engineering syntax** (e.g., weights, parameters, “–v”, “–ar”, etc.).
* Output only a **clean, descriptive list of keywords** appropriate for Flux.1.
* Begin the list with: `WordArt word:"{keyword}"`
**Story:**\n
'''

def create_news_to_keywords_prompt(keywords):
    return NEWS_TO_KEYWORDS_PROMPT.replace("{keywords}", keywords)

with open(SERP_API_TOKEN_FILE, "r") as file:
    api_key = file.read().strip()

def sanitize_filename(filename):
    """Remove characters that can't be used in Windows and Mac filenames"""
    # Remove or replace invalid characters for Windows and Mac
    invalid_chars = r'[<>:"/\\|?*]'
    # Replace invalid characters with empty string
    sanitized = re.sub(invalid_chars, '', filename)
    # Replace spaces with hyphens
    sanitized = sanitized.replace(' ', '-')
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    # Limit length to avoid filesystem issues
    return sanitized[:100]

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

def queue_prompt(prompt_workflow, client_id):
    """Sends the workflow to the ComfyUI server."""
    p = {"prompt": prompt_workflow, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    """Retrieves the generated image from the server."""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    """Gets the execution history for a prompt."""
    with urllib.request.urlopen(f"http://{SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def create_image(image_prompts, serpapi_record):
    """Create an image using ComfyUI based on the image prompts and serpapi record"""
    client_id = str(uuid.uuid4())
    
    # Create image directory if it doesn't exist
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    # Load workflow from JSON file
    try:
        with open("workflow.json", "r", encoding="utf-8") as f:
            prompt_workflow = json.load(f)
    except FileNotFoundError:
        print("Error: workflow.json not found. Please save your workflow in that file.")
        return None
    
    # Modify the prompt in node "6"
    prompt_workflow["6"]["inputs"]["text"] = f"{image_prompts}"
    # prompt_workflow["6"]["inputs"]["text"] = f"(Style: flat illustration, crosshatching), {image_prompts}"
    
    # Modify the seed in node "31" (KSampler) - use random seed for variation
    prompt_workflow["31"]["inputs"]["seed"] = random.randint(0, 999999999999999)
    
    # Create filename
    query_sanitized = sanitize_filename(serpapi_record.get("query", "unknown"))
    filename_prefix = f"{query_sanitized}_{TODAY_YYYYMMDD}_{TODAY_HHMMSS}"
    prompt_workflow["9"]["inputs"]["filename_prefix"] = filename_prefix
    
    # Connect and queue the prompt
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={client_id}")
        
        prompt_id = queue_prompt(prompt_workflow, client_id)['prompt_id']
        print(f"Queued prompt with ID: {prompt_id}")
        
        # Wait for execution to finish
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    # Check for the final "executed" message for our prompt
                    if data.get('node') is None and data.get('prompt_id') == prompt_id:
                        print("Execution finished.")
                        break
            else:
                # This handles binary preview images, which we can ignore
                continue
        
        # Fetch the output image(s)
        history = get_history(prompt_id)[prompt_id]
        saved_filename = None
        
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    # Create the final filename with .png extension
                    final_filename = f"{filename_prefix}.png"
                    final_filepath = os.path.join(IMAGE_DIR, final_filename)
                    
                    # Save the image
                    with open(final_filepath, "wb") as img_file:
                        img_file.write(image_data)
                        print(f"Successfully saved image: {final_filepath}")
                        saved_filename = final_filename
                        break
                if saved_filename:
                    break
        
        return saved_filename
        
    except Exception as e:
        print(f"An error occurred during image creation: {e}")
        return None
    finally:
        ws.close()

def save_image_to_database(filename):
    """Save image filename to image_data table and return the image_id"""
    conn = sqlite3.connect('trends_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO image_data (file_name)
        VALUES (?)
    ''', (filename,))
    
    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"Successfully saved image record with id: {image_id}")
    return image_id

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

def save_story_to_database(story, serpapi_id, image_id=None):
    """Save the generated story to main_news_data table"""
    conn = sqlite3.connect('trends_data.db')
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO main_news_data (news, date, serpapi_id, image_id)
        VALUES (?, ?, ?, ?)
    ''', (story, current_date, serpapi_id, image_id))
    
    conn.commit()
    conn.close()
    print(f"Successfully saved story for serpapi_id: {serpapi_id} with image_id: {image_id}.")

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
    start_time = time.time()
    print(f"Program started at: {datetime.now().strftime('%Y%m%d %H:%M:%S')}")

    # Get the specified number of records from the database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # First get the last one record of the date(TEXT) from serpapi_data(Ex: 2025-10-03 15:29:02). Using this as a filter to get the same date records.
    cursor.execute('SELECT date FROM serpapi_data ORDER BY id DESC LIMIT 1')
    last_date = cursor.fetchone()
    if last_date:
        last_date = last_date[0]
        print(f"Last date found: {last_date}")
    else:
        print("No date found, proceeding without date filter.")
        last_date = None

    cursor.execute('SELECT * FROM serpapi_data WHERE date = ? ORDER BY id ASC LIMIT ?', (last_date, NUM_STORIES_TO_CREATE))
    rows = cursor.fetchall()

    # Get column names
    col_names = [desc[0] for desc in cursor.description]

    counter = 0

    for row in rows:
        record = dict(zip(col_names, row))
        serpapi_id = record['id']
        query = record['query']

        counter += 1
        print(f"Processing record {counter}/{len(rows)} with serpapi_id: {serpapi_id}")
        print(f"Current time: {datetime.now().strftime('%Y%m%d %H:%M:%S')}")

        # Check if story already exists
        cursor.execute('SELECT id FROM main_news_data WHERE serpapi_id = ?', (serpapi_id,))
        if cursor.fetchone():
            print(f"Story already exists for serpapi_id: {serpapi_id}, skipping...")
            continue
        prompt_for_generating_story = create_prompt_for_story_generation(record)
        # Create story
        story = await call_api_with_retry(prompt_for_generating_story)
        prompt_for_generating_image_prompts = create_news_to_keywords_prompt(query) + story
        # Pause for 5s
        await asyncio.sleep(5)
        # Create image prompts
        image_prompts = await call_api_with_retry(prompt_for_generating_image_prompts)
        
        # Create image
        image_id = None
        if image_prompts:
            try:
                image_filename = create_image(image_prompts, record)
                if image_filename:
                    image_id = save_image_to_database(image_filename)
                else:
                    print(f"Failed to create image for serpapi_id: {serpapi_id}")
            except Exception as e:
                print(f"Error creating image for serpapi_id: {serpapi_id}: {e}")
                raise Exception(f"Image creation failed for serpapi_id: {serpapi_id}. Reason: {str(e)}")
        else:
            raise Exception(f"No image prompts generated for serpapi_id: {serpapi_id}")

        if story:
            save_story_to_database(story, serpapi_id, image_id)
        else:
            print(f"Failed to create story for serpapi_id: {serpapi_id}")

    conn.close()
    end_time = time.time()
    print(f"Program ended at: {datetime.now().strftime('%Y%m%d %H:%M:%S')}")
    elapsed = end_time - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    print(f"Total elapsed time: {hours} hours {minutes} minutes {seconds} seconds")



print(f"Starting program at: {datetime.now().strftime('%Y%m%d %H:%M:%S')}")
res = get_trending_searches()
res_json = json.dumps(res, indent=2)
with open("trending_searches.json", "w") as file:
    file.write(res_json)
data = load_trending_searches("trending_searches.json")
trends_data_db_name = 'trends_data.db'
save_to_database(data, trends_data_db_name)
asyncio.run(create_stories(trends_data_db_name))