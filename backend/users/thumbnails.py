import os
import tempfile
import logging
from io import BytesIO

from django.conf import settings
from django.core.cache import cache
from PIL import Image, ImageOps
import cv2

from .models import Media, CustomUser
from .cloud_clients import get_file_from_cloud

logger = logging.getLogger(__name__)

# The gallery asks for a small "grid" rendition; opening a photo asks for the
# larger "large" rendition.  Keeping them separate avoids downloading a
# 1200x1200 JPEG for every card in the grid.
THUMBNAIL_SIZES = {
    'grid': (640, 640),
    'large': (1600, 1600),
}
THUMBNAIL_QUALITIES = {
    'grid': 80,
    'large': 85,
}
DEFAULT_THUMBNAIL_SIZE = 'grid'
THUMBNAIL_VERSION = 'v5'

# Legacy Redis cache used before v5.  It is only read by the
# `warm_thumbnails --from-redis` migration command.
LEGACY_CACHE_KEY_PREFIX = "media_thumbnail:v4"

CACHE_TIMEOUT = 60 * 60 * 24 * 30  # 30 days (~1 month)


def _derived_dir() -> str:
    return os.path.join(settings.MEDIA_ROOT, 'derived')


def _normalise_size(size: str | None) -> str:
    return size if size in THUMBNAIL_SIZES else DEFAULT_THUMBNAIL_SIZE


def thumbnail_path(media_id: int, size: str = DEFAULT_THUMBNAIL_SIZE) -> str:
    """Return the on-disk path of a cached rendition (file may not exist)."""
    size = _normalise_size(size)
    filename = f"{int(media_id)}_{size}_{THUMBNAIL_VERSION}.jpg"
    return os.path.join(_derived_dir(), filename)


def save_thumbnail_bytes(media_id: int, size: str, data: bytes) -> str:
    """Atomically write a rendition to the shared media volume."""
    path = thumbnail_path(media_id, size)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.{os.getpid()}.tmp"
    with open(tmp_path, 'wb') as f:
        f.write(data)
    os.replace(tmp_path, path)
    return path


def _resize_jpeg(img: Image.Image, size_px: tuple[int, int], quality: int) -> bytes:
    img = ImageOps.exif_transpose(img)
    img = img.convert('RGB')
    img.thumbnail(size_px, Image.LANCZOS)
    buf = BytesIO()
    img.save(
        buf,
        format='JPEG',
        quality=quality,
        optimize=True,
        progressive=True,
    )
    return buf.getvalue()


def generate_thumbnail(media: Media, size: str = DEFAULT_THUMBNAIL_SIZE) -> bytes | None:
    """
    Generate a JPEG rendition for the given media.
    Returns the JPEG bytes, or None on failure.
    """
    size = _normalise_size(size)
    size_px = THUMBNAIL_SIZES[size]
    quality = THUMBNAIL_QUALITIES[size]

    content, content_type = get_file_from_cloud(media)
    if content is None:
        logger.warning("No content for media %s", media.id)
        return None

    try:
        if media.media_type == 'image':
            img = Image.open(BytesIO(content))
            # JPEG DCT scaling: decode only the resolution we actually need.
            # This is much faster than decoding a 50MP original at full size.
            if img.format in ('JPEG', 'MPO'):
                img.draft('RGB', (size_px[0] * 2, size_px[1] * 2))
            return _resize_jpeg(img, size_px, quality)

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
                return _resize_jpeg(img, size_px, quality)
            finally:
                os.unlink(tmp_path)

        else:
            return None

    except Exception as e:
        logger.exception("Thumbnail generation failed for media %s: %s", media.id, e)
        return None


def get_thumbnail_path(media_id: int, size: str = DEFAULT_THUMBNAIL_SIZE) -> str | None:
    """
    Return the cached rendition path for the given media ID.
    Generates and caches it on disk if not present.
    """
    size = _normalise_size(size)
    path = thumbnail_path(media_id, size)
    if os.path.exists(path):
        return path

    try:
        media = Media.objects.get(id=media_id)
    except Media.DoesNotExist:
        return None

    data = generate_thumbnail(media, size)
    if data is None:
        return None
    return save_thumbnail_bytes(media_id, size, data)


def get_thumbnail(media_id: int, size: str = DEFAULT_THUMBNAIL_SIZE) -> bytes | None:
    """
    Backwards-compatible helper returning thumbnail bytes.
    Prefer get_thumbnail_path() so nginx can serve the file with sendfile.
    """
    path = get_thumbnail_path(media_id, size)
    if path is None:
        return None
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError:
        return None


def import_legacy_thumbnail(media_id: int) -> str | None:
    """
    One-off migration helper: convert the old 1200px Redis thumbnail into the
    new 640px grid rendition without downloading the original from Nextcloud.
    """
    data = cache.get(f"{LEGACY_CACHE_KEY_PREFIX}:{media_id}")
    if not data:
        return None
    try:
        img = Image.open(BytesIO(data))
        jpeg = _resize_jpeg(img, THUMBNAIL_SIZES['grid'], THUMBNAIL_QUALITIES['grid'])
        return save_thumbnail_bytes(media_id, 'grid', jpeg)
    except Exception as e:
        logger.warning("Could not import legacy thumbnail for media %s: %s", media_id, e)
        return None


def delete_thumbnail_files(media_id: int) -> None:
    """Remove all cached renditions for a media item (used on deletion)."""
    for size in THUMBNAIL_SIZES:
        try:
            os.remove(thumbnail_path(media_id, size))
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning("Could not delete thumbnail %s/%s: %s", media_id, size, e)


def clear_thumbnail_cache() -> int:
    """Remove every generated rendition. Returns the number of files removed."""
    removed = 0
    derived = _derived_dir()
    if not os.path.isdir(derived):
        return removed
    for name in os.listdir(derived):
        if not name.endswith('.jpg'):
            continue
        try:
            os.remove(os.path.join(derived, name))
            removed += 1
        except OSError as e:
            logger.warning("Could not remove cached thumbnail %s: %s", name, e)
    return removed


PROFILE_THUMBNAIL_SIZE = (128, 128)
PROFILE_CACHE_KEY_PREFIX = "user_profile_thumbnail:v1"
PROFILE_CACHE_TIMEOUT = 60 * 60 * 24 * 30  # 30 days


def generate_profile_thumbnail(user) -> bytes | None:
    """
    Generate a small JPEG thumbnail for a user's profile picture.
    Returns JPEG bytes, or None on failure.
    """
    if not user.profile_picture or user.profile_picture.name == 'profile_pics/default.png':
        return None

    try:
        with user.profile_picture.open('rb') as f:
            content = f.read()
    except Exception:
        return None

    try:
        img = Image.open(BytesIO(content))
        img = ImageOps.exif_transpose(img)
        img = img.convert('RGB')
        img.thumbnail(PROFILE_THUMBNAIL_SIZE, Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()
    except Exception as e:
        logger.exception("Profile thumbnail generation failed for user %s: %s", user.id, e)
        return None


def get_profile_thumbnail(user_id: int) -> bytes | None:
    """
    Return cached profile thumbnail bytes for the given user ID.
    Generates and caches if not present.
    """
    cache_key = f"{PROFILE_CACHE_KEY_PREFIX}:{user_id}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return None

    data = generate_profile_thumbnail(user)
    if data is not None:
        cache.set(cache_key, data, timeout=PROFILE_CACHE_TIMEOUT)
    return data
