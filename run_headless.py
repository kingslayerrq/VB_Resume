import asyncio
import os
import sys
import time
import argparse

# --- CRITICAL WINDOWS FIX ---
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from config_manager import load_config
from main import run_daily_workflow

# --- SIMPLE FILE LOGGER ---
def headless_logger(msg):
    """Writes logs to daily_run.log and prints to console"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    print(formatted_msg)
    
    # Append to log file
    with open("daily_run.log", "a", encoding="utf-8") as f:
        f.write(formatted_msg + "\n")

if __name__ == "__main__":
    # 1. Parse Command Line Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="user_config.json", help="Path to specific config file")
    args = parser.parse_args()
    
    # 2. Load the specific profile
    config_path = args.config
    headless_logger(f"📂 Loading Profile: {config_path}")

    # 3. Load config
    config = load_config(config_path)
    
    # 4. Check for API Key
    if not config.get('openai_key'):
        headless_logger("❌ ERROR: OpenAI API Key missing in user_config.json. Aborting.")
        sys.exit(1)
        
    os.environ["OPENAI_API_KEY"] = config['openai_key']
    
    # 5. Prepare Configuration
    scrape_conf = {
        "hours_old": config.get('hours_old', 72),
        "sites": config.get('scrape_sites', ["linkedin"]),
        "is_remote": config.get('is_remote', False),
        "job_type": config.get('job_type', ['fulltime']),
        "distance": config.get('distance', 50),
        "fetch_full_desc": config.get('fetch_full_desc', True),
        "blacklist": config.get('blacklist', [])
    }
    
    headless_logger("🚀 STARTING AUTOMATED RUN...")
    headless_logger(f"   Role: {config['role']}")
    headless_logger(f"   Location: {config['location']}")
    
    # 6. Run Workflow
    try:
        asyncio.run(run_daily_workflow(
            role=config['role'], 
            location=config['location'], 
            target_successes=config['target'],
            safety_limit=config['safety_limit'],
            enable_discord=config.get('enable_discord', True),
            scrape_config=scrape_conf,
            status_callback=headless_logger
        ))
        headless_logger("✅ AUTOMATED RUN COMPLETE.")
    except Exception as e:
        headless_logger(f"❌ CRITICAL ERROR: {e}")