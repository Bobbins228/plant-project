"""Image handler module for plant profile images.

Provides validation and storage logic for uploaded plant images.
Supports JPEG, PNG, GIF, WebP formats with 10 MB size limit.
"""

import logging
from pathlib import Path
from typing import Optional
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

# Configuration
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class ValidationError(Exception):
    """Raised when image validation fails."""
    pass


def validate_image_format(image_data: bytes, filename: str) -> None:
    """Validate that image data is a supported format.

    Args:
        image_data: Raw image file bytes
        filename: Original filename (for extension checking)

    Raises:
        ValidationError: If format is not supported

    Supported formats: JPEG, PNG, GIF, WebP
    """
    # Check file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Invalid file format. Accepted formats: JPEG, PNG, GIF, WebP. "
            f"Got extension: {file_ext}"
        )

    # Verify actual image format using PIL
    try:
        img = Image.open(BytesIO(image_data))
        img_format = img.format

        if img_format not in ALLOWED_FORMATS:
            raise ValidationError(
                f"Invalid file format. Accepted formats: JPEG, PNG, GIF, WebP. "
                f"Detected format: {img_format}"
            )

        logger.debug(f"Image format validated: {img_format}")

    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Invalid image file: {str(e)}")


def validate_image_size(image_data: bytes) -> None:
    """Validate that image size is within limit.

    Args:
        image_data: Raw image file bytes

    Raises:
        ValidationError: If size exceeds 10 MB limit
    """
    size_bytes = len(image_data)
    size_mb = size_bytes / (1024 * 1024)

    if size_bytes > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"File size exceeds 10 MB limit. "
            f"Got: {size_mb:.2f} MB"
        )

    logger.debug(f"Image size validated: {size_mb:.2f} MB")


def validate_image(image_data: bytes, filename: str) -> None:
    """Comprehensive image validation (format + size).

    Args:
        image_data: Raw image file bytes
        filename: Original filename

    Raises:
        ValidationError: If validation fails
    """
    validate_image_format(image_data, filename)
    validate_image_size(image_data)


def save_plant_image(
    image_data: bytes,
    plant_id: int,
    filename: str,
    images_dir: str = "data/images"
) -> str:
    """Save plant image to filesystem.

    Validates image before saving. Overwrites existing image for the plant.

    Args:
        image_data: Raw image file bytes
        plant_id: Plant database ID
        filename: Original uploaded filename (for extension detection)
        images_dir: Directory to save images (default: data/images)

    Returns:
        Relative image path (e.g., "plant_5.jpg")

    Raises:
        ValidationError: If image validation fails
        IOError: If file write fails
    """
    # Validate image
    validate_image(image_data, filename)

    # Determine file extension from original filename
    file_ext = Path(filename).suffix.lower()
    if not file_ext:
        # Default to .jpg if no extension provided
        file_ext = ".jpg"

    # Generate standardized filename: plant_{id}.{ext}
    image_filename = f"plant_{plant_id}{file_ext}"
    image_path = Path(images_dir) / image_filename

    # Ensure images directory exists
    image_path.parent.mkdir(parents=True, exist_ok=True)

    # Save image
    try:
        image_path.write_bytes(image_data)
        logger.info(f"Saved plant image: {image_filename} ({len(image_data) / 1024:.1f} KB)")
        return image_filename

    except Exception as e:
        logger.error(f"Failed to save image {image_filename}: {e}")
        raise IOError(f"Failed to save image: {str(e)}")


def delete_plant_image(
    plant_id: int,
    images_dir: str = "data/images"
) -> bool:
    """Delete plant image from filesystem.

    Idempotent - does not raise error if file doesn't exist.

    Args:
        plant_id: Plant database ID
        images_dir: Directory containing images (default: data/images)

    Returns:
        True if file was deleted, False if file didn't exist
    """
    # Try all possible extensions
    for ext in ALLOWED_EXTENSIONS:
        image_path = Path(images_dir) / f"plant_{plant_id}{ext}"
        if image_path.exists():
            try:
                image_path.unlink()
                logger.info(f"Deleted plant image: plant_{plant_id}{ext}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete image plant_{plant_id}{ext}: {e}")
                # Continue to try other extensions

    logger.debug(f"No image found to delete for plant {plant_id}")
    return False


def get_image_path_for_plant(
    plant_id: int,
    images_dir: str = "data/images"
) -> Optional[str]:
    """Get the image filename for a plant if it exists.

    Args:
        plant_id: Plant database ID
        images_dir: Directory containing images (default: data/images)

    Returns:
        Relative image filename (e.g., "plant_5.jpg") or None if no image exists
    """
    # Check all possible extensions
    for ext in ALLOWED_EXTENSIONS:
        image_path = Path(images_dir) / f"plant_{plant_id}{ext}"
        if image_path.exists():
            return f"plant_{plant_id}{ext}"

    return None
