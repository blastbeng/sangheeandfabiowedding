import logging
import redis

from celery import shared_task
from django.core.files.base import ContentFile
from django.db.models import Count, Q
import hashlib
import os
import requests
import cv2
import face_recognition
import mediapipe as mp
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


def _is_blurry(face_image, threshold=150.0):
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

    try:
        media = Media.objects.get(id=media_id)
    except Media.DoesNotExist:
        logger.warning(f"[detect_faces] Media {media_id} not found, skipping")
        return

    # If force=True, clear existing face tags and reset the attempted flag
    if force:
        # Delete all existing face tags for this media
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

        # Skip if already attempted (safety net)
        if media.face_detection_attempted:
            logger.info(f"[detect_faces] Skipping media {media_id}: face_detection_attempted is already True")
            return
    else:
        # When forcing, still require the file to be an image
        if media.media_type != 'image':
            logger.info(f"[detect_faces] Skipping media {media_id}: media_type is '{media.media_type}', not 'image'")
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

    # Load image with PIL and convert to RGB numpy array
    try:
        pil_image = Image.open(BytesIO(content)).convert('RGB')
        img_array = np.array(pil_image)
    except Exception as e:
        logger.error(f"[detect_faces] Cannot load image for media {media_id}: {e}")
        return

    # Use MediaPipe for fast face detection
    try:
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.6
        ) as face_detection:
            results = face_detection.process(img_array)
    except Exception as e:
        logger.error(f"[detect_faces] MediaPipe face detection failed for media {media_id}: {e}")
        return

    if not results.detections:
        # No faces found – mark as attempted and exit
        logger.info(f"[detect_faces] No faces detected in media {media_id} by MediaPipe")
        media.face_detection_attempted = True
        media.save(update_fields=['face_detection_attempted'])
        return

    logger.info(f"[detect_faces] MediaPipe found {len(results.detections)} face(s) in media {media_id}")

    # Extract face locations in dlib format (top, right, bottom, left)
    # Expand boxes by 20% and filter out tiny faces
    face_locations = []
    h, w, _ = img_array.shape
    for detection in results.detections:
        bbox = detection.location_data.relative_bounding_box
        xmin = int(bbox.xmin * w)
        ymin = int(bbox.ymin * h)
        width = int(bbox.width * w)
        height = int(bbox.height * h)

        # Expand box by 20% to include more context
        expand_w = int(width * 0.2)
        expand_h = int(height * 0.2)
        xmin = max(0, xmin - expand_w)
        ymin = max(0, ymin - expand_h)
        xmax = min(w, xmin + width + 2 * expand_w)
        ymax = min(h, ymin + height + 2 * expand_h)

        # Skip faces that are too small
        if (xmax - xmin) < 50 or (ymax - ymin) < 50:
            continue

        face_locations.append((ymin, xmax, ymax, xmin))  # dlib order: top, right, bottom, left

    if not face_locations:
        logger.info(f"[detect_faces] No usable faces after filtering in media {media_id}")
        media.face_detection_attempted = True
        media.save(update_fields=['face_detection_attempted'])
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
    faces_created = 0
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
            # Check if aligned face is too dark (can happen near image borders)
            if np.mean(aligned_face_uint8) < 10:
                logger.debug(f"[detect_faces] Aligned face is too dark for media {media_id}, skipping alignment")
            else:
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
        if _is_blurry(face_for_quality):
            logger.info(f"[detect_faces] Skipping blurry face in media {media_id}")
            continue

        # Create thumbnail content
        thumb_io = BytesIO()
        pil_thumb.save(thumb_io, format='JPEG', quality=85)
        thumb_content = thumb_io.getvalue()

        # Find closest and second-closest existing groups
        best_group_id = None
        min_distance = 0.5
        second_min_distance = float('inf')
        for group_id, centroid in group_centroids.items():
            distance = np.linalg.norm(encoding - centroid)
            if distance < min_distance:
                second_min_distance = min_distance
                min_distance = distance
                best_group_id = group_id
            elif distance < second_min_distance:
                second_min_distance = distance

        # If the margin between best and second-best is too small, treat as uncertain
        MARGIN = 0.05
        if best_group_id is not None and (second_min_distance - min_distance) < MARGIN:
            logger.info(f"[detect_faces] Uncertain match for media {media_id}: "
                        f"best={min_distance:.4f}, second={second_min_distance:.4f}, margin < {MARGIN}")
            best_group_id = None

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

        # Ensure the face group has a thumbnail (for groups created before this fix)
        if best_group_id:
            group = FaceGroup.objects.get(id=best_group_id)
            if not group.thumbnail:
                group.thumbnail.save(f'group_{group.id}.jpg', ContentFile(thumb_content), save=True)

        # Create FaceTag
        face_tag = FaceTag.objects.create(
            media=media,
            face_group_id=best_group_id,
            encoding=pickle.dumps(encoding),
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
    that have not been attempted yet, and also clean up images
    that have face tags with missing group thumbnails.
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

    # 2. Cleanup: images that have face tags but the group thumbnail is missing
    broken = Media.objects.filter(
        status='approved',
        media_type='image',
        face_detection_attempted=True,
    ).filter(
        Q(face_tags__isnull=False) &
        Q(face_tags__face_group__thumbnail__isnull=True) |
        Q(face_tags__face_group__thumbnail='')
    ).distinct()

    for media in broken:
        # Delete the broken face tags (they reference missing files)
        media.face_tags.all().delete()
        # Reset the flag so the image will be re-processed
        media.face_detection_attempted = False
        media.save(update_fields=['face_detection_attempted'])
        # Queue face detection
        detect_faces_task.delay(media.id)
        count += 1

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
    from PIL import Image
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

    # Load image
    try:
        pil_image = Image.open(BytesIO(content)).convert('RGB')
        img_array = np.array(pil_image)
    except Exception as e:
        logger.error(f"[detect_faces_profile] Cannot load image for user {user_id}: {e}")
        return

    # Detect faces with MediaPipe
    try:
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.6
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

    # Expand box by 20%
    expand_w = int(width * 0.2)
    expand_h = int(height * 0.2)
    xmin = max(0, xmin - expand_w)
    ymin = max(0, ymin - expand_h)
    xmax = min(w, xmin + width + 2 * expand_w)
    ymax = min(h, ymin + height + 2 * expand_h)

    if (xmax - xmin) < 50 or (ymax - ymin) < 50:
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
        if np.mean(aligned_face_uint8) < 10:
            logger.debug(f"[detect_faces_profile] Aligned face is too dark for user {user_id}, skipping alignment")
        else:
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
    if _is_blurry(face_for_quality):
        logger.info(f"[detect_faces_profile] Skipping blurry face for user {user_id}")
        return

    # Create thumbnail content
    thumb_io = BytesIO()
    pil_thumb.save(thumb_io, format='JPEG', quality=85)
    thumb_content = thumb_io.getvalue()

    # Load existing groups and centroids
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

    # Find closest and second-closest existing groups
    best_group_id = None
    min_distance = 0.5
    second_min_distance = float('inf')
    for group_id, centroid in group_centroids.items():
        distance = np.linalg.norm(encoding - centroid)
        if distance < min_distance:
            second_min_distance = min_distance
            min_distance = distance
            best_group_id = group_id
        elif distance < second_min_distance:
            second_min_distance = distance

    # If the margin between best and second-best is too small, treat as uncertain
    MARGIN = 0.05
    if best_group_id is not None and (second_min_distance - min_distance) < MARGIN:
        logger.info(f"[detect_faces_profile] Uncertain match for user {user_id}: "
                    f"best={min_distance:.4f}, second={second_min_distance:.4f}, margin < {MARGIN}")
        best_group_id = None

    user_display_name = user.get_full_name() or user.username

    if best_group_id is not None:
        group = FaceGroup.objects.get(id=best_group_id)
        if not group.name or group.name.strip() == '':
            group.name = user_display_name
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
    THRESHOLD = 0.5
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

    # Compare all group pairs using 80% ratio of pairwise distances below threshold
    group_ids = list(group_encodings.keys())
    merged_groups = set()
    MIN_TAGS_FOR_MERGE = 3
    AVG_DIST_THRESHOLD = 0.5

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
                if ratio >= 0.8:   # at least 80% of pairs must be close
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
