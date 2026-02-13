"""Unit tests for PlantProfile model validation.

Tests the PlantProfile dataclass validation logic, attribute constraints,
and from_db_row() factory method.
"""

import pytest
from datetime import date


class TestPlantProfileValidation:
    """Test PlantProfile model validation."""

    def test_valid_plant_profile_creation(self):
        """Test creating a valid PlantProfile."""
        # This will fail until we implement src/models/plant_profile.py
        from src.models.plant_profile import PlantProfile

        profile = PlantProfile(
            plant_name="Basil",
            sensor_channel=0,
            acceptable_moisture_level=45.0
        )

        assert profile.plant_name == "Basil"
        assert profile.sensor_channel == 0
        assert profile.acceptable_moisture_level == 45.0
        assert profile.current_moisture_level is None
        assert profile.needs_watering is False
        assert profile.date_last_watered is None

    def test_sensor_channel_validation_valid(self):
        """Test that sensor_channel accepts valid values (0, 1, 2)."""
        from src.models.plant_profile import PlantProfile

        # Should not raise for valid channels
        for channel in [0, 1, 2]:
            profile = PlantProfile(
                plant_name="Test",
                sensor_channel=channel,
                acceptable_moisture_level=45.0
            )
            assert profile.sensor_channel == channel

    def test_sensor_channel_validation_invalid(self):
        """Test that sensor_channel rejects invalid values."""
        from src.models.plant_profile import PlantProfile

        with pytest.raises(ValueError, match="sensor_channel must be 0, 1, or 2"):
            PlantProfile(
                plant_name="Invalid",
                sensor_channel=5,
                acceptable_moisture_level=45.0
            )

    def test_acceptable_moisture_level_validation_valid(self):
        """Test that acceptable_moisture_level accepts valid percentages (0-100)."""
        from src.models.plant_profile import PlantProfile

        # Should not raise for valid thresholds
        for threshold in [0.0, 50.0, 100.0]:
            profile = PlantProfile(
                plant_name="Test",
                sensor_channel=0,
                acceptable_moisture_level=threshold
            )
            assert profile.acceptable_moisture_level == threshold

    def test_acceptable_moisture_level_validation_too_low(self):
        """Test that acceptable_moisture_level rejects negative values."""
        from src.models.plant_profile import PlantProfile

        with pytest.raises(ValueError, match="acceptable_moisture_level must be 0-100%"):
            PlantProfile(
                plant_name="Invalid",
                sensor_channel=0,
                acceptable_moisture_level=-10.0
            )

    def test_acceptable_moisture_level_validation_too_high(self):
        """Test that acceptable_moisture_level rejects values > 100."""
        from src.models.plant_profile import PlantProfile

        with pytest.raises(ValueError, match="acceptable_moisture_level must be 0-100%"):
            PlantProfile(
                plant_name="Invalid",
                sensor_channel=0,
                acceptable_moisture_level=150.0
            )

    def test_current_moisture_level_validation_valid(self):
        """Test that current_moisture_level accepts valid percentages or None."""
        from src.models.plant_profile import PlantProfile

        # Should not raise for valid moisture
        for moisture in [None, 0.0, 50.0, 100.0]:
            profile = PlantProfile(
                plant_name="Test",
                sensor_channel=0,
                acceptable_moisture_level=45.0,
                current_moisture_level=moisture
            )
            assert profile.current_moisture_level == moisture

    def test_current_moisture_level_validation_invalid(self):
        """Test that current_moisture_level rejects values outside 0-100."""
        from src.models.plant_profile import PlantProfile

        with pytest.raises(ValueError, match="current_moisture_level must be 0-100% or None"):
            PlantProfile(
                plant_name="Invalid",
                sensor_channel=0,
                acceptable_moisture_level=45.0,
                current_moisture_level=150.0
            )

    def test_plant_name_validation_empty(self):
        """Test that plant_name rejects empty strings."""
        from src.models.plant_profile import PlantProfile

        with pytest.raises(ValueError, match="plant_name must be 1-50 characters"):
            PlantProfile(
                plant_name="",
                sensor_channel=0,
                acceptable_moisture_level=45.0
            )

    def test_plant_name_validation_too_long(self):
        """Test that plant_name rejects strings > 50 characters."""
        from src.models.plant_profile import PlantProfile

        long_name = "A" * 51

        with pytest.raises(ValueError, match="plant_name must be 1-50 characters"):
            PlantProfile(
                plant_name=long_name,
                sensor_channel=0,
                acceptable_moisture_level=45.0
            )

    def test_plant_name_validation_valid_length(self):
        """Test that plant_name accepts 1-50 character strings."""
        from src.models.plant_profile import PlantProfile

        valid_name = "A" * 50  # Exactly 50 characters

        profile = PlantProfile(
            plant_name=valid_name,
            sensor_channel=0,
            acceptable_moisture_level=45.0
        )

        assert profile.plant_name == valid_name


class TestPlantProfileFromDbRow:
    """Test PlantProfile.from_db_row() factory method."""

    def test_from_db_row_complete_data(self):
        """Test from_db_row() with all fields populated."""
        from src.models.plant_profile import PlantProfile

        # Simulate sqlite3.Row as dict
        row = {
            'plant_name': 'Basil',
            'sensor_channel': 0,
            'acceptable_moisture_level': 45.0,
            'current_moisture_level': 42.5,
            'needs_watering': 0,
            'date_last_watered': '2026-02-13'
        }

        profile = PlantProfile.from_db_row(row)

        assert profile.plant_name == 'Basil'
        assert profile.sensor_channel == 0
        assert profile.acceptable_moisture_level == 45.0
        assert profile.current_moisture_level == 42.5
        assert profile.needs_watering is False
        assert profile.date_last_watered == date(2026, 2, 13)

    def test_from_db_row_null_optional_fields(self):
        """Test from_db_row() with NULL optional fields."""
        from src.models.plant_profile import PlantProfile

        row = {
            'plant_name': 'Tomato',
            'sensor_channel': 1,
            'acceptable_moisture_level': 35.0,
            'current_moisture_level': None,
            'needs_watering': 1,
            'date_last_watered': None
        }

        profile = PlantProfile.from_db_row(row)

        assert profile.plant_name == 'Tomato'
        assert profile.sensor_channel == 1
        assert profile.acceptable_moisture_level == 35.0
        assert profile.current_moisture_level is None
        assert profile.needs_watering is True
        assert profile.date_last_watered is None

    def test_from_db_row_needs_watering_boolean_conversion(self):
        """Test that needs_watering INTEGER is converted to boolean."""
        from src.models.plant_profile import PlantProfile

        # SQLite stores as 0/1, Python expects True/False
        row_false = {
            'plant_name': 'Test1',
            'sensor_channel': 0,
            'acceptable_moisture_level': 45.0,
            'current_moisture_level': None,
            'needs_watering': 0,
            'date_last_watered': None
        }

        row_true = {
            'plant_name': 'Test2',
            'sensor_channel': 1,
            'acceptable_moisture_level': 45.0,
            'current_moisture_level': None,
            'needs_watering': 1,
            'date_last_watered': None
        }

        profile_false = PlantProfile.from_db_row(row_false)
        profile_true = PlantProfile.from_db_row(row_true)

        assert profile_false.needs_watering is False
        assert profile_true.needs_watering is True
