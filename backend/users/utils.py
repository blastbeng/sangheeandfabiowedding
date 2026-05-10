from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

MAX_SIZE_MB = 2
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


def process_profile_picture(uploaded_file, max_size_bytes=MAX_SIZE_BYTES):
    """
    Accepts an uploaded file (InMemoryUploadedFile or similar).
    Returns a ContentFile with the (possibly resized) image data,
    or raises ValidationError if the image cannot be reduced below max_size_bytes.
    """
    # Read the file content
    if hasattr(uploaded_file, 'read'):
        content = uploaded_file.read()
    else:
        content = uploaded_file

    # If already under the limit, return as-is
    if len(content) <= max_size_bytes:
        return ContentFile(content, name=uploaded_file.name if hasattr(uploaded_file, 'name') else 'profile.jpg')

    # Try to resize/compress
    try:
        img = Image.open(BytesIO(content))
        # Convert to RGB if necessary (e.g., PNG with transparency)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Start with original dimensions
        width, height = img.size
        quality = 85

        # Loop to reduce size until under limit or dimensions become too small
        while True:
            # Save to BytesIO with current quality
            output = BytesIO()
            img.save(output, format='JPEG', quality=quality)
            data = output.getvalue()
            if len(data) <= max_size_bytes:
                return ContentFile(data, name='profile.jpg')
            # Reduce dimensions by 10% and lower quality
            width = int(width * 0.9)
            height = int(height * 0.9)
            if width < 50 or height < 50:
                break
            img = img.resize((width, height), Image.LANCZOS)
            quality = max(quality - 10, 20)

        raise ValidationError(
            f"Profile picture is too large. Please upload an image smaller than {MAX_SIZE_MB} MB."
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error processing profile picture: {e}")
        raise ValidationError(
            f"Profile picture is too large. Please upload an image smaller than {MAX_SIZE_MB} MB."
        )
