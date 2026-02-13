"""
Contract tests for plant image upload endpoints.

Verifies API responses match the OpenAPI specification in
contracts/api.yaml for image management operations.
"""

import pytest
import json
from io import BytesIO
from PIL import Image


@pytest.fixture
def test_client():
    """Create Flask test client with test database."""
    from src.lib.web_server import create_app
    from src.lib.database import initialize_database, create_plant_profile
    import tempfile
    import os

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Initialize test database
    initialize_database(db_path)

    # Create test plant profile
    create_plant_profile("Test Plant", 0, 40.0, db_path)

    # Create Flask app with test database
    app = create_app(db_path=db_path)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def valid_image_file():
    """Create a valid JPEG image file."""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer


def test_post_plant_image_uploads_successfully(test_client, valid_image_file):
    """
    Test POST /api/plants/{id}/image uploads image successfully.

    Contract: POST /api/plants/{id}/image
    Request: multipart/form-data with image file
    Response: 200 OK with {image_path, message}
    """
    response = test_client.post(
        '/api/plants/Test Plant/image',
        data={'image': (valid_image_file, 'test.jpg')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'image_path' in data
    assert 'message' in data
    assert data['image_path'].endswith('.jpg') or data['image_path'].endswith('.jpeg')


def test_post_plant_image_returns_400_for_invalid_format(test_client):
    """
    Test POST /api/plants/{id}/image returns 400 for invalid format.

    Contract: POST /api/plants/{id}/image with non-image file
    Response: 400 Bad Request with {error: "Invalid file format..."}
    """
    invalid_file = BytesIO(b"This is not an image")

    response = test_client.post(
        '/api/plants/Test Plant/image',
        data={'image': (invalid_file, 'test.txt')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
    assert 'format' in data['error'].lower() or 'invalid' in data['error'].lower()


def test_post_plant_image_returns_400_for_oversized_file(test_client):
    """
    Test POST /api/plants/{id}/image returns 400 for oversized file.

    Contract: POST /api/plants/{id}/image with file >10 MB
    Response: 400 Bad Request with {error: "File size exceeds..."}
    """
    # Create a large image (>10 MB)
    large_img = Image.new('RGB', (5000, 5000), color='blue')
    buffer = BytesIO()
    large_img.save(buffer, format='PNG')
    buffer.seek(0)

    response = test_client.post(
        '/api/plants/Test Plant/image',
        data={'image': (buffer, 'large.png')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
    assert '10 MB' in data['error'] or 'size' in data['error'].lower()


def test_post_plant_image_returns_404_for_nonexistent_plant(test_client, valid_image_file):
    """
    Test POST /api/plants/{id}/image returns 404 for nonexistent plant.

    Contract: POST /api/plants/999/image
    Response: 404 Not Found with {error: "Plant not found"}
    """
    response = test_client.post(
        '/api/plants/NonexistentPlant/image',
        data={'image': (valid_image_file, 'test.jpg')},
        content_type='multipart/form-data'
    )

    assert response.status_code == 404
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data


def test_delete_plant_image_removes_image(test_client, valid_image_file):
    """
    Test DELETE /api/plants/{id}/image removes image successfully.

    Contract: DELETE /api/plants/{id}/image
    Response: 204 No Content
    """
    # First upload an image
    test_client.post(
        '/api/plants/Test Plant/image',
        data={'image': (valid_image_file, 'test.jpg')},
        content_type='multipart/form-data'
    )

    # Then delete it
    response = test_client.delete('/api/plants/Test Plant/image')

    assert response.status_code == 204
    assert len(response.data) == 0  # No content


def test_delete_plant_image_returns_404_for_nonexistent_plant(test_client):
    """
    Test DELETE /api/plants/{id}/image returns 404 for nonexistent plant.

    Contract: DELETE /api/plants/999/image
    Response: 404 Not Found with {error: "Plant not found"}
    """
    response = test_client.delete('/api/plants/NonexistentPlant/image')

    assert response.status_code == 404
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
