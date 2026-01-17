import pytest
import os
from services.google.gmail_job_agent import fetch_job_urls_from_gmail

# Skip if we don't have real keys
@pytest.mark.skipif(not os.path.exists("token.json"), reason="No token found")
def test_gmail_connection_real():
    print("\n📡 Connecting to Real Gmail...")
    jobs = fetch_job_urls_from_gmail(max_results=1)
    
    # We expect a list (empty is fine, but it shouldn't crash)
    assert isinstance(jobs, list)