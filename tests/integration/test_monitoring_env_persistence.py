"""
Integration test for monitoring system persisting environmental data.

Verifies that the monitoring system writes environmental readings
to the database after each monitoring cycle.
"""

import pytest
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test_plants.db"

    # Initialize database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create plant_profiles table
    cursor.execute("""
        CREATE TABLE plant_profiles (
            plant_name TEXT PRIMARY KEY,
            sensor_channel INTEGER NOT NULL UNIQUE,
            acceptable_moisture_level REAL NOT NULL,
            current_moisture_level REAL,
            needs_watering INTEGER NOT NULL DEFAULT 0,
            date_last_watered TEXT,
            image_path TEXT,
            CHECK (sensor_channel IN (0, 1, 2, 3)),
            CHECK (acceptable_moisture_level >= 0.0 AND acceptable_moisture_level <= 100.0)
        )
    """)

    # Create environmental_readings table
    cursor.execute("""
        CREATE TABLE environmental_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            temperature REAL,
            humidity REAL,
            pressure REAL,
            gas_resistance REAL,
            UNIQUE(timestamp)
        )
    """)

    cursor.execute("""
        CREATE INDEX idx_timestamp ON environmental_readings(timestamp)
    """)

    conn.commit()
    conn.close()

    yield str(db_path)


def test_environmental_data_persisted_to_database(test_db):
    """
    Test that environmental readings are persisted to database.

    Scenario:
    - Monitoring system has environmental sensor data available
    - Monitoring cycle completes
    - Environmental reading is written to database with timestamp

    Expected:
    - environmental_readings table contains new row
    - All sensor values (temperature, humidity, pressure, gas) are stored
    - Timestamp is ISO 8601 format
    """
    from src.lib.database import persist_environmental_reading

    # Arrange: Sample environmental sensor data
    env_data = {
        "temperature": 22.45,
        "humidity": 55.67,
        "pressure": 1013.25,
        "gas_resistance": 12345.67
    }
    timestamp = datetime.now()

    # Act: Persist environmental reading
    persist_environmental_reading(
        timestamp=timestamp,
        temperature=env_data["temperature"],
        humidity=env_data["humidity"],
        pressure=env_data["pressure"],
        gas_resistance=env_data["gas_resistance"],
        db_path=test_db
    )

    # Assert: Reading exists in database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, temperature, humidity, pressure, gas_resistance
        FROM environmental_readings
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    assert row is not None, "No environmental reading found in database"
    assert row[1] == pytest.approx(22.45, rel=0.01)  # temperature
    assert row[2] == pytest.approx(55.67, rel=0.01)  # humidity
    assert row[3] == pytest.approx(1013.25, rel=0.01)  # pressure
    assert row[4] == pytest.approx(12345.67, rel=0.01)  # gas_resistance


def test_environmental_data_cleanup_old_readings(test_db):
    """
    Test that old environmental readings (>1 hour) are cleaned up.

    Scenario:
    - Environmental readings older than 1 hour exist in database
    - New reading is persisted
    - Cleanup function runs

    Expected:
    - Only readings from last 60 minutes remain
    - Older readings are deleted
    """
    from src.lib.database import persist_environmental_reading, cleanup_old_environmental_readings
    from datetime import timedelta

    # Arrange: Insert old and recent readings
    now = datetime.now()
    old_timestamp = now - timedelta(hours=2)
    recent_timestamp = now - timedelta(minutes=30)

    persist_environmental_reading(
        timestamp=old_timestamp,
        temperature=20.0,
        humidity=50.0,
        pressure=1010.0,
        gas_resistance=10000.0,
        db_path=test_db
    )

    persist_environmental_reading(
        timestamp=recent_timestamp,
        temperature=22.0,
        humidity=55.0,
        pressure=1013.0,
        gas_resistance=12000.0,
        db_path=test_db
    )

    # Act: Run cleanup
    cleanup_old_environmental_readings(db_path=test_db)

    # Assert: Only recent reading remains
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM environmental_readings")
    count = cursor.fetchone()[0]
    conn.close()

    assert count == 1, f"Expected 1 reading after cleanup, found {count}"


def test_environmental_sensor_unavailable_graceful_handling(test_db):
    """
    Test that missing environmental sensor is handled gracefully.

    Scenario:
    - Environmental sensor is not connected or fails
    - Monitoring cycle completes normally for moisture readings
    - No environmental reading is persisted

    Expected:
    - Moisture monitoring continues unaffected
    - No crash or error
    - Database remains consistent (no partial writes)
    """
    from src.lib.database import persist_environmental_reading

    # Arrange: All sensor values are None (sensor unavailable)
    timestamp = datetime.now()

    # Act: Persist with all None values
    persist_environmental_reading(
        timestamp=timestamp,
        temperature=None,
        humidity=None,
        pressure=None,
        gas_resistance=None,
        db_path=test_db
    )

    # Assert: Reading exists but with NULL values
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT temperature, humidity, pressure, gas_resistance
        FROM environmental_readings
        WHERE timestamp = ?
    """, (timestamp.isoformat(),))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, "No reading found for sensor unavailable case"
    assert all(v is None for v in row), "Expected all NULL values when sensor unavailable"
