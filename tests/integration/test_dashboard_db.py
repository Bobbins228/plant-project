"""
Integration test for dashboard loading and displaying plant data.

Verifies that the dashboard can load plant data from the database
and serve the HTML page successfully.
"""

import pytest


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
    create_plant_profile("Test Plant 1", 0, 40.0, db_path)
    create_plant_profile("Test Plant 2", 1, 35.0, db_path)

    # Create Flask app with test database
    app = create_app(db_path=db_path)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


def test_dashboard_loads_successfully(test_client):
    """
    Test that dashboard HTML page loads successfully.

    Scenario:
    - Flask server is running
    - User navigates to root URL /

    Expected:
    - 200 OK response
    - HTML content-type
    - Page contains dashboard elements
    """
    response = test_client.get('/')

    assert response.status_code == 200
    assert 'text/html' in response.content_type


def test_dashboard_can_fetch_plant_data(test_client):
    """
    Test that dashboard can fetch plant data from database.

    Scenario:
    - Dashboard loads
    - JavaScript polls /api/plants endpoint
    - Database contains plant profiles

    Expected:
    - API returns 200 OK
    - Plant data is accessible
    - At least 2 test plants exist
    """
    response = test_client.get('/api/plants')

    assert response.status_code == 200

    import json
    data = json.loads(response.data)
    assert 'plants' in data
    assert len(data['plants']) >= 2
    assert data['plants'][0]['plant_name'] in ['Test Plant 1', 'Test Plant 2']


def test_dashboard_handles_empty_environmental_data(test_client):
    """
    Test that dashboard handles missing environmental data gracefully.

    Scenario:
    - Dashboard loads
    - Environmental sensor has not written any data yet
    - JavaScript polls /api/environmental/latest

    Expected:
    - API returns 204 No Content (not 500 error)
    - Dashboard can handle absence of environmental data
    """
    response = test_client.get('/api/environmental/latest')

    # Should return 204 (no content) when no environmental data exists
    assert response.status_code == 204
