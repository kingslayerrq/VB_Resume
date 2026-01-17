import base64
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse, parse_qs
from agents.search_agent import fetch_job_page_data
from utils.google_utils import get_google_service
import asyncio


ADDRESSES = [
    "jobalerts-noreply@linkedin.com"
]

def clean_url(url):
    """
    Unwraps security redirects AND fixes LinkedIn specific paths.
    """
    # 1. Handle Proofpoint (urldefense)
    if "urldefense.proofpoint.com" in url:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'u' in query_params:
            encoded_url = query_params['u'][0]
            decoded = encoded_url.replace('-', '%').replace('_', '/')
            url = unquote(decoded)

    # 2. Fix LinkedIn "/comm/" links to allow Guest Access
    # Transforms: linkedin.com/comm/jobs/view/123 -> linkedin.com/jobs/view/123
    if "/comm/jobs/view/" in url:
        url = url.replace("/comm/jobs/view/", "/jobs/view/")

    return url


def fetch_job_urls_from_gmail(max_results=10):
    """
    Scans unread emails for 'LinkedIn Job Alert' and extracts URLs.
    max_results: Maximum number of emails to scan
    """
    # 1. Get Service via Shared Auth
    service = get_google_service('gmail', 'v1')
    if not service:
        return []

    job_list = []
    
    # 2. Query for unread emails
    query = "is:unread (" + " OR ".join(f"from:{a}" for a in ADDRESSES) + ")"
    
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            print("   📭 No new LinkedIn job emails found.")
            return []

        print(f"   📧 Found {len(messages)} new job alert emails...")

        for msg in messages:
            # Get full email data
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            
            # Decode body (Handle multipart)
            body_data = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/html':
                        body_data = part['body']['data']
                        break
            else:
                body_data = payload.get('body', {}).get('data', "")
                
            if not body_data: continue
            
            html_content = base64.urlsafe_b64decode(body_data).decode('utf-8')
            soup = BeautifulSoup(html_content, 'html.parser')

            # Find job links
            links = soup.find_all('a', href=True)
            print(f"   🔍 Scanning {len(links)} links in email...")

            seen_in_this_email = set() # Track duplicates locally

            for link in links:
                raw_url = link['href']
                clean_link = clean_url(raw_url)

                # Filter for valid Job Links
                if "/jobs/view/" in clean_link:
                    # Remove the long tracking ID (?trackingId=...) to find true duplicates
                    # This splits the URL at '?' and keeps only the first part
                    base_url = clean_link.split('?')[0]
                    
                    if base_url in seen_in_this_email:
                        continue # Skip duplicate
                    
                    seen_in_this_email.add(base_url)

                    print(f"      ✅ Found Job: {base_url[:60]}...")
                    job_list.append({
                        "url": base_url, # Save the clean URL without tracking junk
                        "title": "Detected via Email", 
                        "company": "LinkedIn Import",   
                        "description": ""               
                    })
            
            # Mark email as read
            service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()

        return job_list
        
    except Exception as e:
        print(f"   ❌ Gmail Scan Failed: {e}")
        return []
    
# For testing purposes
async def enrich_jobs_with_page_data(jobs, limit=None, concurrency=3):
    """
    For each job in jobs, fetch page data and merge it into the job dict.
    limit: only enrich first N jobs (None = all)
    concurrency: how many pages to scrape in parallel
    """
    jobs_to_process = jobs[:limit] if limit else jobs
    sem = asyncio.Semaphore(concurrency)

    async def _one(job):
        async with sem:
            page_data = await fetch_job_page_data(job["url"])
            # Merge scraped fields into the job
            job.update({
                "title": page_data.get("title") or job.get("title"),
                "company": page_data.get("company") or job.get("company"),
                "description": page_data.get("description") or job.get("description", ""),
            })
            return job

    return await asyncio.gather(*[_one(j) for j in jobs_to_process])
    
def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Scan Gmail unread job alert emails and extract LinkedIn job URLs."
    )
    parser.add_argument("--max-results", type=int, default=10, help="Max number of unread emails to scan.")
    parser.add_argument(
        "--address",
        action="append",
        dest="addresses",
        help="Add a sender email address to scan (repeatable). Example: --address jobalerts@linkedin.com"
    )
    parser.add_argument("--json", action="store_true", help="Print results as JSON.")

    # NEW: scrape/enrich flags
    parser.add_argument("--scrape", action="store_true", help="Visit each job URL and scrape title/company/description.")
    parser.add_argument("--scrape-limit", type=int, default=3, help="Only scrape first N job URLs.")
    parser.add_argument("--concurrency", type=int, default=3, help="How many pages to scrape in parallel.")

    args = parser.parse_args()

    # Override global ADDRESSES if provided via CLI
    if args.addresses:
        global ADDRESSES
        ADDRESSES = args.addresses

    jobs = fetch_job_urls_from_gmail(max_results=args.max_results)

    # NEW: enrich by scraping pages
    if args.scrape and jobs:
        enriched = asyncio.run(
            enrich_jobs_with_page_data(
                jobs,
                limit=args.scrape_limit,
                concurrency=args.concurrency
            )
        )
        # If you want, replace jobs with enriched subset:
        # jobs = enriched

        # Print page data results (enriched jobs)
        if args.json:
            print(json.dumps(enriched, indent=2))
        else:
            print(f"\nScraped {len(enriched)} job page(s):")
            for i, job in enumerate(enriched, start=1):
                print(f"{i}. {job.get('title')} @ {job.get('company')}")
                print(f"   {job.get('url')}")
                print(f"   desc_len={len(job.get('description') or '')}")
        return

    # Default: just print extracted URLs from emails
    if args.json:
        print(json.dumps(jobs, indent=2))
    else:
        print(f"\nFound {len(jobs)} job link(s).")
        for i, job in enumerate(jobs, start=1):
            print(f"{i}. {job.get('url')}")


if __name__ == "__main__":
    main()