import logging
import redis

from celery import shared_task
from django.core.files.base import ContentFile
import hashlib
import os
import requests
import face_recognition
import numpy as np
import pickle
from PIL import Image
from io import BytesIO

from .models import Media, CustomUser, FaceTag, FaceGroup
from .cloud_clients import NextcloudClient, get_file_from_cloud
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def upload_media_task(self, user_id, file_data_list):
    """
    Celery task for async media upload to Nextcloud
    
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

            # Upload to Nextcloud
            nextcloud_id = nextcloud_client.upload_file(file_content, unique_filename)
            if not nextcloud_id:
                errors.append(f"Nextcloud upload failed for {filename} (check Nextcloud logs for details)")
                logger.error(f"Nextcloud upload failed for {filename}")
                continue

            # Create Media record – auto-approve if user is admin
            media_status = 'approved' if user.is_staff or user.is_superuser else 'pending'
            media = Media.objects.create(
                user=user,
                media_type=media_type,
                caption=caption,
                status=media_status,
                nextcloud_file_id=nextcloud_id,
                original_filename=filename,
                view_count=0
            )

            # If auto-approved, trigger face detection immediately
            if media_status == 'approved':
                detect_faces_task.delay(media.id)

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
def delete_media_task(media_id):
    """
    Celery task for async media deletion from Nextcloud and Redis cache
    """
    logger.info(f"Deleting media {media_id}")

    try:
        media = Media.objects.get(id=media_id)
    except Media.DoesNotExist:
        logger.error(f"Delete task failed: Media {media_id} not found")
        return {'error': 'Media not found'}

    nextcloud_client = NextcloudClient()
    
    # Delete from Nextcloud
    if media.nextcloud_file_id:
        nextcloud_client.delete_file(media.nextcloud_file_id)

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


@shared_task(bind=True, max_retries=3)
def detect_faces_task(self, media_id):
    try:
        media = Media.objects.get(id=media_id)
    except Media.DoesNotExist:
        return

    if media.status != 'approved':
        return

    # Download file content from cloud
    content, _ = get_file_from_cloud(media)
    if content is None:
        return

    try:
        img_array = face_recognition.load_image_file(BytesIO(content))
    except Exception as e:
        logger.error(f"Cannot load image for media {media_id}: {e}")
        return

    # Detect face locations and encodings
    try:
        face_locations = face_recognition.face_locations(img_array, model='hog')
        face_encodings = face_recognition.face_encodings(img_array, face_locations)
    except Exception as e:
        logger.error(f"Face detection failed for media {media_id}: {e}")
        return

    if not face_encodings:
        return

    # Load existing groups and their centroids
    existing_groups = FaceGroup.objects.prefetch_related('face_tags').all()
    group_centroids = {}
    for group in existing_groups:
        encodings = []
        for tag in group.face_tags.all():
            if tag.encoding:
                try:
                    enc = pickle.loads(tag.encoding)
                    encodings.append(enc)
                except Exception:
                    pass
        if encodings:
            group_centroids[group.id] = np.mean(encodings, axis=0)

    # Process each detected face
    for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
        # Extract face image
        face_image = img_array[top:bottom, left:right]
        pil_image = Image.fromarray(face_image)
        thumb_io = BytesIO()
        pil_image.save(thumb_io, format='JPEG', quality=85)
        thumb_content = thumb_io.getvalue()

        # Find closest existing group
        best_group_id = None
        min_distance = 0.6
        for group_id, centroid in group_centroids.items():
            distance = np.linalg.norm(encoding - centroid)
            if distance < min_distance:
                min_distance = distance
                best_group_id = group_id

        if best_group_id is None:
            # Create new group
            new_group = FaceGroup.objects.create()
            new_group.thumbnail.save(f'group_{new_group.id}.jpg', ContentFile(thumb_content), save=True)
            best_group_id = new_group.id
            group_centroids[best_group_id] = encoding
        else:
            # Update centroid (moving average)
            group = FaceGroup.objects.get(id=best_group_id)
            old_centroid = group_centroids[best_group_id]
            count = group.face_tags.count()
            new_centroid = (old_centroid * count + encoding) / (count + 1)
            group_centroids[best_group_id] = new_centroid

        # Create FaceTag
        face_tag = FaceTag.objects.create(
            media=media,
            face_group_id=best_group_id,
            encoding=pickle.dumps(encoding),
        )
        face_tag.thumbnail.save(f'face_{face_tag.id}.jpg', ContentFile(thumb_content), save=True)

    # Ensure every group has a thumbnail
    for group in FaceGroup.objects.filter(thumbnail=''):
        first_tag = group.face_tags.first()
        if first_tag and first_tag.thumbnail:
            group.thumbnail = first_tag.thumbnail
            group.save()
