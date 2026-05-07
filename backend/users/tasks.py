import logging

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
from .cloud_clients import NextcloudClient, GoogleDriveClient
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER,
    GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_TOKEN, GOOGLE_DRIVE_FOLDER_ID
)

logger = logging.getLogger(__name__)


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
        logger.error(f"Upload task failed: User {user_id} not found")
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

            logger.info(f"Uploading file {filename} for user {user_id}")

            # Generate unique filename
            unique_filename = f"{user_id}_{hashlib.md5(filename.encode()).hexdigest()[:8]}_{filename}"
            extension = os.path.splitext(filename)[1]

            # Upload to Nextcloud FIRST
            nextcloud_id = nextcloud_client.upload_file(file_content, unique_filename)
            if not nextcloud_id:
                errors.append(f"Nextcloud upload failed for {filename}")
                logger.error(f"Nextcloud upload failed for {filename}")
                continue

            # Upload to Google Drive SECOND
            mime_type = 'video/mp4' if media_type == 'video' else 'image/jpeg'
            google_id = google_client.upload_file(file_content, unique_filename, mime_type)
            if not google_id:
                # ROLLBACK: Delete from Nextcloud since Google Drive failed
                nextcloud_client.delete_file(unique_filename)
                errors.append(f"Google Drive upload failed for {filename}, Nextcloud file deleted")
                logger.error(f"Google Drive upload failed for {filename}, Nextcloud file rolled back")
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
            logger.info(f"File {filename} uploaded successfully")

        except Exception as e:
            errors.append(f"Error uploading {file_data.get('filename', 'unknown')}: {str(e)}")
            logger.error(f"Upload failed for {file_data.get('filename', 'unknown')}: {e}")
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
    
    logger.info(f"Deleting media {media_id}")

    try:
        media = Media.objects.get(id=media_id, user_id=user_id)
    except Media.DoesNotExist:
        logger.error(f"Delete task failed: Media {media_id} not found")
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
        cache_key = f"media_cache:{media.id}"
        redis_client.delete(cache_key)
    except Exception as e:
        logger.error(f"Redis cache delete error: {e}")

    media.delete()
    logger.info(f"Media {media_id} deleted successfully")
    return {'message': 'File deleted successfully'}
