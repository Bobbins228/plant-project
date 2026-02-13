"""
Unit tests for image validation (format, size).

Tests the image_handler module's validation logic for uploaded
plant profile images.
"""

import pytest
from pathlib import Path
from io import BytesIO
from PIL import Image


@pytest.fixture
def valid_jpeg_bytes():
    """Create a valid JPEG image in memory."""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def valid_png_bytes():
    """Create a valid PNG image in memory."""
    img = Image.new('RGB', (100, 100), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def oversized_image_bytes():
    """Create a >10MB image."""
    # Create a very large image (3000x3000 uncompressed should exceed 10MB)
    img = Image.new('RGB', (3000, 3000), color='green')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()


def test_validate_image_format_accepts_jpeg(valid_jpeg_bytes):
    """
    Test that JPEG format is accepted.

    Scenario:
    - User uploads a valid JPEG image
    - Image validation is called

    Expected:
    - Validation passes
    - No exception raised
    """
    from src.lib.image_handler import validate_image_format

    # Should not raise exception
    validate_image_format(valid_jpeg_bytes, filename="test.jpg")


def test_validate_image_format_accepts_png(valid_png_bytes):
    """
    Test that PNG format is accepted.

    Scenario:
    - User uploads a valid PNG image
    - Image validation is called

    Expected:
    - Validation passes
    - No exception raised
    """
    from src.lib.image_handler import validate_image_format

    # Should not raise exception
    validate_image_format(valid_png_bytes, filename="test.png")


def test_validate_image_format_rejects_invalid_format():
    """
    Test that non-image files are rejected.

    Scenario:
    - User uploads a non-image file (e.g., text file)
    - Image validation is called

    Expected:
    - ValidationError raised
    - Error message indicates invalid format
    """
    from src.lib.image_handler import validate_image_format, ValidationError

    invalid_data = b"This is not an image file"

    with pytest.raises(ValidationError) as exc_info:
        validate_image_format(invalid_data, filename="test.txt")

    assert "Invalid file format" in str(exc_info.value)


def test_validate_image_format_rejects_svg():
    """
    Test that SVG files are rejected (not supported).

    Scenario:
    - User uploads an SVG file
    - Image validation is called

    Expected:
    - ValidationError raised
    - Only JPEG, PNG, GIF, WebP accepted
    """
    from src.lib.image_handler import validate_image_format, ValidationError

    svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>'

    with pytest.raises(ValidationError) as exc_info:
        validate_image_format(svg_data, filename="test.svg")

    assert "Invalid file format" in str(exc_info.value) or "Accepted formats" in str(exc_info.value)


def test_validate_image_size_accepts_small_image(valid_jpeg_bytes):
    """
    Test that images under 10MB are accepted.

    Scenario:
    - User uploads a 100x100 pixel JPEG (<1MB)
    - Size validation is called

    Expected:
    - Validation passes
    - No exception raised
    """
    from src.lib.image_handler import validate_image_size

    # Should not raise exception
    validate_image_size(valid_jpeg_bytes)


def test_validate_image_size_rejects_large_image(oversized_image_bytes):
    """
    Test that images over 10MB are rejected.

    Scenario:
    - User uploads a >10MB image
    - Size validation is called

    Expected:
    - ValidationError raised
    - Error message indicates size limit exceeded
    """
    from src.lib.image_handler import validate_image_size, ValidationError

    with pytest.raises(ValidationError) as exc_info:
        validate_image_size(oversized_image_bytes)

    assert "10 MB" in str(exc_info.value) or "size" in str(exc_info.value).lower()


def test_validate_image_comprehensive(valid_jpeg_bytes):
    """
    Test comprehensive validation (format + size).

    Scenario:
    - User uploads a valid JPEG under 10MB
    - Full validation is called

    Expected:
    - Both format and size validation pass
    - No exception raised
    """
    from src.lib.image_handler import validate_image

    # Should not raise exception
    validate_image(valid_jpeg_bytes, filename="test.jpg")


def test_save_plant_image_generates_correct_path(valid_jpeg_bytes, tmp_path):
    """
    Test that plant image is saved with correct filename.

    Scenario:
    - Valid image uploaded for plant with ID 5
    - Image is saved

    Expected:
    - File saved as plant_5.jpg in images directory
    - File exists and is readable
    - Returns correct relative path
    """
    from src.lib.image_handler import save_plant_image

    plant_id = 5
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    # Act
    image_path = save_plant_image(
        image_data=valid_jpeg_bytes,
        plant_id=plant_id,
        filename="upload.jpg",
        images_dir=str(images_dir)
    )

    # Assert
    assert image_path == "plant_5.jpg"
    saved_file = images_dir / "plant_5.jpg"
    assert saved_file.exists()
    assert saved_file.stat().st_size > 0


def test_delete_plant_image_removes_file(valid_jpeg_bytes, tmp_path):
    """
    Test that plant image is deleted from filesystem.

    Scenario:
    - Plant has an existing image file
    - Image deletion is requested

    Expected:
    - File is removed from filesystem
    - No error if file doesn't exist (idempotent)
    """
    from src.lib.image_handler import save_plant_image, delete_plant_image

    plant_id = 3
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    # Arrange: Save an image
    save_plant_image(
        image_data=valid_jpeg_bytes,
        plant_id=plant_id,
        filename="test.jpg",
        images_dir=str(images_dir)
    )

    image_path = images_dir / "plant_3.jpg"
    assert image_path.exists()

    # Act: Delete image
    delete_plant_image(plant_id=plant_id, images_dir=str(images_dir))

    # Assert: File removed
    assert not image_path.exists()


def test_delete_plant_image_idempotent(tmp_path):
    """
    Test that deleting non-existent image doesn't raise error.

    Scenario:
    - Plant has no image
    - Image deletion is requested

    Expected:
    - No exception raised
    - Operation is idempotent
    """
    from src.lib.image_handler import delete_plant_image

    images_dir = tmp_path / "images"
    images_dir.mkdir()

    # Should not raise exception
    delete_plant_image(plant_id=999, images_dir=str(images_dir))
