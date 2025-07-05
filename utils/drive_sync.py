
# utils/drive_sync.py

import os
import pickle
import json
import tempfile
import io
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# Google Drive API settings
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PICKLE = 'token.pickle'
FOLDER_NAME = 'AK-FINANCE-APP'

def get_credentials_file_from_secrets():
    """Create a temporary credentials file from Streamlit secrets."""
    secret_data = {
        "installed": {
            "client_id": st.secrets["google"]["client_id"],
            "client_secret": st.secrets["google"]["client_secret"],
            "redirect_uris": st.secrets["google"]["redirect_uris"],
            "auth_uri": st.secrets["google"]["auth_uri"],
            "token_uri": st.secrets["google"]["token_uri"]
        }
    }
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with open(temp.name, "w") as f:
        json.dump(secret_data, f)
    return temp.name

def get_drive_service():
    """Authenticate and return the Google Drive service."""
    creds = None

    # Use existing credentials if available
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)

    # Authenticate if needed
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            get_credentials_file_from_secrets(), SCOPES
        )

        # Use console login on Streamlit Cloud
        if st.secrets.get("streamlit_cloud", False):
            creds = flow.run_console()
        else:
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service):
    """Get or create the designated folder in Google Drive."""
    response = service.files().list(
        q=f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}'",
        spaces='drive'
    ).execute()
    folders = response.get('files', [])
    if folders:
        return folders[0]['id']

    file_metadata = {
        'name': FOLDER_NAME,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_to_drive(file_path):
    """Upload a file to Google Drive into the designated folder."""
    service = get_drive_service()
    folder_id = get_or_create_folder(service)
    file_name = os.path.basename(file_path)
    query = f"name='{file_name}' and '{folder_id}' in parents"
    result = service.files().list(q=query, spaces='drive').execute()
    files = result.get('files', [])
    media = MediaFileUpload(file_path, resumable=True)

    if files:
        file_id = files[0]['id']
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def download_from_drive(file_path):
    """Download a file from Google Drive if it exists in the designated folder."""
    service = get_drive_service()
    folder_id = get_or_create_folder(service)
    file_name = os.path.basename(file_path)
    query = f"name='{file_name}' and '{folder_id}' in parents"
    result = service.files().list(q=query, spaces='drive').execute()
    files = result.get('files', [])

    if not files:
        return

    file_id = files[0]['id']
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
