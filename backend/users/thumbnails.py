import os
import tempfile
import logging
from io import BytesIO

from django.core.cache import cache
from PIL import Image
import cv2

from .models import Media
from .cloud_clients import get_file_from_cloud

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (1200, 1200)   # max width/height
JPEG_QUALITY = 95
CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 7 days
CACHE_KEY_PREFIX = "media_thumbnail:v3"


def generate_thumbnail(media: Media) -> bytes | None:
    """
    Generate a JPEG thumbnail for the given media.
    Returns the JPEG bytes, or None on failure.
    """
    content, content_type = get_file_from_cloud(media)
    if content is None:
        logger.warning("No content for media %s", media.id)
        return None

    try:
        if media.media_type == 'image':
            img = Image.open(BytesIO(content))
            img = img.convert('RGB')
            img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format='JPEG', quality=JPEG_QUALITY)
            return buf.getvalue()

        elif media.media_type == 'video':
            # Write content to a temporary file for OpenCV
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            try:
                cap = cv2.VideoCapture(tmp_path)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    logger.warning("Could not read first frame of video %s", media.id)
                    return None

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=JPEG_QUALITY)
                return buf.getvalue()
            finally:
                os.unlink(tmp_path)

        else:
            return None

    except Exception as e:
        logger.exception("Thumbnail generation failed for media %s: %s", media.id, e)
        return None


def get_thumbnail(media_id: int) -> bytes | None:
    """
    Return cached thumbnail bytes for the given media ID.
    Generates and caches if not present.
    """
    cache_key = f"{CACHE_KEY_PREFIX}:{media_id}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    try:
        media = Media.objects.get(id=media_id)
    except Media.DoesNotExist:
        return None

    data = generate_thumbnail(media)
    if data is not None:
        cache.set(cache_key, data, timeout=CACHE_TIMEOUT)
    return data
