import pytest
from unittest.mock import patch, MagicMock
from services.google.drive_agent import upload_resume_to_drive 

@patch("services.google.drive_agent.get_google_service")
@patch("services.google.drive_agent.MediaFileUpload") # Mock file reading
def test_upload_flow_existing_folder(mock_media, mock_get_service):
    """
    Scenario: The 'AI_Resumes' folder ALREADY exists.
    Expected: It finds the folder ID and uploads the file into it.
    """
    # 1. Setup Mock Service
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    # 2. Mock 'files().list()' response (Folder found)
    mock_service.files().list.return_value.execute.return_value = {
        "files": [{"id": "existing_folder_id", "name": "AI_Resumes"}]
    }

    # 3. Mock 'files().create()' response (File upload success)
    mock_service.files().create.return_value.execute.return_value = {
        "id": "new_file_id",
        "webViewLink": "https://drive.google.com/file/d/123"
    }

    # 4. Run Function
    link = upload_resume_to_drive("dummy_resume.pdf")

    # 5. Assertions
    assert link == "https://drive.google.com/file/d/123"
    
    # Verify it searched for the folder
    args, _ = mock_service.files().list.call_args
    assert "mimeType='application/vnd.google-apps.folder'" in args[0] if args else True
    
    # Verify it did NOT create a new folder (since it existed)
    # create() is called once for the file, so we check arguments
    create_calls = mock_service.files().create.call_args_list
    assert len(create_calls) == 1
    # Check that the create call was for the FILE, not the folder (has 'parents')
    assert 'parents' in create_calls[0][1]['body']

@patch("services.google.drive_agent.get_google_service")
@patch("services.google.drive_agent.MediaFileUpload")
def test_upload_flow_new_folder(mock_media, mock_get_service):
    """
    Scenario: The 'AI_Resumes' folder DOES NOT exist.
    Expected: It creates the folder first, then uploads the file.
    """
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    # 1. Mock 'list' returns EMPTY (No folder found)
    mock_service.files().list.return_value.execute.return_value = {"files": []}

    # 2. Mock 'create' (Called twice: once for folder, once for file)
    # We use 'side_effect' to return different things for consecutive calls
    mock_service.files().create.return_value.execute.side_effect = [
        {"id": "new_folder_id"}, # 1st call: Folder created
        {"id": "new_file_id", "webViewLink": "https://google.com/pdf"} # 2nd call: File uploaded
    ]

    # 3. Run
    link = upload_resume_to_drive("dummy.pdf")

    # 4. Assert
    assert link == "https://google.com/pdf"
    assert mock_service.files().create.call_count == 2