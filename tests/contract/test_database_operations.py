"""Contract tests for database CRUD operations.

Tests create_plant_profile, load_all_profiles, load_profile_by_channel,
and other database operations to ensure they meet contract specifications.
"""

import sqlite3
import tempfile
import os
import pytest
from pathlib import Path


class TestCreatePlantProfile:
    """Test create_plant_profile operation."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        # Initialize schema
        from src.lib.database import initialize_database
        initialize_database(path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_create_profile_valid_data(self, temp_db):
        """Test creating a plant profile with valid data (T014)."""
        from src.lib.database import create_plant_profile, load_all_profiles

        # Create profile
        create_plant_profile(
            plant_name="Basil",
            sensor_channel=0,
            acceptable_moisture_level=45.0,
            db_path=temp_db
        )

        # Verify it was created correctly
        profiles = load_all_profiles(temp_db)
        assert len(profiles) == 1

        profile = profiles[0]
        assert profile.plant_name == "Basil"
        assert profile.sensor_channel == 0
        assert profile.acceptable_moisture_level == 45.0
        assert profile.current_moisture_level is None
        assert profile.needs_watering is False
        assert profile.date_last_watered is None

    def test_create_profile_duplicate_plant_name(self, temp_db):
        """Test that duplicate plant names are rejected (T015)."""
        from src.lib.database import create_plant_profile

        # Create first profile
        create_plant_profile(
            plant_name="Basil",
            sensor_channel=0,
            acceptable_moisture_level=45.0,
            db_path=temp_db
        )

        # Try to create duplicate - should fail
        with pytest.raises(sqlite3.IntegrityError):
            create_plant_profile(
                plant_name="Basil",  # Duplicate name
                sensor_channel=1,
                acceptable_moisture_level=50.0,
                db_path=temp_db
            )

    def test_create_profile_duplicate_sensor_channel(self, temp_db):
        """Test that duplicate sensor channels are rejected (T016)."""
        from src.lib.database import create_plant_profile

        # Create first profile
        create_plant_profile(
            plant_name="Basil",
            sensor_channel=0,
            acceptable_moisture_level=45.0,
            db_path=temp_db
        )

        # Try to create with duplicate channel - should fail
        with pytest.raises(sqlite3.IntegrityError):
            create_plant_profile(
                plant_name="Tomato",
                sensor_channel=0,  # Duplicate channel
                acceptable_moisture_level=40.0,
                db_path=temp_db
            )

    def test_create_profile_invalid_sensor_channel(self, temp_db):
        """Test that invalid sensor channels are rejected."""
        from src.lib.database import create_plant_profile

        # Try to create with invalid channel - should fail at validation
        with pytest.raises(ValueError, match="sensor_channel must be 0, 1, or 2"):
            create_plant_profile(
                plant_name="Invalid",
                sensor_channel=5,  # Invalid channel
                acceptable_moisture_level=45.0,
                db_path=temp_db
            )

    def test_create_profile_invalid_threshold(self, temp_db):
        """Test that invalid thresholds are rejected."""
        from src.lib.database import create_plant_profile

        # Try to create with invalid threshold - should fail at validation
        with pytest.raises(ValueError, match="acceptable_moisture_level must be 0-100%"):
            create_plant_profile(
                plant_name="Invalid",
                sensor_channel=0,
                acceptable_moisture_level=150.0,  # Invalid threshold
                db_path=temp_db
            )


class TestLoadAllProfiles:
    """Test load_all_profiles operation."""

    @pytest.fixture
    def temp_db_with_profiles(self):
        """Create a temporary database with sample profiles."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)

        # Create sample profiles
        create_plant_profile("Basil", 0, 45.0, path)
        create_plant_profile("Tomato", 1, 35.0, path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_load_all_profiles_multiple(self, temp_db_with_profiles):
        """Test loading multiple profiles ordered by sensor_channel (T017)."""
        from src.lib.database import load_all_profiles

        profiles = load_all_profiles(temp_db_with_profiles)

        assert len(profiles) == 2

        # Verify order by sensor_channel
        assert profiles[0].plant_name == "Basil"
        assert profiles[0].sensor_channel == 0

        assert profiles[1].plant_name == "Tomato"
        assert profiles[1].sensor_channel == 1

    def test_load_all_profiles_empty(self):
        """Test loading profiles from empty database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, load_all_profiles
        initialize_database(path)

        try:
            profiles = load_all_profiles(path)
            assert profiles == []
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestLoadProfileByChannel:
    """Test load_profile_by_channel operation."""

    @pytest.fixture
    def temp_db_with_profiles(self):
        """Create a temporary database with sample profiles."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)

        # Create sample profiles
        create_plant_profile("Basil", 0, 45.0, path)
        create_plant_profile("Tomato", 1, 35.0, path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_load_profile_by_channel_exists(self, temp_db_with_profiles):
        """Test loading profile for mapped sensor channel."""
        from src.lib.database import load_profile_by_channel

        profile = load_profile_by_channel(0, temp_db_with_profiles)

        assert profile is not None
        assert profile.plant_name == "Basil"
        assert profile.sensor_channel == 0

    def test_load_profile_by_channel_unmapped(self, temp_db_with_profiles):
        """Test loading profile for unmapped sensor channel returns None."""
        from src.lib.database import load_profile_by_channel

        profile = load_profile_by_channel(2, temp_db_with_profiles)

        assert profile is None


class TestUpdateCurrentMoisture:
    """Test update_current_moisture operation."""

    @pytest.fixture
    def temp_db_with_profile(self):
        """Create a temporary database with one profile."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)
        create_plant_profile("Basil", 0, 45.0, path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_update_current_moisture(self, temp_db_with_profile):
        """Test updating plant's current moisture reading."""
        from src.lib.database import update_current_moisture, load_profile_by_channel

        # Update moisture
        success = update_current_moisture("Basil", 42.5, temp_db_with_profile)
        assert success is True

        # Verify update
        profile = load_profile_by_channel(0, temp_db_with_profile)
        assert profile.current_moisture_level == 42.5


class TestSetNeedsWateringFlag:
    """Test set_needs_watering_flag operation."""

    @pytest.fixture
    def temp_db_with_profile(self):
        """Create a temporary database with one profile."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)
        create_plant_profile("Basil", 0, 45.0, path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_set_needs_watering_true(self, temp_db_with_profile):
        """Test setting needs_watering flag to True."""
        from src.lib.database import set_needs_watering_flag, load_profile_by_channel

        # Set flag to True
        success = set_needs_watering_flag("Basil", True, temp_db_with_profile)
        assert success is True

        # Verify update
        profile = load_profile_by_channel(0, temp_db_with_profile)
        assert profile.needs_watering is True

    def test_set_needs_watering_false(self, temp_db_with_profile):
        """Test setting needs_watering flag to False."""
        from src.lib.database import set_needs_watering_flag, load_profile_by_channel

        # Set to True first
        set_needs_watering_flag("Basil", True, temp_db_with_profile)

        # Then set to False
        success = set_needs_watering_flag("Basil", False, temp_db_with_profile)
        assert success is True

        # Verify update
        profile = load_profile_by_channel(0, temp_db_with_profile)
        assert profile.needs_watering is False


class TestRecordWateringEvent:
    """Test record_watering_event operation."""

    @pytest.fixture
    def temp_db_with_profile(self):
        """Create a temporary database with one profile needing water."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile, set_needs_watering_flag
        initialize_database(path)
        create_plant_profile("Basil", 0, 45.0, path)
        set_needs_watering_flag("Basil", True, path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_record_watering_event(self, temp_db_with_profile):
        """Test recording a watering event."""
        from datetime import date
        from src.lib.database import record_watering_event, load_profile_by_channel

        # Record watering
        today = date.today()
        success = record_watering_event("Basil", today, temp_db_with_profile)
        assert success is True

        # Verify update
        profile = load_profile_by_channel(0, temp_db_with_profile)
        assert profile.needs_watering is False
        assert profile.date_last_watered == today
