import requests
from io import BytesIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER,
    GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_TOKEN, GOOGLE_DRIVE_FOLDER_ID
)


class NextcloudClient:
    def __init__(self):
        self.base_url = NEXTCLOUD_URL
        self.username = NEXTCLOUD_USERNAME
        self.password = NEXTCLOUD_PASSWORD
        self.folder = NEXTCLOUD_FOLDER

    def upload_file(self, file_content, filename):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.put(url, data=file_content, auth=(self.username, self.password),
                                    headers={'Content-Type': 'application/octet-stream'})
            if response.status_code in [201, 204]:
                propfind_url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
                propfind_response = requests.request('PROPFIND', propfind_url, auth=(self.username, self.password),
                                                     headers={'Depth': '0'})
                file_id = propfind_response.headers.get('OC-FileId', filename)
                return file_id
            return None
        except Exception as e:
            print(f"Nextcloud upload error: {e}")
            return None

    def delete_file(self, filename):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.delete(url, auth=(self.username, self.password))
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Nextcloud delete error: {e}")
            return False

    def download_file(self, file_id_or_name):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{file_id_or_name}"
        try:
            response = requests.get(url, auth=(self.username, self.password))
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Nextcloud download error: {e}")
            return None


class GoogleDriveClient:
    def __init__(self):
        try:
            self.credentials = Credentials(
                token=GOOGLE_DRIVE_TOKEN,
                client_id=GOOGLE_DRIVE_CLIENT_ID,
                client_secret=GOOGLE_DRIVE_CLIENT_SECRET,
                token_uri='https://oauth2.googleapis.com/token',
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.folder_id = GOOGLE_DRIVE_FOLDER_ID
        except Exception as e:
            print(f"Google Drive init error: {e}")
            self.service = None

    def upload_file(self, file_content, filename, mime_type):
        if not self.service:
            return None
        try:
            file_metadata = {'name': filename, 'parents': [self.folder_id]}
            media = MediaIoBaseUpload(BytesIO(file_content), mimetype=mime_type, resumable=True)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            self.service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
            return file['id']
        except HttpError as e:
            print(f"Google Drive upload error: {e}")
            return None

    def delete_file(self, file_id):
        if not self.service:
            return False
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except HttpError as e:
            print(f"Google Drive delete error: {e}")
            return False

    def download_file(self, file_id):
        if not self.service:
            return None
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            return fh.getvalue()
        except HttpError as e:
            print(f"Google Drive download error: {e}")
            return None


def get_file_from_cloud(media):
    content = None
    content_type = 'video/mp4' if media.media_type == 'video' else 'image/jpeg'
    if media.nextcloud_file_id:
        nc = NextcloudClient()
        content = nc.download_file(media.nextcloud_file_id)
        if content:
            return content, content_type
    if media.google_drive_file_id:
        gd = GoogleDriveClient()
        content = gd.download_file(media.google_drive_file_id)
        if content:
            return content, content_type
    return None, None
