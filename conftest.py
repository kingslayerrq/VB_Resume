import pytest
import os

# We don't need sys.path.append anymore! 
# Pytest handles it because this file is in the root.

@pytest.fixture
def mock_creds():
    """Shared fixture for unit tests"""
    return {"token": "fake_token", "client_id": "fake_id"}

# You can add more shared fixtures here later (e.g. for database, browser)