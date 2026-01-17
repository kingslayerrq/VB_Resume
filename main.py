import os
import csv
import json
import time
import asyncio
import argparse
import re
from datetime import timedelta, datetime
import fitz  # PyMuPDF

# Agents
from agents.search_agent import search_jobs, fetch_job_page_data 
from agents.tailor_agent import tailor_resume
from agents.layout_agent import render_resume
from agents.proofread_agent import proofread_resume
from agents.filter_agent import assess_job_suitability
from services.notification.notification_agent import send_start_notification, send_summary_notification
from services.google.drive_agent import upload_resume_to_drive
from services.google.gmail_job_agent import fetch_job_urls_from_gmail

# --- CONFIGURATION ---
BASE_OUTPUT_DIR = "output"
BASE_LOG_DIR = "scraped_jobs"
HISTORY_FILE = "history.json"

# --- HISTORY MANAGER ---
def load_history():
    if not os.path.exists(HISTORY_FILE): 
        return []
    try:
        with open(HISTORY_FILE, "r") as f: 
            return json.load(f)
    except Exception as e: 
        print(f"   ❌ Failed to load history: {e}")
        return []

def normalize_text(text):
    if not text: 
        return ""
    text = str(text) 
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def is_duplicate(job_url, title, company):
    history = load_history()
    norm_title = normalize_text(title)
    norm_company = normalize_text(company)
    sixty_days_ago = datetime.now() - timedelta(days=60)
    
    for entry in history:
        if entry["url"] == job_url: 
            return True
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d")
        if entry_date > sixty_days_ago:
            hist_company = normalize_text(entry.get("company", ""))
            hist_title = normalize_text(entry.get("title", ""))
            if hist_company == norm_company and hist_title == norm_title:
                return True
    return False

def save_to_history(job_url, title, company, status, drive_link=None, source=None):
    history = load_history()
    entry = {
        "url": job_url,
        "title": str(title),
        "company": str(company),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": status,
        "drive_link": drive_link,
        "source": source
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
        with open(temp_json, "w") as f: 
            json.dump(tailored_data, f, indent=4)
            
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
    # Setup Directories
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_output_dir = os.path.join(BASE_OUTPUT_DIR, today_str)
    os.makedirs(daily_output_dir, exist_ok=True)
    os.makedirs(BASE_LOG_DIR, exist_ok=True)
    csv_log_path = os.path.join(BASE_LOG_DIR, f"jobs_found_{today_str}.csv")
    
    success_count = 0
    total_checked = 0
    current_offset = 0
    batch_size = 5
    processed_urls_session = set()
    # Successful Jobs Data To Send in Notification
    successful_jobs_data = []

    # 1. NOTIFY START
    send_start_notification(role, location, target_successes, enabled=enable_discord)
    log(f"\n🎯 GOAL: Generate {target_successes} successful resumes.", status_callback)
    log("⚔️  MODE: Parallel Hunt (Email + Web)", status_callback)

    # --- MAIN LOOP ---
    while success_count < target_successes:
        if total_checked >= safety_limit:
            log(f"\n🛑 SAFETY LIMIT REACHED ({total_checked} jobs). Stopping.", status_callback)
            break

        log(f"\n📡 Fetching batch (Offset {current_offset})...", status_callback)
        
        # ==========================================================
        # 🚀 PARALLEL EXECUTION LOGIC
        # ==========================================================
        
        # 1. Define the WEB Task (Runs every loop)
        #    The Web Agent IS affected by the loop/target (it runs until we stop).
        web_task = asyncio.to_thread(
            search_jobs,
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

        # 2. Define the EMAIL Task (Runs ONLY on first loop)
        use_email = scrape_config.get('use_email', False)
        email_limit = scrape_config.get('email_max_results', 10)
        if current_offset == 0 and use_email:
            log(f"   📧 Email Scraper Active (Limit: {email_limit})", status_callback)
            email_task = asyncio.to_thread(fetch_job_urls_from_gmail, max_results=email_limit)
        else:
            # On subsequent loops, return empty list instantly (don't check email again)
            email_task = asyncio.create_task(asyncio.sleep(0, result=[]))

        # 3. Execute Both Simultaneously
        log("   ⏳ Waiting for Gmail and JobSpy...", status_callback)
        web_results, email_results = await asyncio.gather(web_task, email_task)

        # 4. Tag the Sources
        # We manually add the 'Source' key here since the agents might not return it
        for j in email_results: 
            j['Source'] = 'Email'
        for j in web_results:   
            j['Source'] = 'Web'

        # 5. Combine (Email first, usually higher quality/relevance)
        job_batch = email_results + web_results
        
        log(f"   ✅ Batch received: {len(email_results)} from Email, {len(web_results)} from Web.", status_callback)
        # ==========================================================

        if not job_batch:
            log("⚠️ No more jobs found from any source.", status_callback)
            break

        # Log Batch to CSV (We log EVERYTHING found, even if we don't process it yet)
        file_exists = os.path.isfile(csv_log_path)
        fieldnames = ["Company", "Title", "URL", "Scraped_Date", "Source"]
        with open(csv_log_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists: 
                writer.writeheader()
            for j in job_batch:
                writer.writerow({
                    "Company": str(j.get('company', 'Unknown')), 
                    "Title": str(j.get('title', 'Unknown')), 
                    "URL": j['url'], 
                    "Scraped_Date": today_str,
                    "Source": j.get('Source', 'Unknown')
                })

        # Process Batch
        for job in job_batch:
            # --- CRITICAL: STOP CONDITION ---
            # If we hit the target mid-batch, STOP EVERYTHING.
            # This prevents "recording further jobs to history" or doing extra AI work.
            if success_count >= target_successes: 
                log(f"   🎉 Target met ({success_count}/{target_successes}). Stopping early.", status_callback)
                break

            total_checked += 1
            log(f"\n💼 Checking Job {total_checked} (Target: {success_count}/{target_successes})", status_callback)
            log(f"   {job.get('title', 'Job')} @ {job.get('company', 'Company')} [{job['Source']}]", status_callback)

            if job['url'] in processed_urls_session: 
                continue
            processed_urls_session.add(job['url'])

            if is_duplicate(job['url'], job.get('title', ''), job.get('company', '')):
                log("   ⏭️  Duplicate. Skipping.", status_callback)
                continue

            # --- DEEP SCRAPE IF NEEDED ---
            is_generic_title = "Detected via Email" in job.get('title', '')
            
            if not job.get('description') or len(job.get('description', '')) < 50 or is_generic_title:
                log("   🔍 Fetching full job details...", status_callback)
                
                # Fetch Data
                scraped_data = await fetch_job_page_data(job['url'])
                
                # Update Description
                job['description'] = scraped_data.get('description', '')

                # Update Metadata (Overwrite placeholders if we found real data)
                if scraped_data.get('title'):
                    job['title'] = scraped_data['title']
                if scraped_data.get('company'):
                    job['company'] = scraped_data['company']
                
                # --- NEW STRICT VALIDATION ---
                has_desc = job.get('description') and len(job['description']) > 50
                has_title = job.get('title') and "Detected via Email" not in job['title']
                has_company = job.get('company') and "LinkedIn Import" not in job['company']

                if not (has_desc and has_title and has_company):
                    log("      ⚠️ Scrape Incomplete. Missing Metadata. Skipping.", status_callback)
                    log(f"         (Desc: {has_desc}, Title: {has_title}, Company: {has_company})", status_callback)
                    
                    # Save as failed so we don't try again
                    save_to_history(
                        job['url'], 
                        job.get('title', 'Unknown'), 
                        job.get('company', 'Unknown'), 
                        "FAILED_SCRAPE", 
                        source=job.get('Source')
                    )
                    continue
                
                log(f"      ✨ Updated Info: {job['title']} @ {job['company']}", status_callback)

            # Now that we have the REAL title, check history one last time to be safe
            if is_duplicate(job['url'], job['title'], job['company']):
                 log("   ⏭️  Duplicate Content (Found after scrape). Skipping.", status_callback)
                 save_to_history(job['url'], job['title'], job['company'], "Duplicate", source=job.get('Source'))
                 continue

            # Assessment
            assessment = assess_job_suitability(job['description'], "master_resume.json")
            if not assessment.is_suitable:
                log(f"   🛑 SKIPPING: Match Score {assessment.match_score}/100", status_callback)
                save_to_history(job['url'], job.get('title', ''), job.get('company', ''), "FILTERED_OUT", source=job['Source'])
                continue 

            log(f"   ✅ MATCH! Score {assessment.match_score}/100. Generating...", status_callback)

            # Generate Filenames & Paths
            company_clean = "".join(c for c in str(job.get('company', 'Job')) if c.isalnum())
            role_clean = "".join(c for c in str(job.get('title', 'Role')) if c.isalnum())[:15]
            filename = f"Resume_{company_clean}_{role_clean}.pdf"
            output_path = os.path.join(daily_output_dir, filename)
            
            # Tailor & Render
            success = await generate_resume_for_job(job['description'], "master_resume.json", output_path, status_callback)
            
            if success:
                log(f"   📁 SAVED: {output_path}", status_callback)
                drive_link = upload_resume_to_drive(output_path)
                
                # Save to History (Only successful ones)
                save_to_history(job['url'], job.get('title', ''), job.get('company', ''), "GENERATED", drive_link=drive_link, source=job['Source'])
                success_count += 1
                successful_jobs_data.append({
                    "company": job.get('company', 'Unknown'),
                    "role": job.get('title', 'Unknown'),
                    "url": job['url'],
                    "pdf_path": output_path,
                    "source": job['Source']
                })
            else:
                if os.path.exists(output_path): 
                    os.remove(output_path)
                save_to_history(job['url'], job.get('title', ''), job.get('company', ''), "FAILED_CONTENT", source=job['Source'])
            
            time.sleep(2)

        # Break the OUTER loop if target is met
        if success_count >= target_successes: 
            break
        
        current_offset += batch_size
        log("   ---> Fetching next batch...", status_callback)
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
    scrape_conf = {"hours_old": 24, "sites": ["linkedin"]}
    asyncio.run(run_daily_workflow(args.role, args.location, args.target, 50, True, scrape_conf))