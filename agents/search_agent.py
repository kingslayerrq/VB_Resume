import pandas as pd
from jobspy import scrape_jobs

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
    # The config gives us a list ['fulltime', 'internship'], but JobSpy needs a string 'fulltime'
    raw_job_types = kwargs.get('job_type', ['fulltime'])
    
    # Ensure it is always a list for our loop
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
            # We divide results_wanted by the number of types to keep the total count reasonable
            # (e.g. if you want 10 jobs and chose 2 types, we get ~5 of each)
            # But strictly speaking, grabbing 10 of each is safer to ensure we find matches.
            current_scrape: pd.DataFrame = scrape_jobs(
                site_name=sites,
                search_term=role,
                location=location,
                results_wanted=num_results, 
                offset=offset,
                hours_old=hours_old,
                country_urlpatterns={"Global": "https://www.indeed.com"},
                
                is_remote=is_remote,
                job_type=j_type, # Pass ONE string at a time
                distance=distance,
                linkedin_fetch_description=fetch_desc
            )
            
            # Append to master list
            if not current_scrape.empty:
                all_jobs_df = pd.concat([all_jobs_df, current_scrape], ignore_index=True)
                
        except Exception as e:
            print(f"    ❌ Failed searching for {j_type}: {e}")
            continue

    # Remove duplicates that might appear across different searches
    if not all_jobs_df.empty:
        all_jobs_df = all_jobs_df.drop_duplicates(subset=['job_url'])

    print(f"   🔎 Found {len(all_jobs_df)} jobs total.")

    valid_jobs = []
    # Process the combined results
    for index, row in all_jobs_df.iterrows():
        title = str(row.get('title', ''))
        company = str(row.get('company', ''))
        desc = row.get('description', '')
        url = row.get('job_url', '')
        
        # Blacklist Check
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