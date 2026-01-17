import base64
from unittest.mock import patch, MagicMock
from services.google.gmail_job_agent import fetch_job_urls_from_gmail

@patch("services.google.gmail_job_agent.get_google_service")
def test_gmail_parsing_logic(mock_get_service):
    # Setup Mock
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    # Fake HTML and Gmail-style base64url encoding
    html = "<html><body><a href='https://www.linkedin.com/jobs/view/999999'>Apply Now</a></body></html>"
    fake_encoded_html = base64.urlsafe_b64encode(html.encode("utf-8")).decode("utf-8")

    # Mock list/get responses
    mock_service.users().messages().list.return_value.execute.return_value = {
        "messages": [{"id": "1"}]
    }
    mock_service.users().messages().get.return_value.execute.return_value = {
        "payload": {
            "mimeType": "text/html",
            "body": {"data": fake_encoded_html},
        }
    }

    # Run
    jobs = fetch_job_urls_from_gmail(max_results=1)

    # Assert
    assert len(jobs) == 1
    assert jobs[0]["company"] == "LinkedIn Import"
