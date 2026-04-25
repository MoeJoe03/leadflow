import sys
import asyncio
import threading
import json
import os
import glob
from fastapi import FastAPI, UploadFile, BackgroundTasks, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ig4 import start_scraper 

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    hashtags: list[str]
    limit: int

# --- THE WINDOWS PLAYWRIGHT FIX ---
# We isolate Playwright into its own thread with a fresh Windows event loop
# so it doesn't collide with FastAPI's web server loop.
def run_scraper_isolated(hashtags, limit, cookies_path):
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(start_scraper(hashtags, cookies_path, limit=limit))
    finally:
        loop.close()
# ----------------------------------

@app.post("/settings/cookies")
async def save_cookies(file: UploadFile = File(...)):
    content = await file.read()
    with open("cookies.json", "wb") as f:
        f.write(content)
    return {"status": "Cookies updated successfully"}

import sys
import asyncio
import threading

# --- THE WINDOWS PLAYWRIGHT FIX (We need this back!) ---
def run_scraper_isolated(hashtags, limit, cookies_path):
    """Runs the scraper in a completely separate thread with a fresh Windows event loop."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Calls your original ig4.py function safely
        loop.run_until_complete(start_scraper(hashtags, cookies_path, limit=limit, headless=True))
    except Exception as e:
        print(f"Scraper error: {e}")
    finally:
        loop.close()
# -------------------------------------------------------

@app.post("/scrape/start")
async def run_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    # CRITICAL: We call our isolated wrapper here, NOT start_scraper directly!
    background_tasks.add_task(
        run_scraper_isolated, 
        request.hashtags, 
        request.limit, 
        "cookies.json"
    )
    return {"message": "Scraper started"}

@app.get("/leads")
async def get_leads():
    output_dir = "output"
    if not os.path.exists(output_dir):
        return []
    
    files = glob.glob(f"{output_dir}/*.json")
    if not files: 
        return []
        
    latest_file = max(files, key=os.path.getctime)
    
    # --- ADD encoding="utf-8" RIGHT HERE ---
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading leads: {e}")
        return []