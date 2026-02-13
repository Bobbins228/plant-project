"""
Contract tests for environmental API endpoints.

Verifies API responses match the OpenAPI specification in
contracts/api.yaml for environmental data queries.
"""

import pytest
import json
from datetime import datetime


@pytest.fixture
def test_client_with_env_data():
    """Create Flask test client with test database and environmental data."""
    from src.lib.web_server import create_app
    from src.lib.database import initialize_database, persist_environmental_reading
    import tempfile
    import os

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Initialize test database
    initialize_database(db_path)

    # Ensure environmental_readings table exists
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environmental_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            gas_resistance REAL,
            UNIQUE(timestamp)
        )
    """)
    conn.commit()
    conn.close()

    # Insert test environmental reading
    persist_environmental_reading(
        timestamp=datetime.now(),
        temperature=22.45,
        humidity=55.67,
        pressure=1013.25,
        gas_resistance=12345.67,
        db_path=db_path
    )

    # Create Flask app with test database
    app = create_app(db_path=db_path)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def test_client_no_env_data():
    """Create Flask test client with empty environmental data."""
    from src.lib.web_server import create_app
    from src.lib.database import initialize_database
    import tempfile
    import os

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Initialize test database
    initialize_database(db_path)

    # Ensure environmental_readings table exists but is empty
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environmental_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            gas_resistance REAL,
            UNIQUE(timestamp)
        )
    """)
    conn.commit()
    conn.close()

    # Create Flask app with test database
    app = create_app(db_path=db_path)
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


def test_get_environmental_latest_returns_200_with_reading(test_client_with_env_data):
    """
    Test GET /api/environmental/latest returns 200 when data exists.

    Contract: GET /api/environmental/latest
    Response: 200 OK with EnvironmentalReading object
    """
    response = test_client_with_env_data.get('/api/environmental/latest')

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'id' in data
    assert 'timestamp' in data
    assert 'temperature' in data
    assert 'humidity' in data
    assert 'pressure' in data
    assert 'gas_resistance' in data

    # Verify data types
    assert isinstance(data['temperature'], (int, float))
    assert isinstance(data['humidity'], (int, float))
    assert isinstance(data['pressure'], (int, float))
    assert isinstance(data['gas_resistance'], (int, float))


def test_get_environmental_latest_returns_204_when_no_data(test_client_no_env_data):
    """
    Test GET /api/environmental/latest returns 204 when no data exists.

    Contract: GET /api/environmental/latest
    Response: 204 No Content (sensor not connected or no readings yet)
    """
    response = test_client_no_env_data.get('/api/environmental/latest')

    assert response.status_code == 204
    assert len(response.data) == 0  # No content


def test_get_environmental_history_returns_200_with_readings(test_client_with_env_data):
    """
    Test GET /api/environmental/history returns 200 with readings list.

    Contract: GET /api/environmental/history
    Response: 200 OK with {readings: [EnvironmentalReading]}
    """
    response = test_client_with_env_data.get('/api/environmental/history')

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'readings' in data
    assert isinstance(data['readings'], list)

    if len(data['readings']) > 0:
        reading = data['readings'][0]
        assert 'id' in reading
        assert 'timestamp' in reading
        assert 'temperature' in reading
        assert 'humidity' in reading
        assert 'pressure' in reading
        assert 'gas_resistance' in reading


def test_get_environmental_history_returns_empty_list_when_no_data(test_client_no_env_data):
    """
    Test GET /api/environmental/history returns empty list when no data.

    Contract: GET /api/environmental/history
    Response: 200 OK with {readings: []}
    """
    response = test_client_no_env_data.get('/api/environmental/history')

    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'readings' in data
    assert data['readings'] == []
