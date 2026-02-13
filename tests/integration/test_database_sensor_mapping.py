"""Integration tests for sensor-to-plant mapping.

Tests the sensor channel to plant profile mapping functionality,
ensuring correct plant names are returned for sensor channels.
"""

import tempfile
import os
import pytest


class TestSensorToPlantMapping:
    """Test sensor channel to plant profile mapping."""

    @pytest.fixture
    def temp_db_with_named_profiles(self):
        """Create database with named plant profiles on specific channels."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)

        # Create profiles with meaningful names
        create_plant_profile("Tomato", 0, 35.0, path)
        create_plant_profile("Basil", 1, 45.0, path)
        # Channel 2 left unmapped

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_sensor_mapping_returns_correct_plant_names(self, temp_db_with_named_profiles):
        """Test that sensor channels map to correct plant names (T031)."""
        from src.lib.database import load_profile_by_channel

        # Channel 0 -> Tomato
        profile0 = load_profile_by_channel(0, temp_db_with_named_profiles)
        assert profile0 is not None
        assert profile0.plant_name == "Tomato"
        assert profile0.sensor_channel == 0

        # Channel 1 -> Basil
        profile1 = load_profile_by_channel(1, temp_db_with_named_profiles)
        assert profile1 is not None
        assert profile1.plant_name == "Basil"
        assert profile1.sensor_channel == 1

        # Channel 2 -> Unmapped (None)
        profile2 = load_profile_by_channel(2, temp_db_with_named_profiles)
        assert profile2 is None

    def test_load_all_profiles_returns_plant_names_in_channel_order(self, temp_db_with_named_profiles):
        """Test that load_all_profiles returns profiles ordered by sensor channel."""
        from src.lib.database import load_all_profiles

        profiles = load_all_profiles(temp_db_with_named_profiles)

        assert len(profiles) == 2

        # Should be ordered by sensor_channel (0, 1)
        assert profiles[0].plant_name == "Tomato"
        assert profiles[0].sensor_channel == 0

        assert profiles[1].plant_name == "Basil"
        assert profiles[1].sensor_channel == 1

    def test_unmapped_channels_handled_gracefully(self, temp_db_with_named_profiles):
        """Test that unmapped sensor channels return None."""
        from src.lib.database import load_profile_by_channel

        # Channel 2 is not mapped
        profile = load_profile_by_channel(2, temp_db_with_named_profiles)
        assert profile is None

        # Invalid channel numbers
        for invalid_channel in [-1, 3, 5, 10]:
            # Should not crash, just return None or raise ValueError
            try:
                result = load_profile_by_channel(invalid_channel, temp_db_with_named_profiles)
                # If it doesn't raise, it should return None
                assert result is None
            except ValueError:
                # Validation error is also acceptable
                pass
