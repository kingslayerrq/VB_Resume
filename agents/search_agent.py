import pandas as pd
import re
import json
from jobspy import scrape_jobs
from playwright.async_api import async_playwright

async def fetch_job_page_data(url):
    data = {"description": "", "title": None, "company": None}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            
            # --- STRATEGY 1: HIDDEN JSON DATA (Gold Standard) ---
            # LinkedIn often embeds a JSON object for SEO. We can parse this directly.
            try:
                # Find the script tag containing schema.org data
                json_handle = await page.query_selector('script[type="application/ld+json"]')
                if json_handle:
                    json_content = await json_handle.inner_text()
                    structured_data = json.loads(json_content)
                    
                    # Sometimes it's a list, sometimes a dict
                    if isinstance(structured_data, list):
                        structured_data = structured_data[0]

                    # Extract Clean Data
                    if "title" in structured_data:
                        data["title"] = structured_data["title"]
                    
                    if "hiringOrganization" in structured_data:
                        org = structured_data["hiringOrganization"]
                        if isinstance(org, dict):
                            data["company"] = org.get("name")
                        elif isinstance(org, str):
                            data["company"] = org
                            
                    print(f"   ✨ Extracted via JSON: {data['title']} @ {data['company']}")
            except Exception as e:
                print(f"   ❌ JSON extraction failed: {e}")
                # JSON extraction failed, proceed to fallback
                pass

            # --- STRATEGY 2: PAGE TITLE REGEX (Fallback) ---
            # If JSON failed, try to parse the messy title string
            if not data["title"] or not data["company"]:
                raw_title = await page.title()
                # Pattern: "Company hiring Role in Location | LinkedIn"
                match = re.search(r"(.*?) hiring (.*?) in (.*?) \| LinkedIn", raw_title)
                if match:
                    data["company"] = match.group(1).strip() # BCforward
                    data["title"] = match.group(2).strip()   # Software Engineer
                
                # Pattern: "Role at Company | LinkedIn"
                elif " at " in raw_title:
                    parts = raw_title.split(" at ")
                    data["title"] = parts[0].strip()
                    if len(parts) > 1:
                        data["company"] = parts[1].replace("| LinkedIn", "").strip()

            # --- GET DESCRIPTION ---
            try:
                # Try specific container first
                await page.wait_for_selector(".description__text", timeout=2000)
                data["description"] = await page.inner_text(".description__text")
            except Exception as e:
                print(f"   ⚠️ Specific desc selector failed: {e}")
                data["description"] = await page.inner_text("body")

        except Exception as e:
            print(f"   ⚠️ Scraping Error: {e}")
            
        await browser.close()
        return data

def search_jobs(role, location, num_results, offset=0, hours_old=72, sites=["linkedin"], **kwargs):
    """
    Enhanced search that handles multiple Job Types by running parallel scrapes.
    """
    print(f"🕵️  JobSpy Hunting (Offset {offset})...")
    
    # Extract params
    is_remote = kwargs.get('is_remote', False)
    distance = kwargs.get('distance', 50)
    fetch_desc = kwargs.get('fetch_full_desc', True)
    blacklist = kwargs.get('blacklist', [])
    
    # HANDLE MULTI-SELECT JOB TYPES
    raw_job_types = kwargs.get('job_type', ['fulltime'])
    
    if isinstance(raw_job_types, str):
        job_types_to_check = [raw_job_types]
    else:
        job_types_to_check = raw_job_types

    print(f"    Params: Remote={is_remote} | Types={job_types_to_check} | Dist={distance}m")

    all_jobs_df = pd.DataFrame()

    # --- LOOP THROUGH EACH JOB TYPE ---
    for j_type in job_types_to_check:
        print(f"    🔎 Scanning for: {j_type}...")
        try:
            current_scrape: pd.DataFrame = scrape_jobs(
                site_name=sites,
                search_term=role,
                location=location,
                results_wanted=num_results, 
                offset=offset,
                hours_old=hours_old,
                country_urlpatterns={"Global": "https://www.indeed.com"},
                
                is_remote=is_remote,
                job_type=j_type, 
                distance=distance,
                linkedin_fetch_description=fetch_desc
            )
            
            if not current_scrape.empty:
                all_jobs_df = pd.concat([all_jobs_df, current_scrape], ignore_index=True)
                
        except Exception as e:
            print(f"    ❌ Failed searching for {j_type}: {e}")
            continue

    if not all_jobs_df.empty:
        all_jobs_df = all_jobs_df.drop_duplicates(subset=['job_url'])

    print(f"   🔎 Found {len(all_jobs_df)} jobs total.")

    valid_jobs = []
    for index, row in all_jobs_df.iterrows():
        title = str(row.get('title', ''))
        company = str(row.get('company', ''))
        desc = row.get('description', '')
        url = row.get('job_url', '')
        
        if any(bad_word.lower() in title.lower() for bad_word in blacklist):
            print(f"   🗑️  Filtered Blacklisted Job: {title}")
            continue
            
        if desc and len(str(desc)) > 100:
            valid_jobs.append({
                "title": title,
                "company": company,
                "url": url,
                "description": str(desc)[:5000]
            })

    return valid_jobs