"""
Contract tests for plant API endpoints.

Verifies API responses match the OpenAPI specification in
contracts/api.yaml for plant CRUD operations.
"""

import pytest
import json
from datetime import date


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

    # Create test plant profiles
    create_plant_profile("Snake Plant", 0, 40.0, db_path)
    create_plant_profile("Boston Fern", 1, 45.0, db_path)

    # Create Flask app with test database
    app = create_app(db_path=db_path)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


def test_get_plants_returns_200_with_plant_list(test_client):
    """
    Test GET /api/plants returns 200 with list of plants.

    Contract: GET /api/plants
    Response: 200 OK with {plants: [PlantProfile]}
    """
    response = test_client.get('/api/plants')

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'plants' in data
    assert isinstance(data['plants'], list)
    assert len(data['plants']) >= 2  # At least the two test plants

    # Verify plant structure
    plant = data['plants'][0]
    assert 'id' in plant or 'plant_name' in plant
    assert 'sensor_channel' in plant
    assert 'acceptable_moisture_level' in plant
    assert 'current_moisture_level' in plant
    assert 'needs_watering' in plant
    assert 'image_path' in plant


def test_get_plant_by_id_returns_200_for_existing_plant(test_client):
    """
    Test GET /api/plants/{id} returns 200 for existing plant.

    Contract: GET /api/plants/{id}
    Response: 200 OK with PlantProfile object
    """
    # First, get list to find a valid plant name
    list_response = test_client.get('/api/plants')
    plants = json.loads(list_response.data)['plants']
    plant_name = plants[0].get('plant_name') or plants[0].get('id')

    # Get single plant
    response = test_client.get(f'/api/plants/{plant_name}')

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    plant = json.loads(response.data)
    assert plant.get('plant_name') or plant.get('id')
    assert 'sensor_channel' in plant
    assert 'acceptable_moisture_level' in plant


def test_get_plant_by_id_returns_404_for_nonexistent_plant(test_client):
    """
    Test GET /api/plants/{id} returns 404 for nonexistent plant.

    Contract: GET /api/plants/999
    Response: 404 Not Found with {error: "..."}
    """
    response = test_client.get('/api/plants/NonexistentPlant123')

    assert response.status_code == 404
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
    assert 'not found' in data['error'].lower() or 'Plant with ID' in data['error']


def test_post_plants_creates_new_plant(test_client):
    """
    Test POST /api/plants creates new plant profile.

    Contract: POST /api/plants
    Request: {plant_name, sensor_channel, acceptable_moisture_level}
    Response: 201 Created with PlantProfile object
    """
    new_plant = {
        'plant_name': 'Money Plant',
        'sensor_channel': 2,
        'acceptable_moisture_level': 35
    }

    response = test_client.post(
        '/api/plants',
        data=json.dumps(new_plant),
        content_type='application/json'
    )

    assert response.status_code == 201
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert data['plant_name'] == 'Money Plant'
    assert data['sensor_channel'] == 2
    assert data['acceptable_moisture_level'] == 35


def test_post_plants_returns_400_for_duplicate_channel(test_client):
    """
    Test POST /api/plants returns 400 for duplicate sensor channel.

    Contract: POST /api/plants with channel already in use
    Response: 400 Bad Request with {error: "..."}
    """
    # Channel 0 is already used by "Snake Plant"
    duplicate_channel_plant = {
        'plant_name': 'Another Plant',
        'sensor_channel': 0,
        'acceptable_moisture_level': 40
    }

    response = test_client.post(
        '/api/plants',
        data=json.dumps(duplicate_channel_plant),
        content_type='application/json'
    )

    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
    assert 'channel' in data['error'].lower() or 'already' in data['error'].lower()


def test_post_plants_returns_400_for_invalid_threshold(test_client):
    """
    Test POST /api/plants returns 400 for invalid threshold.

    Contract: POST /api/plants with threshold outside 0-100 range
    Response: 400 Bad Request with {error: "..."}
    """
    invalid_plant = {
        'plant_name': 'Invalid Plant',
        'sensor_channel': 3,
        'acceptable_moisture_level': 150  # Invalid: > 100
    }

    response = test_client.post(
        '/api/plants',
        data=json.dumps(invalid_plant),
        content_type='application/json'
    )

    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data


def test_put_plant_updates_existing_plant(test_client):
    """
    Test PUT /api/plants/{id} updates plant profile.

    Contract: PUT /api/plants/{id}
    Request: {plant_name?, sensor_channel?, acceptable_moisture_level?}
    Response: 200 OK with updated PlantProfile
    """
    # Get existing plant name
    list_response = test_client.get('/api/plants')
    plants = json.loads(list_response.data)['plants']
    plant_name = plants[0]['plant_name']

    # Update plant
    update_data = {
        'acceptable_moisture_level': 50
    }

    response = test_client.put(
        f'/api/plants/{plant_name}',
        data=json.dumps(update_data),
        content_type='application/json'
    )

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert data['acceptable_moisture_level'] == 50


def test_put_plant_returns_404_for_nonexistent_plant(test_client):
    """
    Test PUT /api/plants/{id} returns 404 for nonexistent plant.

    Contract: PUT /api/plants/999
    Response: 404 Not Found with {error: "..."}
    """
    update_data = {
        'acceptable_moisture_level': 45
    }

    response = test_client.put(
        '/api/plants/NonexistentPlant999',
        data=json.dumps(update_data),
        content_type='application/json'
    )

    assert response.status_code == 404
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data


def test_delete_plant_removes_plant(test_client):
    """
    Test DELETE /api/plants/{id} deletes plant profile.

    Contract: DELETE /api/plants/{id}
    Response: 204 No Content
    """
    # Create a third plant so we can delete one without violating "last plant" rule
    test_client.post(
        '/api/plants',
        data=json.dumps({
            'plant_name': 'Temporary Plant',
            'sensor_channel': 2,
            'acceptable_moisture_level': 40
        }),
        content_type='application/json'
    )

    # Delete the temporary plant
    response = test_client.delete('/api/plants/Temporary Plant')

    assert response.status_code == 204
    assert len(response.data) == 0  # No content


def test_delete_plant_returns_400_for_last_plant(test_client):
    """
    Test DELETE /api/plants/{id} returns 400 when trying to delete last plant.

    Contract: DELETE /api/plants/{id} when only 1 plant exists
    Response: 400 Bad Request with {error: "Cannot delete the last plant..."}
    """
    # Get all plants
    list_response = test_client.get('/api/plants')
    plants = json.loads(list_response.data)['plants']

    # Delete all but one plant
    for plant in plants[1:]:
        test_client.delete(f'/api/plants/{plant["plant_name"]}')

    # Try to delete the last plant
    last_plant_name = plants[0]['plant_name']
    response = test_client.delete(f'/api/plants/{last_plant_name}')

    assert response.status_code == 400
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
    assert 'last plant' in data['error'].lower() or 'at least one' in data['error'].lower()


def test_delete_plant_returns_404_for_nonexistent_plant(test_client):
    """
    Test DELETE /api/plants/{id} returns 404 for nonexistent plant.

    Contract: DELETE /api/plants/999
    Response: 404 Not Found with {error: "..."}
    """
    response = test_client.delete('/api/plants/NonexistentPlant999')

    assert response.status_code == 404
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'error' in data
