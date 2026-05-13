"""
NSFW (Not Safe For Work) content detection utilities.
Uses NudeNet to detect inappropriate images.
"""

import logging
import os
import tempfile

logger = logging.getLogger(__name__)

# NSFW detection confidence threshold (0.0 to 1.0)
NSFW_THRESHOLD = 0.5

# Cache the classifier to avoid reloading the model on every request
_classifier = None


def get_classifier():
    """
    Get or initialize the NudeNet NudeClassifier.
    Caches the classifier instance for performance.

    Returns:
        NudeClassifier or None: The classifier instance, or None if
        NudeNet is not available.
    """
    global _classifier
    if _classifier is None:
        try:
            from nudenet import NudeClassifier
            _classifier = NudeClassifier()
        except ImportError:
            logger.warning(
                "NudeNet is not installed. NSFW detection will be skipped. "
                "Install it with: pip install nudenet"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to initialize NudeClassifier: {e}")
            return None
    return _classifier


def check_nsfw_image(image_file):
    """
    Check if an image contains NSFW content using NudeNet.

    The image is saved to a temporary file for classification, then cleaned up.

    Args:
        image_file: A Django ImageFieldFile, UploadedFile, or any file-like
                    object with a read() method.

    Returns:
        tuple: (is_nsfw: bool, confidence: float)
               Returns (False, 0.0) if the check cannot be performed
               (e.g., NudeNet not installed, image processing error).
    """
    classifier = get_classifier()
    if classifier is None:
        return False, 0.0

    tmp_path = None
    try:
        # Save the image to a temporary file for classification
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
            if hasattr(image_file, 'chunks'):
                # Django UploadedFile
                for chunk in image_file.chunks():
                    tmp.write(chunk)
            elif hasattr(image_file, 'open'):
                # Django ImageFieldFile / FieldFile
                image_file.open(mode='rb')
                try:
                    tmp.write(image_file.read())
                finally:
                    image_file.close()
            elif hasattr(image_file, 'read'):
                # Generic file-like object
                image_file.seek(0)
                tmp.write(image_file.read())
            else:
                logger.warning("Unsupported image file type for NSFW check")
                return False, 0.0

        # Classify the image
        predictions = classifier.classify(tmp_path)

        # Extract the unsafe score from the result.
        # nudenet >=1.0 returns a list of dicts, e.g.:
        # [{'class': 'safe', 'score': 0.9}, {'class': 'unsafe', 'score': 0.1}]
        unsafe_score = 0.0
        for pred in predictions:
            if pred.get('class') == 'unsafe':
                unsafe_score = pred.get('score', 0.0)
                break

        is_nsfw = unsafe_score > NSFW_THRESHOLD

        return is_nsfw, unsafe_score

    except Exception as e:
        logger.error(f"Error checking NSFW content: {e}")
        return False, 0.0
    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def is_image_file(file_field):
    """
    Check if a file field contains an image based on its name or content type.

    Args:
        file_field: A Django FileField, ImageField, or UploadedFile instance.

    Returns:
        bool: True if the file appears to be an image, False otherwise.
    """
    if not file_field:
        return False

    # Check by file extension
    name = getattr(file_field, 'name', '') or ''
    image_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'
    )
    if name.lower().endswith(image_extensions):
        return True

    # Check by content type
    content_type = getattr(file_field, 'content_type', '') or ''
    if content_type.startswith('image/'):
        return True

    return False
