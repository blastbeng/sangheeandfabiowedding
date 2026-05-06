from celery import shared_task
from django.core.files.base import ContentFile
import hashlib
import os
import requests
from io import BytesIO
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .models import Media, CustomUser
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER,
    GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_TOKEN, GOOGLE_DRIVE_FOLDER_ID
)


class NextcloudClient:
    """WebDAV client for Nextcloud"""

    def __init__(self):
        self.base_url = NEXTCLOUD_URL
        self.username = NEXTCLOUD_USERNAME
        self.password = NEXTCLOUD_PASSWORD
        self.folder = NEXTCLOUD_FOLDER

    def upload_file(self, file_content, filename):
        url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
        try:
            response = requests.put(
                url,
                data=file_content,
                auth=(self.username, self.password),
                headers={'Content-Type': 'application/octet-stream'}
            )
            if response.status_code in [201, 204]:
                propfind_url = f"{self.base_url}/remote.php/dav/files/{self.username}{self.folder}/{filename}"
                propfind_response = requests.request(
                    'PROPFIND',
                    propfind_url,
                    auth=(self.username, self.password),
                    headers={'Depth': '0'}
                )
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


class GoogleDriveClient:
    """Google Drive API client"""

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
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            media = MediaFileUpload(BytesIO(file_content), mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            self.service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
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


@shared_task(bind=True, max_retries=3)
def upload_media_task(self, user_id, file_data_list):
    """
    Celery task for async media upload to Nextcloud and Google Drive
    
    file_data_list: List of dicts with keys:
        - file_content: base64 encoded file content
        - filename: original filename
        - caption: file caption
        - media_type: 'image' or 'video'
    """
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return {'error': 'User not found'}

    nextcloud_client = NextcloudClient()
    google_client = GoogleDriveClient()
    
    uploaded_media = []
    errors = []

    for file_data in file_data_list:
        try:
            import base64
            file_content = base64.b64decode(file_data['file_content'])
            filename = file_data['filename']
            caption = file_data.get('caption', '')
            media_type = file_data.get('media_type', 'image')

            # Generate unique filename
            unique_filename = f"{user_id}_{hashlib.md5(filename.encode()).hexdigest()[:8]}_{filename}"
            extension = os.path.splitext(filename)[1]

            # Upload to Nextcloud FIRST
            nextcloud_id = nextcloud_client.upload_file(file_content, unique_filename)
            if not nextcloud_id:
                errors.append(f"Nextcloud upload failed for {filename}")
                continue

            # Upload to Google Drive SECOND
            mime_type = 'video/mp4' if media_type == 'video' else 'image/jpeg'
            google_id = google_client.upload_file(file_content, unique_filename, mime_type)
            if not google_id:
                # ROLLBACK: Delete from Nextcloud since Google Drive failed
                nextcloud_client.delete_file(unique_filename)
                errors.append(f"Google Drive upload failed for {filename}, Nextcloud file deleted")
                continue

            # Both uploads successful - create Media record
            media = Media.objects.create(
                user=user,
                media_type=media_type,
                caption=caption,
                status='pending',
                nextcloud_file_id=nextcloud_id,
                google_drive_file_id=google_id,
                view_count=0
            )
            uploaded_media.append({
                'id': media.id,
                'filename': filename,
                'status': media.status
            })

        except Exception as e:
            errors.append(f"Error uploading {file_data.get('filename', 'unknown')}: {str(e)}")
            # Retry logic
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60)

    return {
        'uploaded': uploaded_media,
        'errors': errors,
        'warning': 'Some files failed to upload' if errors else None
    }


@shared_task
def delete_media_task(media_id, user_id):
    """
    Celery task for async media deletion from Nextcloud, Google Drive, and Redis cache
    """
    import redis
    
    try:
        media = Media.objects.get(id=media_id, user_id=user_id)
    except Media.DoesNotExist:
        return {'error': 'Media not found'}

    nextcloud_client = NextcloudClient()
    google_client = GoogleDriveClient()
    
    # Delete from Nextcloud
    if media.nextcloud_file_id:
        nextcloud_client.delete_file(media.nextcloud_file_id)

    # Delete from Google Drive
    if media.google_drive_file_id:
        google_client.delete_file(media.google_drive_file_id)

    # Delete from Redis cache
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=False
        )
        extension = '.mp4' if media.media_type == 'video' else '.jpg'
        cache_key = f"media_cache:{media.id}{extension}"
        redis_client.delete(cache_key)
    except Exception as e:
        print(f"Redis cache delete error: {e}")

    media.delete()
    return {'message': 'File deleted successfully'}
