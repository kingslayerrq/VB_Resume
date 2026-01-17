import os
from googleapiclient.http import MediaFileUpload
from utils.google_utils import get_google_service 

def upload_resume_to_drive(file_path, folder_name="AI_Resumes"):
    """Uploads a PDF to a specific folder in Google Drive."""
    
    # 1. Get Service via Shared Auth
    service = get_google_service('drive', 'v3')
    if not service:
        return None

    file_name = os.path.basename(file_path)

    try:
        # 2. Check/Create Folder
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(q=query, spaces='drive').execute()
        items = results.get('files', [])

        if not items:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"   📁 Created Drive Folder: {folder_name}")
        else:
            folder_id = items[0]['id']

        # 3. Upload File
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        print(f"   ☁️  Uploaded to Drive: {file.get('webViewLink')}")
        return file.get('webViewLink')

    except Exception as e:
        print(f"   ❌ Drive Upload Failed: {e}")
        return None