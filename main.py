import os
import csv
import json
import time
import asyncio
import argparse
import re
from datetime import timedelta
import fitz  # PyMuPDF
from datetime import datetime
from agents.search_agent import search_jobs
from agents.tailor_agent import tailor_resume
from agents.layout_agent import render_resume
from agents.proofread_agent import proofread_resume
from agents.filter_agent import assess_job_suitability
from agents.notification_agent import send_start_notification, send_summary_notification

# --- CONFIGURATION ---
BASE_OUTPUT_DIR = "output"
BASE_LOG_DIR = "scraped_jobs"
HISTORY_FILE = "history.json"

# --- HISTORY MANAGER ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    except: return []

def normalize_text(text):
    if not text: return ""
    text = str(text) 
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def is_duplicate(job_url, title, company):
    history = load_history()
    norm_title = normalize_text(title)
    norm_company = normalize_text(company)
    sixty_days_ago = datetime.now() - timedelta(days=60)
    
    for entry in history:
        if entry["url"] == job_url: return True
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
        if entry_date > sixty_days_ago:
            hist_company = normalize_text(entry.get("company", ""))
            hist_title = normalize_text(entry.get("title", ""))
            if hist_company == norm_company and hist_title == norm_title:
                return True
    return False

def save_to_history(job_url, title, company, status):
    history = load_history()
    entry = {
        "url": job_url,
        "title": str(title),
        "company": str(company),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": status
    }
    history.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

# --- LOGGING HELPER ---
def log(msg, callback=None):
    """Prints to console AND sends to Streamlit if callback exists"""
    print(msg) # Terminal
    if callback:
        callback(msg) # UI

# --- SINGLE RESUME GENERATOR ---
async def generate_resume_for_job(jd_text, master_json_path, output_filename, status_callback=None):
    max_retries = 3
    current_feedback = ""
    
    # PHASE 1: CONTENT
    for attempt in range(max_retries):
        log(f"   Drafting Content (Attempt {attempt+1})...", status_callback)
        tailored_data = tailor_resume(master_json_path, jd_text, feedback=current_feedback)
        
        temp_json = "temp_tailored.json"
        with open(temp_json, "w") as f: json.dump(tailored_data, f, indent=4)
            
        await render_resume(temp_json, output_filename, scale=1.0)
        audit = proofread_resume(output_filename, jd_text)
        
        if audit['content_passed']:
            log("   ✅ Content Approved.", status_callback)
            break 
        
        log(f"   ❌ Content Feedback: {audit['feedback']}", status_callback)
        current_feedback = audit['feedback']
    else:
        log("   ⛔ SKIPPING JOB: Content generation failed.", status_callback)
        return False

    # PHASE 2: LAYOUT
    log("   📏 Optimizing Layout...", status_callback)
    for scale in [1.0, 0.95, 0.9, 0.85, 0.8]:
        await render_resume(temp_json, output_filename, scale=scale)
        doc = fitz.open(output_filename)
        if len(doc) == 1:
            log(f"   🎉 SUCCESS! Fits on 1 page (Scale {scale}).", status_callback)
            doc.close()
            return True
        doc.close()
            
    log("   ⚠️ WARNING: Saved best effort (>1 page).", status_callback)
    return True

# --- THE WORKFLOW ---
async def run_daily_workflow(role, location, target_successes, safety_limit, enable_discord, scrape_config, status_callback=None):
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_output_dir = os.path.join(BASE_OUTPUT_DIR, today_str)
    os.makedirs(daily_output_dir, exist_ok=True)
    os.makedirs(BASE_LOG_DIR, exist_ok=True)
    csv_log_path = os.path.join(BASE_LOG_DIR, f"jobs_found_{today_str}.csv")
    
    success_count = 0
    total_checked = 0
    current_offset = 0
    batch_size = 10
    processed_urls_session = set()
    successful_jobs_data = []

    # 1. NOTIFY START
    send_start_notification(role, location, target_successes, enabled=enable_discord)
    log(f"\n🎯 GOAL: Generate {target_successes} successful resumes.", status_callback)
    log(f"🛡️ Safety Limit set to {safety_limit} jobs checked.", status_callback)
    
    # --- MAIN LOOP ---
    while success_count < target_successes:
        if total_checked >= safety_limit:
            log(f"\n🛑 SAFETY LIMIT REACHED ({total_checked} jobs). Stopping.", status_callback)
            break

        log(f"\n📡 Fetching batch (Offset {current_offset})...", status_callback)
        
        job_batch = search_jobs(
            role, 
            location, 
            num_results=batch_size, 
            offset=current_offset,
            hours_old=scrape_config['hours_old'],
            sites=scrape_config['sites'],
            is_remote=scrape_config.get('is_remote'),
            job_type=scrape_config.get('job_type'),
            distance=scrape_config.get('distance'),
            fetch_full_desc=scrape_config.get('fetch_full_desc')
        )
        
        if not job_batch:
            log("⚠️ No more jobs found.", status_callback)
            break

        # Log Batch
        file_exists = os.path.isfile(csv_log_path)
        with open(csv_log_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Company", "Title", "URL", "Scraped_Date"])
            if not file_exists: writer.writeheader()
            for j in job_batch:
                writer.writerow({
                    "Company": str(j['company']), 
                    "Title": str(j['title']), 
                    "URL": j['url'], 
                    "Scraped_Date": today_str
                })

        # Process Batch
        for job in job_batch:
            if success_count >= target_successes: break

            total_checked += 1
            log(f"\n💼 Checking Job {total_checked} (Target: {success_count}/{target_successes})", status_callback)
            log(f"   {job['title']} @ {job['company']}", status_callback)

            if job['url'] in processed_urls_session: continue
            processed_urls_session.add(job['url'])

            if is_duplicate(job['url'], job['title'], job['company']):
                log("   ⏭️  Duplicate. Skipping.", status_callback)
                continue

            assessment = assess_job_suitability(job['description'], "master_resume.json")
            if not assessment.is_suitable:
                log(f"   🛑 SKIPPING: Match Score {assessment.match_score}/100", status_callback)
                save_to_history(job['url'], job['title'], job['company'], "FILTERED_OUT")
                continue 

            log(f"   ✅ MATCH! Score {assessment.match_score}/100. Generating...", status_callback)

            company_clean = "".join(c for c in str(job['company']) if c.isalnum())
            role_clean = "".join(c for c in str(job['title']) if c.isalnum())[:15]
            filename = f"Resume_{company_clean}_{role_clean}.pdf"
            output_path = os.path.join(daily_output_dir, filename)
            
            # Pass callback to generator
            success = await generate_resume_for_job(job['description'], "master_resume.json", output_path, status_callback)
            
            if success:
                log(f"   📁 SAVED: {output_path}", status_callback)
                save_to_history(job['url'], job['title'], job['company'], "GENERATED")
                success_count += 1
                successful_jobs_data.append({
                    "company": job['company'],
                    "role": job['title'],
                    "url": job['url'],
                    "pdf_path": output_path
                })
            else:
                if os.path.exists(output_path): os.remove(output_path)
                save_to_history(job['url'], job['title'], job['company'], "FAILED_CONTENT")
            
            time.sleep(2)

        if success_count >= target_successes: break
        
        current_offset += batch_size
        log(f"   ---> Fetching next batch...", status_callback)
        time.sleep(5)

    # 2. NOTIFY END
    log("\n📨 Sending Discord Summary...", status_callback)
    send_summary_notification(successful_jobs_data, enabled=enable_discord)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", type=str, default="Software Engineer")
    parser.add_argument("--location", type=str, default="New York")
    parser.add_argument("--target", type=int, default=3)
    
    args = parser.parse_args()
    # Dummy config for CLI
    scrape_conf = {"hours_old": 24, "sites": ["linkedin"]}
    asyncio.run(run_daily_workflow(args.role, args.location, args.target, 50, True, scrape_conf))