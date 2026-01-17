import pytest
import os
from services.google.drive_agent import upload_resume_to_drive

# Skip if no credentials (avoids crashing in CI/CD)
@pytest.mark.skipif(not os.path.exists("token.json"), reason="No Google Token found")
def test_real_drive_upload():
    """
    Integration: Actually uploads a dummy file to Google Drive.
    """
    print("\n☁️ Testing Real Google Drive Upload...")

    # 1. Create a dummy file to upload
    test_filename = "test_upload_artifact.txt"
    with open(test_filename, "w") as f:
        f.write("This is a test file from VB-Resume integration tests.")

    try:
        # 2. Run the upload (Using a test folder name to keep it clean)
        link = upload_resume_to_drive(test_filename, folder_name="VB_Resume_Tests")

        # 3. Validation
        assert link is not None
        assert "drive.google.com" in link or "google.com" in link
        print(f"   ✅ Success! File uploaded to: {link}")

    finally:
        # 4. Cleanup local file
        if os.path.exists(test_filename):
            os.remove(test_filename)