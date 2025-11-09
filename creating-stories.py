import serpapi
import json
import sqlite3
import asyncio
import websockets
import time
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# New York timezone
NY_TZ = ZoneInfo("America/New_York")

SERP_API_TOKEN_FILE = "serp_token.txt"
MAX_RETRIES = 4
NUM_STORIES_TO_CREATE = 20
# Get current time in New York timezone
now_ny = datetime.now(NY_TZ)
TODAY_YYYY = now_ny.strftime("%Y")
TODAY_MM = now_ny.strftime("%m")
TODAY_DD = now_ny.strftime("%d")
TODAY_YYYYMMDD = now_ny.strftime("%Y%m%d")
TODAY_HHMMSS = now_ny.strftime("%H%M%S")
IMAGE_DIR = f"images/{TODAY_YYYY}/{TODAY_MM}/{TODAY_DD}"

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
        keyword_summary = ", ".join(story_parts) + "."
        format_instructions = """
Based on this information and real-world context, generate a concise news brief explaining why these keywords are trending.
Your audience has no prior knowledge of the topic.

Structure your response *exactly* as follows, using these specific headers in Markdown:

### Summary (tl;dr)
[A one or two-sentence summary of the main point.]

### Essential Background
[Briefly provide the key context or background needed to understand the topic. What happened before this?]

### The Full Story
[Explain the current event or situation. What is happening *right now* and why is it trending today?]

### Why It Matters
[Explain the significance of this trend. Why are people concerned, interested, or searching for this? What are the implications?]

Generate *only* this structured response. Do not repeat the input keywords I provided."""
        
        # Combine the keyword summary and the detailed format instructions
        return f"{keyword_summary}\n\n{format_instructions}"
    else:
        print("No relevant fields found in the record.")
        return None

def create_image(all_queries, current_query, serpapi_record):
    """Create a WordCloud image with all queries as background and current query highlighted
    
    Args:
        all_queries: List of all query strings from the SQL results
        current_query: The current story's query to be highlighted
        serpapi_record: The serpapi record dictionary containing query and other info
    
    Returns:
        str: The filename of the saved image, or None if failed
    """
    try:
        # Create image directory if it doesn't exist
        os.makedirs(IMAGE_DIR, exist_ok=True)
        
        # Combine all queries into a single text corpus
        text_corpus = ' '.join(all_queries)
        
        # Split current query into individual words for highlighting
        highlight_words = set(current_query.lower().split())
        
        # Color function: grey for background words, vibrant color for highlighted words
        def color_func(word, **kwargs):
            if word.lower() in highlight_words:
                return '#FF4500'  # Orange-red for highlighted words
            return '#808080'  # Grey for background words
        
        # Generate wordcloud
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color='white',
            random_state=42,  # Ensures consistent layout within each program run
            colormap=None,  # We'll use custom color function
            relative_scaling=0.5,
            min_font_size=10
        ).generate(text_corpus)
        
        # Apply custom colors
        wordcloud.recolor(color_func=color_func)
        
        # Create filename
        query_sanitized = sanitize_filename(serpapi_record.get("query", "unknown"))
        filename = f"{query_sanitized}_{TODAY_YYYYMMDD}_{TODAY_HHMMSS}.png"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # Save the wordcloud image
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(filepath, dpi=100, bbox_inches='tight')
        plt.close()
        
        print(f"Successfully created WordCloud image: {filepath}")
        return filename
        
    except ImportError:
        print("Error: wordcloud library not installed. Please install it with: pip install wordcloud")
        return None
    except Exception as e:
        print(f"An error occurred during WordCloud image creation: {e}")
        return None

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
    
    # print(f"Successfully saved image record with id: {image_id}")
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
            # print(f"Attempt {attempt + 1} for query: {prompt}")
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
    
    current_date = datetime.now(NY_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO main_news_data (news, date, serpapi_id, image_id)
        VALUES (?, ?, ?, ?)
    ''', (story, current_date, serpapi_id, image_id))
    
    conn.commit()
    conn.close()
    # print(f"Successfully saved story for serpapi_id: {serpapi_id} with image_id: {image_id}.")

def save_to_database(data, db_name):
    """Save trending searches data to the database"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    current_date = datetime.now(NY_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
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

    # last_date just dates. Original format: 'YYYY-MM-DD HH:MM:SS'
    last_date_date_only = last_date.split(' ')[0] if last_date else None

    # Now get records from serpapi_data with the last date, excluding categories '17-Sports' and removing duplicates based on 'query'
    cursor.execute('''
    SELECT * FROM serpapi_data AS sd
    WHERE
        -- Condition 1: Process only the latest batch of data
        sd.date = ?

        -- Condition 2: Exclude news where the category is exclusively '17-Sports'
        AND sd.categories != '17-Sports'
        
        -- Condition 3: Deduplicate queries within the current batch
        AND sd.id IN (
            SELECT MIN(id) FROM serpapi_data
            WHERE date = ? AND categories != '17-Sports'
            GROUP BY query
        )
        
        -- Condition 4: Exclude queries that have already been processed today
        AND NOT EXISTS (
            SELECT 1
            FROM main_news_data AS mnd
            JOIN serpapi_data AS sd_join ON mnd.serpapi_id = sd_join.id
            WHERE sd_join.query = sd.query AND SUBSTR(mnd.date, 1, 10) = ?
        )
    ORDER BY sd.id ASC
    LIMIT ?
    ''', (last_date, last_date, last_date_date_only, NUM_STORIES_TO_CREATE))
    rows = cursor.fetchall()

    # Get column names
    col_names = [desc[0] for desc in cursor.description]
    
    # Extract all queries for WordCloud corpus
    all_queries = [dict(zip(col_names, row))['query'] for row in rows]

    counter = 0

    for row in rows:
        record = dict(zip(col_names, row))
        serpapi_id = record['id']
        query = record['query']

        counter += 1
        print(f"\nProcessing record {counter}/{len(rows)} with serpapi_id: {serpapi_id}")
        print(f"Current time: {datetime.now().strftime('%Y%m%d %H:%M:%S')}")

        # Check if story already exists
        cursor.execute('SELECT id FROM main_news_data WHERE serpapi_id = ?', (serpapi_id,))
        if cursor.fetchone():
            print(f"Story already exists for serpapi_id: {serpapi_id}, skipping...")
            continue
        prompt_for_generating_story = create_prompt_for_story_generation(record)
        # Create story
        story = await call_api_with_retry(prompt_for_generating_story)
        
        # Create image using WordCloud
        image_id = None
        try:
            image_filename = create_image(all_queries, query, record)
            if image_filename:
                image_id = save_image_to_database(image_filename)
            else:
                print(f"Failed to create image for serpapi_id: {serpapi_id}")
        except Exception as e:
            print(f"Error creating image for serpapi_id: {serpapi_id}: {e}")
            raise Exception(f"Image creation failed for serpapi_id: {serpapi_id}. Reason: {str(e)}")

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



def generate_sitemap(db_name):
    """Generate sitemap.xml with homepage and all historical date pages.
    Intelligently merges with existing sitemap if it exists."""
    sitemap_path = 'sitemap.xml'
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    
    # Get dates from database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT date FROM main_news_data ORDER BY date DESC')
    dates = cursor.fetchall()
    conn.close()
    
    # Parse dates from database into a dictionary {date_yyyymmdd: lastmod_date}
    db_urls = {}
    for date_row in dates:
        date_str = date_row[0]  # Format: 'YYYY-MM-DD HH:MM:SS'
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            date_yyyymmdd = date_obj.strftime('%Y%m%d')
            lastmod_date = date_obj.strftime('%Y-%m-%d')
            url = f'https://trending.oopus.info/date/{date_yyyymmdd}'
            db_urls[url] = lastmod_date
        except ValueError as e:
            print(f"Warning: Could not parse date '{date_str}': {e}")
            continue
    
    # Check if sitemap already exists
    existing_urls = {}
    if os.path.exists(sitemap_path):
        print(f"Existing sitemap found at {sitemap_path}, parsing and merging...")
        try:
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            
            # Parse existing URLs with namespace handling
            for url_elem in root.findall(f'{{{namespace}}}url'):
                loc_elem = url_elem.find(f'{{{namespace}}}loc')
                lastmod_elem = url_elem.find(f'{{{namespace}}}lastmod')
                
                if loc_elem is not None and loc_elem.text:
                    loc = loc_elem.text.strip()
                    lastmod = lastmod_elem.text.strip() if lastmod_elem is not None else None
                    
                    # Skip homepage - will be regenerated with current timestamp
                    if loc != 'https://trending.oopus.info/':
                        existing_urls[loc] = lastmod
            
            print(f"Parsed {len(existing_urls)} existing URLs from sitemap")
        except ET.ParseError as e:
            print(f"Warning: Could not parse existing sitemap: {e}. Creating new sitemap.")
            existing_urls = {}
        except Exception as e:
            print(f"Warning: Error reading existing sitemap: {e}. Creating new sitemap.")
            existing_urls = {}
    
    # Merge URLs: use more recent lastmod date for duplicates
    merged_urls = existing_urls.copy()
    new_count = 0
    updated_count = 0
    
    for url, db_lastmod in db_urls.items():
        if url in merged_urls:
            # Compare dates and use the more recent one
            existing_lastmod = merged_urls[url]
            if existing_lastmod and db_lastmod:
                try:
                    existing_date = datetime.strptime(existing_lastmod, '%Y-%m-%d')
                    db_date = datetime.strptime(db_lastmod, '%Y-%m-%d')
                    if db_date > existing_date:
                        merged_urls[url] = db_lastmod
                        updated_count += 1
                except ValueError:
                    # If date parsing fails, use database date
                    merged_urls[url] = db_lastmod
                    updated_count += 1
            else:
                # If one is missing, use the database date
                merged_urls[url] = db_lastmod
                updated_count += 1
        else:
            merged_urls[url] = db_lastmod
            new_count += 1
    
    # Build the sitemap XML
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    # Add homepage first with current timestamp
    current_date = datetime.now(NY_TZ).strftime("%Y-%m-%d")
    sitemap_lines.extend([
        '  <url>',
        '    <loc>https://trending.oopus.info/</loc>',
        f'    <lastmod>{current_date}</lastmod>',
        '  </url>'
    ])
    
    # Sort URLs (excluding homepage) - extract date and sort chronologically
    sorted_urls = []
    for url, lastmod in merged_urls.items():
        # Extract date from URL for sorting (format: /date/YYYYMMDD)
        try:
            date_match = re.search(r'/date/(\d{8})$', url)
            if date_match:
                date_key = date_match.group(1)
                sorted_urls.append((date_key, url, lastmod))
            else:
                # For URLs without date pattern, put them at the end
                sorted_urls.append(('99999999', url, lastmod))
        except:
            sorted_urls.append(('99999999', url, lastmod))
    
    # Sort by date (chronological order)
    sorted_urls.sort(key=lambda x: x[0])
    
    # Add sorted URL entries
    for _, url, lastmod in sorted_urls:
        sitemap_lines.extend([
            '  <url>',
            f'    <loc>{url}</loc>',
            f'    <lastmod>{lastmod if lastmod else current_date}</lastmod>',
            '  </url>'
        ])
    
    # Close the urlset
    sitemap_lines.append('</urlset>')
    
    # Write sitemap to file
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sitemap_lines))
    
    print(f"Successfully generated sitemap at: {sitemap_path}")
    print(f"  Total URLs: {len(merged_urls) + 1} (including homepage)")
    print(f"  New entries: {new_count}")
    print(f"  Updated entries: {updated_count}")
    print(f"  Preserved entries: {len(existing_urls) - updated_count}")
    
    return sitemap_path


print(f"Starting program at: {datetime.now().strftime('%Y%m%d %H:%M:%S')}")
trends_data_db_name = 'trends_data.db'
res = get_trending_searches()
res_json = json.dumps(res, indent=2)
with open("trending_searches.json", "w") as file:
    file.write(res_json)
data = load_trending_searches("trending_searches.json")
save_to_database(data, trends_data_db_name)
asyncio.run(create_stories(trends_data_db_name))

# Generate sitemap after all operations complete
generate_sitemap(trends_data_db_name)