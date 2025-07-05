# utils/drive_sync.py

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PICKLE = 'token.pickle'
CREDENTIALS_FILE = 'client_secret_753213051956-fo561q6sb1pld89vmfqhk9q7ttls8oak.apps.googleusercontent.com.json'
FOLDER_NAME = 'AK-FINANCE-APP'

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)
    service = build('drive', 'v3', credentials=creds)
    return service

def get_or_create_folder(service):
    response = service.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{FOLDER_NAME}'",
                                    spaces='drive').execute()
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
