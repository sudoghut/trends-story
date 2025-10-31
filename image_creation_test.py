import json
import os
import random
import uuid
import websocket
import urllib.request
import urllib.parse
from datetime import datetime
import re

# --- Configuration ---
SERVER_ADDRESS = "127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())

# --- PROXY FIX ---
# Tell urllib to not use any proxy settings from the system
proxy_handler = urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)
urllib.request.install_opener(opener)
# --- END PROXY FIX ---

# --- Helper Functions (from your code) ---

def queue_prompt(prompt_workflow):
    """Sends the workflow to the ComfyUI server."""
    p = {"prompt": prompt_workflow, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read())
    except Exception as e:
        print(f"Error queuing prompt: {e}")
        return None

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

def sanitize_filename(filename):
    """Sanitizes a string to be a valid filename."""
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '', filename)
    sanitized = sanitized.replace(' ', '-')
    sanitized = re.sub(r'-+', '-', sanitized)
    return sanitized.strip('-')[:100]


# --- Main Image Creation Function ---

def create_image_from_prompt(prompt_text, query_for_filename):
    """
    Creates an image using ComfyUI based on a simple text prompt.
    Assumes a specific workflow.json structure.
    """
    # Load the workflow template
    try:
        with open("workflow.json", "r", encoding="utf-8") as f:
            prompt_workflow = json.load(f)
    except FileNotFoundError:
        print("Error: `workflow.json` not found. Please ensure it's in the same directory.")
        return

    # --- Modify the workflow ---
    # Set the positive prompt in node "6"
    prompt_workflow["6"]["inputs"]["text"] = prompt_text
    
    # Set a random seed in node "31" (KSampler)
    prompt_workflow["31"]["inputs"]["seed"] = random.randint(0, 999999999999999)
    
    # --- Prepare filename ---
    now = datetime.now()
    filename_prefix = f"{sanitize_filename(query_for_filename)}_{now.strftime('%Y%m%d_%H%M%S')}"
    prompt_workflow["9"]["inputs"]["filename_prefix"] = filename_prefix
    
    # --- Queue the prompt and get the image ---
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
        
        # Queue the prompt
        prompt_data = queue_prompt(prompt_workflow)
        if not prompt_data or 'prompt_id' not in prompt_data:
            print("Failed to queue prompt.")
            return

        prompt_id = prompt_data['prompt_id']
        print(f"Successfully queued prompt with ID: {prompt_id}")

        # Wait for execution to finish
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message.get('type') == 'executing' and message.get('data', {}).get('node') is None:
                    if message['data'].get('prompt_id') == prompt_id:
                        print("Execution finished.")
                        break
            
        # Get history and find the saved image
        history = get_history(prompt_id).get(prompt_id, {})
        outputs = history.get('outputs', {})
        
        for node_id in outputs:
            node_output = outputs[node_id]
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    
                    # --- MODIFIED: Save the image directly to the script's directory ---
                    final_filepath = image['filename'] 
                    with open(final_filepath, "wb") as img_file:
                        img_file.write(image_data)
                    print(f"✅ Successfully saved image to: {final_filepath}")
                    return

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        ws.close()

# --- Main execution ---
if __name__ == "__main__":
    print("Starting cat image generation test...")
    
    # Define the prompt for the image
    cat_prompt = "a cute cat, professional photograph, high quality, sharp focus"
    
    # Define a simple query for the filename
    filename_query = "cute-cat-test"
    
    # Call the function to create the image
    create_image_from_prompt(cat_prompt, filename_query)
    
    print("Test finished.")