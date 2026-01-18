import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# UPDATE THIS LIST:
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',    # Upload files
    'https://www.googleapis.com/auth/gmail.modify'   # Read AND Mark as Read (Modify)
]

def get_google_service(api_name, api_version):
    """
    Authenticates the user and returns a specific Google API Service.
    """
    creds = None
    # Early exit if no credentials or token files exist
    if not os.path.exists('credentials.json') and not os.path.exists('token.json'):
        return None
    
    # 1. Load existing token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 2. If no valid token, Log In
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"   🔄 Refreshing Google {api_name} Token...")
            creds.refresh(Request())
        else:
            print(f"   🔑 Logging into Google for {api_name}...")
            if not os.path.exists('credentials.json'):
                print("   ❌ ERROR: 'credentials.json' not found.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the new token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        return build(api_name, api_version, credentials=creds)
    except Exception as e:
        print(f"   ❌ Failed to build Google Service ({api_name}): {e}")
        return None