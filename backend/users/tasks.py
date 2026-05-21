import logging
import redis

from celery import shared_task
from collections import defaultdict, deque
from django.core.files.base import ContentFile
from django.db.models import Count, Q
import hashlib
import os
import math
import random
import requests
import cv2
import face_recognition
import mediapipe as mp
import numpy as np
import pickle
from PIL import Image, ImageOps
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor

from .models import Media, CustomUser, FaceTag, FaceGroup, WeddingBook
from .cloud_clients import NextcloudClient, get_file_from_cloud
from .wedding_book_utils import generate_english_caption, translate_text, unload_models, auto_select_media
from django.conf import settings as django_settings
from config.settings import (
    NEXTCLOUD_URL, NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD, NEXTCLOUD_FOLDER
)

logger = logging.getLogger(__name__)


def _iou(boxA, boxB):
    """Intersection over Union for two boxes in (top, right, bottom, left) format."""
    # Determine intersection rectangle
    xA = max(boxA[3], boxB[3])          # left
    yA = max(boxA[0], boxB[0])          # top
    xB = min(boxA[1], boxB[1])          # right
    yB = min(boxA[2], boxB[2])          # bottom

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = (boxA[1] - boxA[3]) * (boxA[2] - boxA[0])
    boxBArea = (boxB[1] - boxB[3]) * (boxB[2] - boxB[0])
    return interArea / float(boxAArea + boxBArea - interArea)


def _nms(boxes, threshold=0.5):
    """Simple non-maximum suppression on a list of (top, right, bottom, left) boxes."""
    if not boxes:
        return []
    # Sort by area descending (largest first)
    boxes = sorted(boxes, key=lambda b: (b[1]-b[3])*(b[2]-b[0]), reverse=True)
    keep = []
    while boxes:
        current = boxes.pop(0)
        keep.append(current)
        boxes = [b for b in boxes if _iou(current, b) < threshold]
    return keep


def _is_blurry(face_image, threshold=30.0):
    """Return True if the face image is too blurry to produce a reliable encoding."""
    gray = cv2.cvtColor(face_image, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var < threshold


def _align_face(image_array, top, right, bottom, left, target_size=256, landmarks=None):
    """
    Align a face so the eyes are horizontal, then crop and resize.
    Returns an aligned face image (numpy array) or None if alignment fails.
    If landmarks are provided, they are used; otherwise computed.
    Handles upside-down faces by rotating 180°.
    """
    try:
        if landmarks is None:
            landmarks_list = face_recognition.face_landmarks(
                image_array, [(top, right, bottom, left)]
            )
            if not landmarks_list:
                return None
            landmarks = landmarks_list[0]

        left_eye = np.mean(landmarks['left_eye'], axis=0)
        right_eye = np.mean(landmarks['right_eye'], axis=0)

        # Detect upside-down face: nose tip should be below eyes (y larger)
        eye_center_y = (left_eye[1] + right_eye[1]) / 2
        nose_tip = np.mean(landmarks['nose_tip'], axis=0)
        upside_down = nose_tip[1] < eye_center_y

        # Compute angle between eyes
        dY = right_eye[1] - left_eye[1]
        dX = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dY, dX))

        # Desired position of eyes in the aligned image
        desired_left_eye = (0.35, 0.35)
        desired_right_eye = (0.65, 0.35)

        if upside_down:
            # angle already ~180° for upside-down faces; just swap desired positions
            desired_left_eye, desired_right_eye = desired_right_eye, desired_left_eye

        desired_dist = desired_right_eye[0] - desired_left_eye[0]
        dist = np.sqrt(dX**2 + dY**2)
        scale = desired_dist * target_size / dist

        # Center between eyes
        eyes_center = ((left_eye[0] + right_eye[0]) / 2,
                       (left_eye[1] + right_eye[1]) / 2)

        # Rotation matrix
        M = cv2.getRotationMatrix2D(eyes_center, angle, scale)
        # Adjust translation so eyes land at desired positions
        tX = target_size * 0.5 - eyes_center[0]
        tY = target_size * desired_left_eye[1] - eyes_center[1]
        M[0, 2] += tX
        M[1, 2] += tY

        aligned = cv2.warpAffine(image_array, M, (target_size, target_size),
                                 flags=cv2.INTER_CUBIC)
        return aligned
    except Exception as e:
        logger.error(f"[_align_face] Alignment failed: {e}", exc_info=True)
        return None


def _detect_faces_robust(img_array):
    """
    Detect faces using MediaPipe first, then HOG fallback,
    then rotation fallback. Returns list of (top, right, bottom, left)
    in dlib order.
    """
    h, w = img_array.shape[:2]
    face_locations = []

    # --- Stage 1: MediaPipe with low confidence ---
    try:
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.2
        ) as face_detection:
            results = face_detection.process(img_array)
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                xmin = int(bbox.xmin * w)
                ymin = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                # Expand box by 10%
                expand_w = int(width * 0.1)
                expand_h = int(height * 0.1)
                xmin = max(0, xmin - expand_w)
                ymin = max(0, ymin - expand_h)
                xmax = min(w, xmin + width + 2 * expand_w)
                ymax = min(h, ymin + height + 2 * expand_h)
                if (xmax - xmin) >= 20 and (ymax - ymin) >= 20:
                    face_locations.append((ymin, xmax, ymax, xmin))
    except Exception as e:
        logger.warning(f"[detect_faces] MediaPipe failed: {e}")

    # --- Stage 2: HOG fallback if MediaPipe found nothing ---
    if not face_locations:
        try:
            hog_locations = face_recognition.face_locations(
                img_array, number_of_times_to_upsample=1, model="hog"
            )
            # Filter tiny faces
            face_locations = [
                loc for loc in hog_locations
                if (loc[2] - loc[0]) >= 20 and (loc[1] - loc[3]) >= 20
            ]
        except Exception as e:
            logger.warning(f"[detect_faces] HOG fallback failed: {e}")

    # --- Stage 3: Rotation fallback (90°, 180°, 270°) ---
    if not face_locations:
        for angle in [90, 180, 270]:
            if angle == 90:
                rotated = cv2.rotate(img_array, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                rotated = cv2.rotate(img_array, cv2.ROTATE_180)
            else:
                rotated = cv2.rotate(img_array, cv2.ROTATE_90_COUNTERCLOCKWISE)
            try:
                with mp.solutions.face_detection.FaceDetection(
                    model_selection=1, min_detection_confidence=0.2
                ) as face_detection:
                    results = face_detection.process(rotated)
                if results.detections:
                    rh, rw = rotated.shape[:2]
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        xmin = int(bbox.xmin * rw)
                        ymin = int(bbox.ymin * rh)
                        width = int(bbox.width * rw)
                        height = int(bbox.height * rh)
                        # Map back to original coordinates
                        if angle == 90:
                            orig_xmin = ymin
                            orig_ymin = h - 1 - (xmin + width)
                            orig_xmax = ymin + height
                            orig_ymax = h - 1 - xmin
                        elif angle == 180:
                            orig_xmin = w - 1 - (xmin + width)
                            orig_ymin = h - 1 - (ymin + height)
                            orig_xmax = w - 1 - xmin
                            orig_ymax = h - 1 - ymin
                        else:  # 270
                            orig_xmin = w - 1 - (ymin + height)
                            orig_ymin = xmin
                            orig_xmax = w - 1 - ymin
                            orig_ymax = xmin + width
                        # Expand and clamp
                        expand_w = int((orig_xmax - orig_xmin) * 0.1)
                        expand_h = int((orig_ymax - orig_ymin) * 0.1)
                        orig_xmin = max(0, orig_xmin - expand_w)
                        orig_ymin = max(0, orig_ymin - expand_h)
                        orig_xmax = min(w, orig_xmax + expand_w)
                        orig_ymax = min(h, orig_ymax + expand_h)
                        if (orig_xmax - orig_xmin) >= 20 and (orig_ymax - orig_ymin) >= 20:
                            face_locations.append((orig_ymin, orig_xmax, orig_ymax, orig_xmin))
                    break  # stop after first successful rotation
            except Exception as e:
                logger.warning(f"[detect_faces] Rotation {angle}° failed: {e}")

    # Deduplicate overlapping boxes (simple NMS)
    if len(face_locations) > 1:
        face_locations = _nms(face_locations, threshold=0.3)

    return face_locations


@shared_task(bind=True, max_retries=3)
def upload_media_task(self, user_id, file_paths):
    """
    Celery task for async media upload to Nextcloud.

    file_paths: List of dicts with keys:
        - tmp_path: absolute path to the temporary uploaded file
        - original_filename: original filename
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

    for file_data in file_paths:
        tmp_path = file_data['tmp_path']
        original_filename = file_data['original_filename']
        caption = file_data.get('caption', '')
        media_type = file_data.get('media_type', 'image')

        try:
            # Read the file from the temporary location
            with open(tmp_path, 'rb') as f:
                file_content = f.read()

            # Compute content hash for deduplication
            content_hash = hashlib.sha256(file_content).hexdigest()

            logger.info(f"Uploading file {original_filename} for user {user_id}")

            # Generate unique filename for Nextcloud
            unique_filename = f"{user_id}_{hashlib.md5(original_filename.encode()).hexdigest()[:8]}_{original_filename}"

            # Upload to Nextcloud
            nextcloud_id = nextcloud_client.upload_file(file_content, unique_filename)
            if not nextcloud_id:
                errors.append(f"Nextcloud upload failed for {original_filename} (check Nextcloud logs for details)")
                logger.error(f"Nextcloud upload failed for {original_filename}")
                continue

            # Create Media record – auto-approve if user is admin
            media_status = 'approved' if user.is_staff or user.is_superuser else 'pending'
            media = Media.objects.create(
                user=user,
                media_type=media_type,
                caption=caption,
                status=media_status,
                nextcloud_file_id=nextcloud_id,
                original_filename=original_filename,
                view_count=0,
                content_hash=content_hash,
            )

            # If auto-approved, trigger face detection immediately
            if media_status == 'approved':
                detect_faces_task.delay(media.id)

            uploaded_media.append({
                'id': media.id,
                'filename': original_filename,
                'status': media_status
            })
            logger.info(f"File {original_filename} uploaded successfully")

        except Exception as e:
            errors.append(f"Error uploading {original_filename}: {str(e)}")
            logger.error(f"Upload failed for {original_filename}: {e}")
            # Retry logic
            if self.request.retries < self.max_retries:
                raise self.retry(exc=e, countdown=60)
        finally:
            # Always delete the temporary file
            try:
                os.remove(tmp_path)
            except OSError:
                pass

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

    # Clean up any FaceGroups that are now empty
    empty_groups = FaceGroup.objects.annotate(
        tag_count=Count('face_tags')
    ).filter(tag_count=0)
    for group in empty_groups:
        if group.thumbnail:
            group.thumbnail.delete(save=False)
        group.delete()
        logger.info(f"Deleted empty FaceGroup {group.id}")

    return {'message': 'File deleted successfully'}


@shared_task(bind=True, max_retries=3)
def detect_faces_task(self, media_id, force=False):
    logger.info(f"[detect_faces] Called with media_id={media_id}, force={force}")

    from django.db import transaction

    try:
        with transaction.atomic():
            media = Media.objects.select_for_update().get(id=media_id)

            if force:
                # Clear existing face tags and reset the attempted flag
                media.face_tags.all().delete()
                media.face_detection_attempted = False
                media.save(update_fields=['face_detection_attempted'])

            if not force:
                if media.status != 'approved':
                    logger.info(f"[detect_faces] Skipping media {media_id}: status is '{media.status}', not 'approved'")
                    return

                if media.media_type != 'image':
                    logger.info(f"[detect_faces] Skipping media {media_id}: media_type is '{media.media_type}', not 'image'")
                    return

                if media.face_detection_attempted:
                    logger.info(f"[detect_faces] Skipping media {media_id}: face_detection_attempted is already True")
                    return
            else:
                if media.media_type != 'image':
                    logger.info(f"[detect_faces] Skipping media {media_id}: media_type is '{media.media_type}', not 'image'")
                    return
    except Media.DoesNotExist:
        logger.warning(f"[detect_faces] Media {media_id} not found, skipping")
        return

    # Download file content from cloud
    content, _ = get_file_from_cloud(media)
    if content is None:
        # Fallback to local file storage
        if media.file and media.file.storage.exists(media.file.name):
            try:
                with media.file.open('rb') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"[detect_faces] Local file read failed for media {media_id}: {e}")
                return
        else:
            logger.warning(f"[detect_faces] No content available for media {media_id} (cloud and local both returned None)")
            return

    logger.info(f"[detect_faces] Downloaded content for media {media_id} ({len(content)} bytes)")

    # Load image with PIL and convert to RGB numpy array, applying EXIF orientation
    try:
        pil_image = ImageOps.exif_transpose(Image.open(BytesIO(content))).convert('RGB')
        img_array = np.array(pil_image)
    except Exception as e:
        logger.error(f"[detect_faces] Cannot load image for media {media_id}: {e}")
        return

    # Use robust multi-stage face detection (MediaPipe → HOG → rotation fallback)
    face_locations = _detect_faces_robust(img_array)

    if not face_locations:
        logger.info(f"[detect_faces] No faces detected in media {media_id}")
        media.face_detection_attempted = True
        media.save(update_fields=['face_detection_attempted'])
        return

    logger.info(f"[detect_faces] Found {len(face_locations)} face(s) in media {media_id}")

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

    # First pass: compute encodings, thumbnails, and initial group assignments
    face_data = []
    for (top, right, bottom, left) in face_locations:
        # Get landmarks for this face (used for alignment and upside-down detection)
        landmarks_list = face_recognition.face_landmarks(img_array, [(top, right, bottom, left)])
        landmarks = landmarks_list[0] if landmarks_list else None
        upside_down = False
        if landmarks:
            left_eye = np.mean(landmarks['left_eye'], axis=0)
            right_eye = np.mean(landmarks['right_eye'], axis=0)
            eye_center_y = (left_eye[1] + right_eye[1]) / 2
            nose_tip = np.mean(landmarks['nose_tip'], axis=0)
            upside_down = nose_tip[1] < eye_center_y

        # Align face (for better encoding and thumbnail)
        aligned_face = _align_face(img_array, top, right, bottom, left, landmarks=landmarks)
        use_aligned = False
        if aligned_face is not None:
            aligned_face_uint8 = (aligned_face * 255).astype(np.uint8) if aligned_face.dtype == np.float64 else aligned_face
            encoding_result = face_recognition.face_encodings(aligned_face_uint8, model="large")
            if encoding_result:
                use_aligned = True
            else:
                logger.debug(f"[detect_faces] Aligned face encoding failed for media {media_id}, falling back to original crop")

        if use_aligned:
            face_for_quality = aligned_face_uint8
            encoding = encoding_result[0]
            pil_thumb = Image.fromarray(aligned_face_uint8)
        else:
            # Fallback: use original image with known location
            encoding_result = face_recognition.face_encodings(
                img_array,
                known_face_locations=[(top, right, bottom, left)],
                model="large"
            )
            if not encoding_result:
                logger.warning(f"[detect_faces] No encoding generated for face in media {media_id}")
                continue
            encoding = encoding_result[0]
            # Use raw crop for thumbnail
            face_crop = img_array[top:bottom, left:right]
            if face_crop.size == 0:
                continue
            # Rotate crop if face is upside down
            if upside_down:
                face_crop = cv2.rotate(face_crop, cv2.ROTATE_180)
            face_for_quality = face_crop
            thumb_face = cv2.resize(face_crop, (160, 160))
            pil_thumb = Image.fromarray(thumb_face)

        # Blur check – skip low-quality faces that produce unreliable encodings
        if _is_blurry(face_for_quality, threshold=20.0):
            logger.info(f"[detect_faces] Skipping blurry face in media {media_id}")
            continue

        # Create thumbnail content
        thumb_io = BytesIO()
        pil_thumb.save(thumb_io, format='JPEG', quality=85)
        thumb_content = thumb_io.getvalue()

        # Initialize group matching variables
        best_group_id = None
        min_distance = 0.6   # single relaxed threshold

        # General search: find closest existing group
        for group_id, centroid in group_centroids.items():
            distance = np.linalg.norm(encoding - centroid)
            if distance < min_distance:
                min_distance = distance
                best_group_id = group_id

        # No margin check – accept the closest group if below threshold
        if best_group_id is not None and min_distance >= 0.6:
            best_group_id = None   # closest is still too far

        if best_group_id is None:
            # Create new group
            new_group = FaceGroup.objects.create()
            new_group.thumbnail.save(f'group_{new_group.id}.jpg', ContentFile(thumb_content), save=True)
            best_group_id = new_group.id
            group_centroids[best_group_id] = encoding
        else:
            # Update centroid (moving average)
            group = FaceGroup.objects.get(id=best_group_id)
            old_centroid = group_centroids.get(best_group_id, encoding)
            count = group.face_tags.count()
            new_centroid = (old_centroid * count + encoding) / (count + 1)
            group_centroids[best_group_id] = new_centroid

        face_data.append({
            'encoding': encoding,
            'group_id': best_group_id,
            'thumb_content': thumb_content,
        })

    # Second pass: immediate deduplication within the same media
    # If two faces in the same photo are very close, force them into the same group
    for i in range(len(face_data)):
        for j in range(i + 1, len(face_data)):
            dist = np.linalg.norm(face_data[i]['encoding'] - face_data[j]['encoding'])
            if dist < 0.5:
                gid_i = face_data[i]['group_id']
                gid_j = face_data[j]['group_id']
                if gid_i != gid_j:
                    # Choose the group with more existing FaceTags (or lower ID if equal)
                    count_i = FaceTag.objects.filter(face_group_id=gid_i).count()
                    count_j = FaceTag.objects.filter(face_group_id=gid_j).count()
                    if count_i >= count_j:
                        face_data[j]['group_id'] = gid_i
                    else:
                        face_data[i]['group_id'] = gid_j

    # Third pass: create FaceTags
    faces_created = 0
    for fd in face_data:
        best_group_id = fd['group_id']
        thumb_content = fd['thumb_content']

        # Ensure the face group has a thumbnail (for groups created before this fix)
        if best_group_id:
            group = FaceGroup.objects.get(id=best_group_id)
            if not group.thumbnail:
                group.thumbnail.save(f'group_{group.id}.jpg', ContentFile(thumb_content), save=True)

        # Avoid creating a duplicate FaceTag for the same media and group
        if FaceTag.objects.filter(media=media, face_group_id=best_group_id).exists():
            logger.info(f"[detect_faces] FaceTag already exists for media {media_id} and group {best_group_id}, skipping")
            continue

        # Create FaceTag
        face_tag = FaceTag.objects.create(
            media=media,
            face_group_id=best_group_id,
            encoding=pickle.dumps(fd['encoding']),
        )
        face_tag.thumbnail.save(f'face_{face_tag.id}.jpg', ContentFile(thumb_content), save=True)
        faces_created += 1

    # Ensure every group has a thumbnail
    from django.db.models import Q
    for group in FaceGroup.objects.filter(Q(thumbnail__isnull=True) | Q(thumbnail='')):
        first_tag = group.face_tags.first()
        if first_tag and first_tag.thumbnail:
            group.thumbnail = first_tag.thumbnail
            group.save()

    # Mark media as attempted
    media.face_detection_attempted = True
    media.save(update_fields=['face_detection_attempted'])

    logger.info(f"[detect_faces] Completed for media {media_id}: created {faces_created} face tag(s)")


@shared_task
def backfill_faces_periodic():
    """
    Periodic task: queue face detection for all approved images
    that have not been attempted yet, and also fix face groups
    that have missing thumbnails.
    """
    from .models import Media, FaceGroup
    from django.db.models import Q

    # 1. Standard backfill: images never attempted
    eligible = Media.objects.filter(
        status='approved',
        media_type='image',
        face_detection_attempted=False
    )
    count = 0
    for media in eligible:
        detect_faces_task.delay(media.id)
        count += 1

    # 2. Fix missing group thumbnails without deleting tags
    broken_groups = FaceGroup.objects.filter(
        Q(thumbnail__isnull=True) | Q(thumbnail='')
    ).filter(face_tags__isnull=False).distinct()

    for group in broken_groups:
        first_tag = group.face_tags.first()
        if first_tag and first_tag.thumbnail:
            group.thumbnail = first_tag.thumbnail
            group.save()
            logger.info(f'[backfill] Fixed missing thumbnail for group {group.id}')

    if count > 0:
        logger.info(f'[backfill] Queued face detection for {count} media items.')
    else:
        logger.debug('[backfill] No eligible media items found for face detection.')
    return count


@shared_task
def cleanup_empty_face_groups():
    empty_groups = FaceGroup.objects.annotate(
        tag_count=Count('face_tags')
    ).filter(tag_count=0)
    count = 0
    for group in empty_groups:
        if group.thumbnail:
            group.thumbnail.delete(save=False)
        group.delete()
        count += 1
    if count:
        logger.info(f"Cleaned up {count} empty FaceGroups")
    return count


@shared_task
def backfill_content_hashes():
    """
    Backfill content_hash for all Media objects that don't have one.
    Computes SHA-256 hash of the file content and stores it in the
    content_hash field for deduplication purposes.
    """
    media_without_hash = Media.objects.filter(
        Q(content_hash__isnull=True) | Q(content_hash='')
    )

    count = 0
    for media in media_without_hash:
        content, _ = get_file_from_cloud(media)
        if content is None:
            # Fallback to local file storage
            if media.file and media.file.storage.exists(media.file.name):
                try:
                    with media.file.open('rb') as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"[backfill_content_hashes] Cannot read file for media {media.id}: {e}")
                    continue
            else:
                logger.warning(f"[backfill_content_hashes] No content available for media {media.id}")
                continue

        content_hash = hashlib.sha256(content).hexdigest()
        media.content_hash = content_hash
        media.save(update_fields=['content_hash'])
        count += 1

    if count > 0:
        logger.info(f"[backfill_content_hashes] Backfilled {count} media items with content hashes")
    else:
        logger.debug("[backfill_content_hashes] No media items needed content hash backfill")
    return count


@shared_task(bind=True, max_retries=3)
def detect_faces_profile_picture(self, user_id):
    from .models import CustomUser, FaceGroup
    from django.core.files.base import ContentFile
    import face_recognition
    import mediapipe as mp
    import numpy as np
    import pickle
    from PIL import Image, ImageOps
    from io import BytesIO

    logger.info(f"[detect_faces_profile] Starting for user {user_id}")

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        logger.warning(f"[detect_faces_profile] User {user_id} not found")
        return

    if not user.profile_picture or user.profile_picture.name == 'profile_pics/default.png':
        logger.info(f"[detect_faces_profile] User {user_id} has no custom profile picture")
        return

    # Read profile picture
    try:
        with user.profile_picture.open('rb') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"[detect_faces_profile] Cannot read profile picture for user {user_id}: {e}")
        return

    # Load image, applying EXIF orientation
    try:
        pil_image = ImageOps.exif_transpose(Image.open(BytesIO(content))).convert('RGB')
        img_array = np.array(pil_image)
    except Exception as e:
        logger.error(f"[detect_faces_profile] Cannot load image for user {user_id}: {e}")
        return

    # Detect faces with MediaPipe
    try:
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.3
        ) as face_detection:
            results = face_detection.process(img_array)
    except Exception as e:
        logger.error(f"[detect_faces_profile] MediaPipe failed for user {user_id}: {e}")
        return

    if not results.detections:
        logger.info(f"[detect_faces_profile] No face detected for user {user_id}")
        return

    # Use the first detected face
    detection = results.detections[0]
    bbox = detection.location_data.relative_bounding_box
    h, w, _ = img_array.shape
    xmin = int(bbox.xmin * w)
    ymin = int(bbox.ymin * h)
    width = int(bbox.width * w)
    height = int(bbox.height * h)

    # Expand box by 10%
    expand_w = int(width * 0.1)
    expand_h = int(height * 0.1)
    xmin = max(0, xmin - expand_w)
    ymin = max(0, ymin - expand_h)
    xmax = min(w, xmin + width + 2 * expand_w)
    ymax = min(h, ymin + height + 2 * expand_h)

    if (xmax - xmin) < 20 or (ymax - ymin) < 20:
        logger.info(f"[detect_faces_profile] Face too small for user {user_id}")
        return

    face_location = (ymin, xmax, ymax, xmin)

    # Get landmarks for this face
    landmarks_list = face_recognition.face_landmarks(img_array, [face_location])
    landmarks = landmarks_list[0] if landmarks_list else None
    upside_down = False
    if landmarks:
        left_eye = np.mean(landmarks['left_eye'], axis=0)
        right_eye = np.mean(landmarks['right_eye'], axis=0)
        eye_center_y = (left_eye[1] + right_eye[1]) / 2
        nose_tip = np.mean(landmarks['nose_tip'], axis=0)
        upside_down = nose_tip[1] < eye_center_y

    # Align face
    aligned_face = _align_face(img_array, ymin, xmax, ymax, xmin, landmarks=landmarks)
    use_aligned = False
    if aligned_face is not None:
        aligned_face_uint8 = (aligned_face * 255).astype(np.uint8) if aligned_face.dtype == np.float64 else aligned_face
        face_encodings_result = face_recognition.face_encodings(aligned_face_uint8, model="large")
        if face_encodings_result:
            use_aligned = True
        else:
            logger.debug(f"[detect_faces_profile] Aligned face encoding failed for user {user_id}, falling back to original crop")

    if use_aligned:
        face_for_quality = aligned_face_uint8
        encoding = face_encodings_result[0]
        pil_thumb = Image.fromarray(aligned_face_uint8)
    else:
        # Fallback: use original image with known location
        face_encodings_result = face_recognition.face_encodings(
            img_array,
            known_face_locations=[face_location],
            model="large"
        )
        if not face_encodings_result:
            logger.warning(f"[detect_faces_profile] No encoding generated for user {user_id}")
            return
        encoding = face_encodings_result[0]
        # Use raw crop for thumbnail
        face_crop = img_array[ymin:ymax, xmin:xmax]
        if face_crop.size == 0:
            logger.warning(f"[detect_faces_profile] Empty face crop for user {user_id}")
            return
        if upside_down:
            face_crop = cv2.rotate(face_crop, cv2.ROTATE_180)
        face_for_quality = face_crop
        thumb_face = cv2.resize(face_crop, (160, 160))
        pil_thumb = Image.fromarray(thumb_face)

    # Blur check – skip low-quality faces that produce unreliable encodings
    if _is_blurry(face_for_quality, threshold=20.0):
        logger.info(f"[detect_faces_profile] Skipping blurry face for user {user_id}")
        return

    # Create thumbnail content
    thumb_io = BytesIO()
    pil_thumb.save(thumb_io, format='JPEG', quality=85)
    thumb_content = thumb_io.getvalue()

    # Check if user already has a FaceGroup
    existing_user_group = FaceGroup.objects.filter(user=user).first()
    skip_general_search = False
    if existing_user_group:
        # Compute centroid of that group
        encodings_list = []
        for tag in existing_user_group.face_tags.exclude(encoding__isnull=True):
            try:
                enc = pickle.loads(tag.encoding)
                encodings_list.append(enc)
            except Exception:
                pass
        if encodings_list:
            centroid = np.mean(encodings_list, axis=0)
            distance = np.linalg.norm(encoding - centroid)
            if distance < 0.6:
                best_group_id = existing_user_group.id
                # Update centroid (moving average)
                count = len(encodings_list)
                new_centroid = (centroid * count + encoding) / (count + 1)
                # We'll store the updated centroid for later use if needed
                group_centroids = {best_group_id: new_centroid}
            else:
                # Even if distance is high, still use the user's group to avoid duplicates
                logger.info(f"[detect_faces_profile] User {user_id} existing group {existing_user_group.id} distance {distance:.4f} > 0.6, but reusing to avoid duplicate")
                best_group_id = existing_user_group.id
                count = len(encodings_list)
                new_centroid = (centroid * count + encoding) / (count + 1)
                group_centroids = {best_group_id: new_centroid}
        else:
            # Group exists but has no encodings – just use it
            best_group_id = existing_user_group.id
            group_centroids = {best_group_id: encoding}
        skip_general_search = True
    else:
        # Load existing groups and centroids (original logic)
        existing_groups = FaceGroup.objects.prefetch_related('face_tags').all()
        group_centroids = {}
        for group in existing_groups:
            encodings_list = []
            for tag in group.face_tags.all():
                if tag.encoding:
                    try:
                        enc = pickle.loads(tag.encoding)
                        encodings_list.append(enc)
                    except Exception:
                        pass
            if encodings_list:
                group_centroids[group.id] = np.mean(encodings_list, axis=0)

    if not skip_general_search:
        # Find closest existing group with a single relaxed threshold
        best_group_id = None
        min_distance = 0.6
        for group_id, centroid in group_centroids.items():
            distance = np.linalg.norm(encoding - centroid)
            if distance < min_distance:
                min_distance = distance
                best_group_id = group_id

        # No margin check – accept the closest group if below threshold
        if best_group_id is not None and min_distance >= 0.6:
            best_group_id = None

    user_display_name = user.get_full_name() or user.username

    if best_group_id is not None:
        group = FaceGroup.objects.get(id=best_group_id)
        if not group.name or group.name.strip() == '':
            group.name = user_display_name
        if not group.user:
            group.user = user
        group.save(update_fields=['name', 'user'])
        logger.info(f"[detect_faces_profile] Matched user {user_id} to group {best_group_id}, name='{user_display_name}'")
    else:
        new_group = FaceGroup.objects.create(name=user_display_name, user=user)
        new_group.thumbnail.save(f'group_{new_group.id}.jpg', ContentFile(thumb_content), save=True)
        logger.info(f"[detect_faces_profile] Created new group {new_group.id} for user {user_id}, name='{user_display_name}'")


def _merge_groups(keep_group, remove_group):
    """
    Merge remove_group into keep_group:
    - Reassign all FaceTags from remove_group to keep_group.
    - Copy name if keep_group has no name.
    - Ensure keep_group has a thumbnail (use remove_group's if missing).
    - Delete remove_group.
    """
    # Reassign tags
    FaceTag.objects.filter(face_group=remove_group).update(face_group=keep_group)

    # Copy name if keep_group lacks one
    if (not keep_group.name or keep_group.name.strip() == '') and remove_group.name:
        keep_group.name = remove_group.name
        keep_group.save(update_fields=['name'])

    # Preserve user link
    if not keep_group.user and remove_group.user:
        keep_group.user = remove_group.user
        keep_group.save(update_fields=['user'])

    # Ensure keep_group has a thumbnail
    if not keep_group.thumbnail:
        if remove_group.thumbnail:
            keep_group.thumbnail = remove_group.thumbnail
            keep_group.save(update_fields=['thumbnail'])
        else:
            # Try to get a thumbnail from any of its tags
            first_tag = keep_group.face_tags.first()
            if first_tag and first_tag.thumbnail:
                keep_group.thumbnail = first_tag.thumbnail
                keep_group.save(update_fields=['thumbnail'])

    # Delete the now-empty group
    if remove_group.thumbnail and remove_group.thumbnail != keep_group.thumbnail:
        remove_group.thumbnail.delete(save=False)
    remove_group.delete()


@shared_task
def deduplicate_faces():
    """
    Periodic task that removes duplicate FaceTags within the same media
    and merges duplicate FaceGroups (same person).
    """
    THRESHOLD = 0.4               # stricter: only merge very close tags within same media
    logger.info("[deduplicate_faces] Starting face deduplication")

    # ---------- 1. Deduplicate FaceTags within each media ----------
    # Get all media that have more than one FaceTag with an encoding
    media_ids = (
        FaceTag.objects
        .exclude(encoding__isnull=True)
        .values('media_id')
        .annotate(tag_count=Count('id'))
        .filter(tag_count__gt=1)
        .values_list('media_id', flat=True)
    )

    tags_deleted = 0
    groups_merged = set()  # track (kept_group_id, deleted_group_id) to avoid double merge

    for media_id in media_ids:
        tags = list(FaceTag.objects.filter(media_id=media_id).exclude(encoding__isnull=True))
        if len(tags) < 2:
            continue

        # Load encodings
        encodings = []
        for tag in tags:
            try:
                enc = pickle.loads(tag.encoding)
                encodings.append(enc)
            except Exception:
                encodings.append(None)

        # Compare all pairs
        to_delete = set()
        for i in range(len(tags)):
            if i in to_delete:
                continue
            for j in range(i + 1, len(tags)):
                if j in to_delete:
                    continue
                if encodings[i] is None or encodings[j] is None:
                    continue
                dist = np.linalg.norm(encodings[i] - encodings[j])
                if dist < THRESHOLD:
                    # Duplicate found – keep the one with smaller ID
                    keep, remove = (i, j) if tags[i].id < tags[j].id else (j, i)
                    to_delete.add(remove)

                    # Merge face groups if they differ
                    g1 = tags[keep].face_group
                    g2 = tags[remove].face_group
                    if g1 and g2 and g1.id != g2.id:
                        # Merge g2 into g1
                        if (g1.id, g2.id) not in groups_merged and (g2.id, g1.id) not in groups_merged:
                            _merge_groups(g1, g2)
                            groups_merged.add((g1.id, g2.id))

        # Delete duplicate tags
        for idx in to_delete:
            tag = tags[idx]
            logger.info(f"[deduplicate_faces] Deleting duplicate FaceTag {tag.id} (media {media_id})")
            tag.delete()
            tags_deleted += 1

    logger.info(f"[deduplicate_faces] Deleted {tags_deleted} duplicate FaceTags")

    # ---------- 2. Deduplicate FaceGroups ----------
    # Get all groups that have at least one encoding
    groups = FaceGroup.objects.annotate(
        tag_count=Count('face_tags')
    ).filter(tag_count__gt=0)

    # Build list of encodings per group
    group_encodings = {}
    for group in groups:
        encodings_list = []
        for tag in group.face_tags.exclude(encoding__isnull=True):
            try:
                enc = pickle.loads(tag.encoding)
                encodings_list.append(enc)
            except Exception:
                pass
        if encodings_list:
            group_encodings[group.id] = encodings_list

    # Compare all group pairs using ratio of pairwise distances below threshold
    group_ids = list(group_encodings.keys())
    merged_groups = set()
    MIN_TAGS_FOR_MERGE = 3   # only merge groups that have at least 3 tags
    AVG_DIST_THRESHOLD = 0.5  # stricter: groups must be more similar

    for i in range(len(group_ids)):
        gid1 = group_ids[i]
        if gid1 in merged_groups:
            continue
        encs1 = group_encodings[gid1]
        if len(encs1) < MIN_TAGS_FOR_MERGE:
            continue
        for j in range(i + 1, len(group_ids)):
            gid2 = group_ids[j]
            if gid2 in merged_groups:
                continue
            encs2 = group_encodings[gid2]
            if len(encs2) < MIN_TAGS_FOR_MERGE:
                continue

            # Compute pairwise distances and count how many are below threshold
            below_threshold = 0
            total_pairs = 0
            for e1 in encs1:
                for e2 in encs2:
                    dist = np.linalg.norm(e1 - e2)
                    if dist < AVG_DIST_THRESHOLD:
                        below_threshold += 1
                    total_pairs += 1

            if total_pairs > 0:
                ratio = below_threshold / total_pairs
                if ratio >= 0.8:   # require 80% of pairwise distances to be below threshold
                    # Merge gid2 into gid1 (keep the one with smaller ID)
                    keep_id, remove_id = (gid1, gid2) if gid1 < gid2 else (gid2, gid1)
                    if (keep_id, remove_id) not in groups_merged and (remove_id, keep_id) not in groups_merged:
                        keep_group = FaceGroup.objects.get(id=keep_id)
                        remove_group = FaceGroup.objects.get(id=remove_id)
                        _merge_groups(keep_group, remove_group)
                        groups_merged.add((keep_id, remove_id))
                        merged_groups.add(remove_id)
                        logger.info(f"[deduplicate_faces] Merged group {remove_id} into {keep_id} "
                                    f"(ratio={ratio:.2f}, {below_threshold}/{total_pairs} below {AVG_DIST_THRESHOLD})")

    # ---------- 2b. Merge groups where one has only 1 tag ----------
    single_tag_groups = {
        gid: encs[0] for gid, encs in group_encodings.items() if len(encs) == 1
    }
    for gid1, enc1 in single_tag_groups.items():
        if gid1 in merged_groups:
            continue
        for gid2, encs2 in group_encodings.items():
            if gid2 == gid1 or gid2 in merged_groups:
                continue
            if len(encs2) < 3:   # only merge into a group that has at least 3 tags
                continue
            centroid2 = np.mean(encs2, axis=0)
            dist = np.linalg.norm(enc1 - centroid2)
            if dist < 0.5:        # stricter for single-tag groups
                keep_id, remove_id = (gid2, gid1) if gid2 < gid1 else (gid1, gid2)
                if (keep_id, remove_id) not in groups_merged and (remove_id, keep_id) not in groups_merged:
                    keep_group = FaceGroup.objects.get(id=keep_id)
                    remove_group = FaceGroup.objects.get(id=remove_id)
                    _merge_groups(keep_group, remove_group)
                    groups_merged.add((keep_id, remove_id))
                    merged_groups.add(remove_id)
                    logger.info(f"[deduplicate_faces] Merged single-tag group {remove_id} into {keep_id} (dist={dist:.4f})")

    # Clean up empty groups (just in case)
    empty_groups = FaceGroup.objects.annotate(
        tag_count=Count('face_tags')
    ).filter(tag_count=0)
    for group in empty_groups:
        if group.thumbnail:
            group.thumbnail.delete(save=False)
        group.delete()

    logger.info("[deduplicate_faces] Deduplication complete")
    return {'tags_deleted': tags_deleted, 'groups_merged': len(groups_merged)}


@shared_task
def clean_orphaned_facetag_files():
    """
    Remove JPEG/PNG files in the facetags/ directory that are not
    referenced by any FaceTag or FaceGroup thumbnail.
    """
    import glob
    from django.conf import settings as django_settings

    facetags_dir = os.path.join(django_settings.MEDIA_ROOT, 'facetags')
    if not os.path.isdir(facetags_dir):
        logger.info("[clean_orphaned_facetag_files] facetags/ directory does not exist")
        return 0

    # Collect all filenames currently referenced in the database
    referenced = set()
    for tag in FaceTag.objects.exclude(thumbnail='').exclude(thumbnail__isnull=True):
        referenced.add(os.path.basename(tag.thumbnail.name))
    for group in FaceGroup.objects.exclude(thumbnail='').exclude(thumbnail__isnull=True):
        referenced.add(os.path.basename(group.thumbnail.name))

    # Walk the directory and delete unreferenced files
    deleted = 0
    for filepath in glob.glob(os.path.join(facetags_dir, '*')):
        if os.path.isfile(filepath):
            filename = os.path.basename(filepath)
            if filename not in referenced:
                try:
                    os.remove(filepath)
                    deleted += 1
                    logger.info(f"[clean_orphaned_facetag_files] Deleted orphan: {filepath}")
                except OSError as e:
                    logger.error(f"[clean_orphaned_facetag_files] Failed to delete {filepath}: {e}")

    if deleted:
        logger.info(f"[clean_orphaned_facetag_files] Removed {deleted} orphaned files")
    else:
        logger.debug("[clean_orphaned_facetag_files] No orphaned files found")
    return deleted


@shared_task
def cleanup_missing_cloud_files():
    """
    Delete Media records whose files no longer exist in Nextcloud.
    Checks both nextcloud_file_id and original_filename against the actual
    files present in the cloud folder.
    """
    client = NextcloudClient()
    try:
        cloud_files = client.list_files()
    except Exception as e:
        logger.error(f"cleanup_missing_cloud_files: failed to list Nextcloud files: {e}")
        return

    deleted_count = 0
    # Process in batches to limit memory usage
    for media in Media.objects.only('id', 'nextcloud_file_id', 'original_filename').iterator(chunk_size=500):
        file_id = media.nextcloud_file_id or ''
        orig_name = media.original_filename or ''
        if file_id not in cloud_files and orig_name not in cloud_files:
            logger.info(f"Deleting Media {media.id} because file is missing from Nextcloud "
                        f"(nextcloud_file_id={file_id}, original_filename={orig_name})")
            media.delete()  # cascades to FaceTags, etc.
            deleted_count += 1

    logger.info(f"cleanup_missing_cloud_files: deleted {deleted_count} Media records")


@shared_task
def compute_similarity_ordering():
    """
    Compute visual similarity ordering for all approved images and videos
    using a MobileNetV2 feature extractor (TFLite).  Assigns a float position
    to each media item so that visually similar items appear near each other.
    Runs every 24 hours (or as scheduled).
    """
    import tflite_runtime.interpreter as tflite
    from PIL import Image
    from io import BytesIO
    import numpy as np
    import cv2
    import tempfile
    import os
    import requests
    from django.conf import settings as django_settings

    MODEL_URL = (
        "https://tfhub.dev/google/lite-model/imagenet/mobilenet_v2_100_224/"
        "feature_vector/2/default/1?lite-format=tflite"
    )
    MODELS_DIR = os.path.join(django_settings.BASE_DIR, 'models')
    os.makedirs(MODELS_DIR, exist_ok=True)
    MODEL_PATH = os.path.join(MODELS_DIR, 'similarity_model.tflite')

    # Download model if not present
    if not os.path.exists(MODEL_PATH):
        logger.info("[similarity] Downloading MobileNetV2 TFLite model...")
        resp = requests.get(MODEL_URL, timeout=120)
        resp.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            f.write(resp.content)

    # Load TFLite model
    interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_shape = input_details[0]['shape']  # [1, 224, 224, 3]

    # Fetch all approved media (images + videos)
    from .models import Media
    media_items = list(Media.objects.filter(status='approved'))

    if not media_items:
        logger.info("[similarity] No approved media to order.")
        return

    embeddings = []
    valid_media = []

    for media in media_items:
        try:
            content, _ = get_file_from_cloud(media)
            if content is None:
                # fallback to local file
                if media.file and media.file.storage.exists(media.file.name):
                    with media.file.open('rb') as f:
                        content = f.read()
                else:
                    continue

            if media.media_type == 'image':
                # Process image
                img = Image.open(BytesIO(content)).convert('RGB').resize((224, 224))
                img_array = np.array(img, dtype=np.float32) / 127.5 - 1.0
                img_array = np.expand_dims(img_array, axis=0)
                interpreter.set_tensor(input_details[0]['index'], img_array)
                interpreter.invoke()
                embedding = interpreter.get_tensor(output_details[0]['index'])[0]
                embeddings.append(embedding)
                valid_media.append(media)

            elif media.media_type == 'video':
                # Extract one frame from the middle of the video
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                cap = cv2.VideoCapture(tmp_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
                    ret, frame = cap.read()
                    if ret:
                        # Convert BGR to RGB and resize
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb).resize((224, 224))
                        img_array = np.array(img, dtype=np.float32) / 127.5 - 1.0
                        img_array = np.expand_dims(img_array, axis=0)
                        interpreter.set_tensor(input_details[0]['index'], img_array)
                        interpreter.invoke()
                        embedding = interpreter.get_tensor(output_details[0]['index'])[0]
                        embeddings.append(embedding)
                        valid_media.append(media)
                cap.release()
                os.unlink(tmp_path)

        except Exception as e:
            logger.warning(f"[similarity] Failed to process media {media.id}: {e}")

    if len(valid_media) < 2:
        # Not enough items to order
        for idx, media in enumerate(valid_media):
            media.similarity_position = float(idx)
            media.save(update_fields=['similarity_position'])
        # Clear positions for non-processed approved media
        Media.objects.filter(status='approved').exclude(
            id__in=[m.id for m in valid_media]
        ).update(similarity_position=None)
        return

    # Compute cosine distance matrix
    embeddings = np.array(embeddings)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    normalized = embeddings / norms
    similarity = np.dot(normalized, normalized.T)
    distance = 1.0 - similarity
    np.fill_diagonal(distance, np.inf)

    # Greedy nearest-neighbour ordering
    n = len(valid_media)
    start_idx = 0  # deterministic start
    order = [start_idx]
    visited = {start_idx}

    for _ in range(n - 1):
        last = order[-1]
        dists = distance[last].copy()
        for v in visited:
            dists[v] = np.inf
        next_idx = np.argmin(dists)
        order.append(next_idx)
        visited.add(next_idx)

    # Assign positions
    for pos, idx in enumerate(order):
        valid_media[idx].similarity_position = float(pos)
        valid_media[idx].save(update_fields=['similarity_position'])

    # Clear positions for approved media not in this run
    Media.objects.filter(status='approved').exclude(
        id__in=[m.id for m in valid_media]
    ).update(similarity_position=None)

    logger.info(f"[similarity] Ordered {len(valid_media)} media items by visual similarity.")


@shared_task(bind=True, max_retries=1)
def generate_wedding_book_task(self, book_id):
    try:
        book = WeddingBook.objects.get(id=book_id)
    except WeddingBook.DoesNotExist:
        return

    try:
        book.status = WeddingBook.Status.PROCESSING
        book.progress = 0
        book.error_message = ''
        book.save()

        media_ids = book.selected_media_ids or []

        # Auto-select media if fewer than 20 IDs were provided
        if len(media_ids) < 20:
            media_ids = auto_select_media(media_ids, target=20)

        # Persist the final list back to the book
        book.selected_media_ids = media_ids
        book.save(update_fields=['selected_media_ids'])

        media_list = list(Media.objects.filter(
            id__in=media_ids, status='approved', media_type='image'
        ).order_by('id'))
        if not media_list:
            book.status = WeddingBook.Status.FAILED
            book.error_message = 'No approved images found for the selected IDs.'
            book.save()
            return

        # Update selected_media_ids to only the valid image IDs
        book.selected_media_ids = [m.id for m in media_list]
        book.save(update_fields=['selected_media_ids'])

        total = len(media_list)
        captions = {}

        # Step 1: generate captions
        for idx, media_obj in enumerate(media_list):
            try:
                file_content, _ = get_file_from_cloud(media_obj)
                if file_content is None:
                    raise Exception("File not found in cloud")
                eng_caption = generate_english_caption(file_content)
                it_caption = translate_text(eng_caption, 'it')
                ko_caption = translate_text(eng_caption, 'ko')
                captions[str(media_obj.id)] = {'it': it_caption, 'ko': ko_caption}
            except Exception as e:
                logger.error(f"Caption generation failed for media {media_obj.id}: {e}")
                captions[str(media_obj.id)] = {'it': '', 'ko': ''}

            progress = int((idx + 1) / total * 50)
            book.progress = progress
            book.captions_data = captions
            book.save()

        # Step 2: build PDF
        buffer = BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Color palette
        GOLD = HexColor('#D4AF37')
        SOFT_PINK = HexColor('#F8E8E8')
        WHITE = HexColor('#FFFFFF')
        DARK = HexColor('#333333')
        NAVY = HexColor('#1B2A4A')
        BLUSH = HexColor('#F9E4E4')
        FONT_NAME = 'Helvetica'
        FONT_BOLD = 'Helvetica-Bold'
        FONT_ITALIC = 'Helvetica-Oblique'
        # Register a cursive font if available (optional, fallback to Helvetica)
        CURSIVE = FONT_ITALIC
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            font_path = os.path.join(django_settings.BASE_DIR, 'static', 'fonts', 'GreatVibes-Regular.ttf')
            pdfmetrics.registerFont(TTFont('Cursive', font_path))
            CURSIVE = 'Cursive'
        except Exception:
            pass

        # Creative layouts for 1, 2, or 3 photos (x, y, w, h, rotation)
        layouts = {
            1: [
                # Centered large with slight tilt
                [(70, 200, 455, 400, 2)],
                # Off-center with decorative corner
                [(40, 150, 400, 450, -3)],
            ],
            2: [
                # Diagonal split
                [(30, 300, 250, 300, 5), (310, 100, 250, 300, -5)],
                # Overlapping frames
                [(50, 250, 280, 350, 0), (250, 150, 280, 350, 8)],
                # Side-by-side with tilt
                [(40, 250, 250, 300, -4), (305, 250, 250, 300, 4)],
            ],
            3: [
                # One large left, two small right stacked
                [(30, 200, 280, 400, 0), (330, 420, 220, 180, 5), (330, 180, 220, 180, -5)],
                # Triangle arrangement
                [(170, 450, 250, 200, 0), (40, 150, 200, 200, -6), (350, 150, 200, 200, 6)],
                # Vertical strip with overlapping
                [(40, 400, 250, 250, 3), (200, 200, 250, 250, -3), (120, 50, 250, 250, 0)],
            ],
        }

        def draw_floral_border(pdf_canvas, width, height, color=GOLD):
            pdf_canvas.setStrokeColor(color)
            pdf_canvas.setLineWidth(1.5)
            pdf_canvas.rect(15, 15, width - 30, height - 30)
            pdf_canvas.rect(18, 18, width - 36, height - 36)
            # Simple corner flourishes
            pdf_canvas.setLineWidth(1)
            for x, y in [(20, 20), (width - 20, 20), (20, height - 20), (width - 20, height - 20)]:
                pdf_canvas.arc(x - 10, y - 10, x + 10, y + 10, 0, 360)

        def draw_page_number(pdf_canvas, page_num, total_pages):
            pdf_canvas.setFont(FONT_NAME, 8)
            pdf_canvas.setFillColor(GOLD)
            pdf_canvas.drawRightString(width - 40, 20, f"{page_num} / {total_pages}")

        # ---- Cover Page ----
        pdf_canvas.setFillColor(NAVY)
        pdf_canvas.rect(0, 0, width, height, fill=1)
        draw_floral_border(pdf_canvas, width, height, GOLD)
        pdf_canvas.setFont(CURSIVE, 36)
        pdf_canvas.setFillColor(GOLD)
        pdf_canvas.drawCentredString(width / 2, height / 2 + 40, "Our Wedding Book")
        pdf_canvas.setFont(FONT_ITALIC, 14)
        pdf_canvas.drawCentredString(width / 2, height / 2 - 20, "Sang Hee & Fabio")
        pdf_canvas.showPage()

        def caption_similarity(cap1, cap2):
            """Simple word overlap similarity between two captions."""
            words1 = set(cap1.lower().split())
            words2 = set(cap2.lower().split())
            if not words1 or not words2:
                return 0.0
            intersection = words1 & words2
            union = words1 | words2
            return len(intersection) / len(union)

        # Group media into pages of 1-3 based on caption similarity
        page_groups = []
        used = set()
        for idx, media_obj in enumerate(media_list):
            if idx in used:
                continue
            group = [media_obj]
            used.add(idx)
            # Try to add up to 2 more similar items
            for j in range(idx + 1, min(idx + 3, total)):
                if j in used:
                    continue
                if len(group) >= 3:
                    break
                # Check similarity with the first item in the group
                cap1 = captions.get(str(media_obj.id), {}).get('it', '')
                cap2 = captions.get(str(media_list[j].id), {}).get('it', '')
                sim = caption_similarity(cap1, cap2)
                if sim > 0.2:   # threshold – tune as needed
                    group.append(media_list[j])
                    used.add(j)
            page_groups.append(group)

        total_pages = len(page_groups) + 1  # +1 for cover

        for page_idx, group in enumerate(page_groups):
            # Alternate background colors
            if page_idx % 2 == 0:
                bg_color = SOFT_PINK
            else:
                bg_color = BLUSH
            pdf_canvas.setFillColor(bg_color)
            pdf_canvas.rect(0, 0, width, height, fill=1)
            draw_floral_border(pdf_canvas, width, height)

            # Pick a random layout for the group size
            group_size = len(group)
            possible_layouts = layouts.get(group_size, layouts[1])
            chosen_layout = random.choice(possible_layouts)

            # Draw images with rotation
            for slot_idx, media_obj in enumerate(group):
                if slot_idx >= len(chosen_layout):
                    break
                x, y, w, h, rotation = chosen_layout[slot_idx]
                try:
                    file_content, _ = get_file_from_cloud(media_obj)
                    img = ImageReader(BytesIO(file_content))
                    pdf_canvas.saveState()
                    # Translate to center of image, rotate, then draw
                    cx = x + w / 2
                    cy = y + h / 2
                    pdf_canvas.translate(cx, cy)
                    pdf_canvas.rotate(rotation)
                    pdf_canvas.drawImage(img, -w/2, -h/2, w, h, preserveAspectRatio=True, mask='auto')
                    pdf_canvas.restoreState()
                except Exception as e:
                    logger.error(f"Could not draw image {media_obj.id}: {e}")
                    pdf_canvas.setFillColor(HexColor('#CCCCCC'))
                    pdf_canvas.rect(x, y, w, h, fill=1)
                    pdf_canvas.setFillColor(DARK)
                    pdf_canvas.drawString(x + 10, y + h / 2, "Image missing")

            # Captions area
            caption_y = 120
            pdf_canvas.setFont(FONT_BOLD, 10)
            pdf_canvas.setFillColor(GOLD)
            pdf_canvas.drawString(40, caption_y + 20, "Didascalia / 캡션")
            pdf_canvas.setFont(FONT_NAME, 9)
            pdf_canvas.setFillColor(DARK)
            y_offset = caption_y
            for media_obj in group:
                cap = captions.get(str(media_obj.id), {'it': '', 'ko': ''})
                it_text = cap.get('it', '')
                ko_text = cap.get('ko', '')
                combined = f"{it_text}  |  {ko_text}"
                if pdf_canvas.stringWidth(combined, FONT_NAME, 9) > width - 80:
                    pdf_canvas.drawString(40, y_offset, it_text[:80])
                    y_offset -= 12
                    pdf_canvas.drawString(40, y_offset, ko_text[:80])
                    y_offset -= 12
                else:
                    pdf_canvas.drawString(40, y_offset, combined)
                    y_offset -= 14
                if y_offset < 40:
                    break

            draw_page_number(pdf_canvas, page_idx + 2, total_pages)
            pdf_canvas.showPage()

            # Update progress (50% -> 100%)
            progress = 50 + int((page_idx + 1) / len(page_groups) * 50)
            book.progress = progress
            book.save()

        pdf_canvas.save()
        pdf_content = buffer.getvalue()
        buffer.close()

        filename = f"wedding_book_{book.id}.pdf"
        book.pdf_file.save(filename, ContentFile(pdf_content), save=False)
        book.status = WeddingBook.Status.COMPLETED
        book.progress = 100
        book.save()

        # Unload AI models to free memory on Raspberry Pi
        unload_models()

    except Exception as e:
        logger.exception("Wedding book generation failed")
        try:
            book = WeddingBook.objects.get(id=book_id)
            book.status = WeddingBook.Status.FAILED
            book.error_message = str(e)[:500]
            book.save()
        except Exception:
            pass
