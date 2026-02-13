"""Contract tests for database schema creation and initialization.

Tests database schema creation, table structure, and pragma settings
to ensure the database meets the specification requirements.
"""

import sqlite3
import tempfile
import os
import pytest
from pathlib import Path


class TestDatabaseSchema:
    """Test database schema creation and structure."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_initialize_database_creates_table(self, temp_db):
        """Test that initialize_database() creates the plant_profiles table."""
        # This will fail until we implement src/lib/database.py
        from src.lib.database import initialize_database

        initialize_database(temp_db)

        # Verify table exists
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='plant_profiles'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "plant_profiles table should exist"
        assert result[0] == 'plant_profiles'

    def test_schema_has_correct_columns(self, temp_db):
        """Test that plant_profiles table has all required columns with correct types."""
        from src.lib.database import initialize_database

        initialize_database(temp_db)

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(plant_profiles)")
        columns = cursor.fetchall()
        conn.close()

        # Convert to dict for easier testing
        column_dict = {col[1]: col[2] for col in columns}  # col[1]=name, col[2]=type

        # Verify required columns exist with correct types
        assert 'plant_name' in column_dict
        assert column_dict['plant_name'] == 'TEXT'

        assert 'sensor_channel' in column_dict
        assert column_dict['sensor_channel'] == 'INTEGER'

        assert 'acceptable_moisture_level' in column_dict
        assert column_dict['acceptable_moisture_level'] == 'REAL'

        assert 'current_moisture_level' in column_dict
        assert column_dict['current_moisture_level'] == 'REAL'

        assert 'needs_watering' in column_dict
        assert column_dict['needs_watering'] == 'INTEGER'

        assert 'date_last_watered' in column_dict
        assert column_dict['date_last_watered'] == 'TEXT'

    def test_primary_key_constraint(self, temp_db):
        """Test that plant_name is the primary key."""
        from src.lib.database import initialize_database

        initialize_database(temp_db)

        conn = sqlite3.connect(temp_db)

        # Insert first profile
        conn.execute("""
            INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
            VALUES ('Basil', 0, 45.0, 0)
        """)
        conn.commit()

        # Try to insert duplicate plant_name - should fail
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed.*plant_name"):
            conn.execute("""
                INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
                VALUES ('Basil', 1, 50.0, 0)
            """)
            conn.commit()

        conn.close()

    def test_sensor_channel_unique_constraint(self, temp_db):
        """Test that sensor_channel has UNIQUE constraint."""
        from src.lib.database import initialize_database

        initialize_database(temp_db)

        conn = sqlite3.connect(temp_db)

        # Insert first profile
        conn.execute("""
            INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
            VALUES ('Basil', 0, 45.0, 0)
        """)
        conn.commit()

        # Try to insert duplicate sensor_channel - should fail
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed.*sensor_channel"):
            conn.execute("""
                INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
                VALUES ('Tomato', 0, 40.0, 0)
            """)
            conn.commit()

        conn.close()

    def test_check_constraint_sensor_channel_range(self, temp_db):
        """Test CHECK constraint for sensor_channel (must be 0, 1, or 2)."""
        from src.lib.database import initialize_database

        initialize_database(temp_db)

        conn = sqlite3.connect(temp_db)

        # Try to insert invalid sensor_channel - should fail
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute("""
                INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
                VALUES ('Invalid', 5, 45.0, 0)
            """)
            conn.commit()

        conn.close()

    def test_check_constraint_acceptable_moisture_range(self, temp_db):
        """Test CHECK constraint for acceptable_moisture_level (0-100%)."""
        from src.lib.database import initialize_database

        initialize_database(temp_db)

        conn = sqlite3.connect(temp_db)

        # Try to insert invalid threshold - should fail
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            conn.execute("""
                INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
                VALUES ('Invalid', 0, 150.0, 0)
            """)
            conn.commit()

        conn.close()

    def test_pragma_foreign_keys_enabled(self, temp_db):
        """Test that PRAGMA foreign_keys is ON."""
        from src.lib.database import get_db_connection

        with get_db_connection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()

            assert result[0] == 1, "PRAGMA foreign_keys should be ON (1)"

    def test_pragma_journal_mode_wal(self, temp_db):
        """Test that PRAGMA journal_mode is WAL."""
        from src.lib.database import get_db_connection

        with get_db_connection(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            result = cursor.fetchone()

            assert result[0].upper() == 'WAL', "PRAGMA journal_mode should be WAL"
