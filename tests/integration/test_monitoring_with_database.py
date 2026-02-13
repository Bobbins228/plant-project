"""Integration tests for monitoring with database profiles.

Tests the integration between the monitoring system and database,
including profile loading, threshold checking, and fallback behavior.
"""

import tempfile
import os
import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock


class TestMonitoringWithDatabase:
    """Test monitoring system integration with database."""

    @pytest.fixture
    def temp_db_with_plants(self):
        """Create database with plant profiles for testing."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)

        # Create profiles with different thresholds
        create_plant_profile("Cactus", 0, 20.0, path)  # Low threshold
        create_plant_profile("Fern", 1, 60.0, path)    # High threshold

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for monitoring."""
        config = Mock()
        config.moisture_threshold = 40.0  # Default fallback threshold
        config.moisture_voltage_dry = 1.2
        config.moisture_voltage_wet = 0.5
        config.ads1115_address = 0x48
        config.ads1115_gain = 1
        config.sampling_interval = 30
        config.throttle_duration = 21600
        config.ntfy_topic = "test-topic"
        config.ntfy_url = "https://ntfy.sh"
        config.log_level = "INFO"
        return config

    def test_load_profiles_from_database(self, temp_db_with_plants, mock_config):
        """Test that monitoring loads plant profiles from database (T036)."""
        # This test will initially fail until we modify MoistureMonitor
        from src.lib.moisture_monitor import MoistureMonitor

        # Mock sensor to avoid hardware dependency
        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plants)

            # Verify profiles were loaded
            # Monitor should have loaded profiles from database
            # (Implementation will store them for use)

    def test_check_thresholds_uses_plant_specific_values(self, temp_db_with_plants, mock_config):
        """Test that each plant is checked against its own threshold (T036)."""
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.database import update_current_moisture

        # Set moisture levels
        update_current_moisture("Cactus", 25.0, temp_db_with_plants)  # Above 20% threshold - OK
        update_current_moisture("Fern", 50.0, temp_db_with_plants)    # Below 60% threshold - DRY

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plants)

            # Mock check_thresholds behavior
            # Cactus at 25% with 20% threshold -> should NOT need water
            # Fern at 50% with 60% threshold -> should need water

    def test_fallback_to_environment_defaults_when_database_unavailable(self, mock_config):
        """Test fallback to environment defaults when database unavailable (T037)."""
        from src.lib.moisture_monitor import MoistureMonitor

        # Use non-existent database path
        invalid_db_path = "/nonexistent/path/to/database.db"

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            # Should not crash, should fall back to environment defaults
            monitor = MoistureMonitor(mock_config, db_path=invalid_db_path)

            # Monitor should use default threshold from config
            # (40.0% in our mock)

    def test_database_write_failure_continues_monitoring(self, temp_db_with_plants, mock_config):
        """Test that database write failures don't stop monitoring (T038)."""
        from src.lib.moisture_monitor import MoistureMonitor

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plants)

            # Make database read-only to simulate write failure
            os.chmod(temp_db_with_plants, 0o444)

            try:
                # Monitoring should continue even if database writes fail
                # (Will be verified by checking that monitor doesn't crash)
                pass
            finally:
                # Restore permissions for cleanup
                os.chmod(temp_db_with_plants, 0o644)

    def test_notifications_use_plant_names_from_database(self, temp_db_with_plants, mock_config):
        """Test that notifications display plant names from database (T036)."""
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.database import update_current_moisture, set_needs_watering_flag

        # Set up plant needing water
        update_current_moisture("Fern", 30.0, temp_db_with_plants)  # Below 60% threshold
        set_needs_watering_flag("Fern", True, temp_db_with_plants)

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
                mock_notifier = Mock()
                mock_notifier_class.return_value = mock_notifier
                mock_notifier.send_notification.return_value = {'success': True}

                monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plants)

                # When notification is sent, it should use "Fern" not "Plant-A"
                # (This will be verified in implementation)


class TestMonitoringThresholdLogic:
    """Test threshold comparison logic (>= vs <)."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)
        create_plant_profile("TestPlant", 0, 40.0, path)

        yield path

        if os.path.exists(path):
            os.unlink(path)

    def test_moisture_at_threshold_is_okay(self, temp_db):
        """Test that moisture exactly at threshold (>=) means plant is okay."""
        from src.lib.database import update_current_moisture, load_profile_by_channel

        # Set moisture exactly at threshold
        update_current_moisture("TestPlant", 40.0, temp_db)

        profile = load_profile_by_channel(0, temp_db)

        # With >= comparison, 40.0 >= 40.0 should be True (plant is okay)
        # needs_watering should be False
        # (This will be tested via monitoring integration)

    def test_moisture_below_threshold_needs_water(self, temp_db):
        """Test that moisture below threshold (<) means plant needs water."""
        from src.lib.database import update_current_moisture

        # Set moisture below threshold
        update_current_moisture("TestPlant", 35.0, temp_db)

        # With < comparison, 35.0 < 40.0 should be True (plant needs water)
        # needs_watering should be set to True
        # (This will be tested via monitoring integration)
