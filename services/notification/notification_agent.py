import requests
import json
import os
from config_manager import load_config

def get_webhook():
    config = load_config()
    return config.get("discord_webhook", "")

def send_start_notification(role, location, target, enabled=True): 
    if not enabled: 
        return
    
    url = get_webhook()
    if not url: 
        return

    embed = {
        "title": "🚀 Resume Factory Started",
        "color": 3447003,
        "fields": [
            {"name": "Role", "value": role, "inline": True},
            {"name": "Location", "value": location, "inline": True},
            {"name": "Target", "value": str(target), "inline": True}
        ]
    }
    try:
        requests.post(url, json={"embeds": [embed]})
    except Exception: 
        pass

def send_summary_notification(successful_jobs, enabled=True): 
    if not enabled: 
        return 

    url = get_webhook()
    if not url: 
        return

    if not successful_jobs:
        requests.post(url, json={"content": "⚠️ Workflow finished. 0 Resumes generated."})
        return

    # 1. Create Text Summary
    description = "**Job Applications Ready:**\n"
    for job in successful_jobs:
        description += f"✅ **{job['company']}** - {job['role']}\n[View Job Post]({job['url']})\n\n"

    embed = {
        "title": "🎉 Daily Workflow Complete",
        "description": description,
        "color": 5763719,
        "footer": {"text": f"Generated {len(successful_jobs)} PDFs"}
    }

    files = {}
    opened_files = []
    
    try:
        for i, job in enumerate(successful_jobs):
            path = job['pdf_path']
            if os.path.exists(path):
                f = open(path, 'rb')
                opened_files.append(f)
                files[f'file{i}'] = (os.path.basename(path), f, 'application/pdf')

        payload = {"embeds": [embed]}
        requests.post(url, data={"payload_json": json.dumps(payload)}, files=files)
        print("📨 Discord Notification Sent with Files!")

    except Exception as e:
        print(f"❌ Failed to send Discord summary: {e}")
    finally:
        for f in opened_files:
            f.close()