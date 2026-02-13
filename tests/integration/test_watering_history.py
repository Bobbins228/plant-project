"""Integration tests for watering history tracking.

Tests the automatic detection and recording of watering events when
moisture levels rise above threshold after being dry.
"""

import tempfile
import os
import pytest
from datetime import date
from unittest.mock import Mock, patch


class TestWateringEventDetection:
    """Test automatic watering event detection and recording."""

    @pytest.fixture
    def temp_db_with_plant(self):
        """Create database with a single plant profile."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        from src.lib.database import initialize_database, create_plant_profile
        initialize_database(path)

        # Create a plant with 40% threshold
        create_plant_profile("TestPlant", 0, 40.0, path)

        yield path

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for monitoring."""
        config = Mock()
        config.moisture_threshold = 40.0
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

    def test_watering_event_detected_when_moisture_rises_above_threshold(
        self, temp_db_with_plant, mock_config
    ):
        """Test that watering event is recorded when moisture rises above threshold (T049)."""
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.database import (
            update_current_moisture,
            set_needs_watering_flag,
            load_profile_by_channel
        )

        # Set up plant as dry (below threshold)
        update_current_moisture("TestPlant", 30.0, temp_db_with_plant)
        set_needs_watering_flag("TestPlant", True, temp_db_with_plant)

        # Verify initial state
        profile = load_profile_by_channel(0, temp_db_with_plant)
        assert profile.current_moisture_level == 30.0
        assert profile.needs_watering is True
        assert profile.date_last_watered is None

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plant)

            # Simulate watering - plant moisture rises above threshold + hysteresis (45%)
            monitor.plants[0].current_moisture = 50.0
            monitor.plants[0].last_notification_time = Mock()  # Simulate previous notification

            # Trigger threshold check
            monitor.check_thresholds()

            # Verify watering event was recorded
            profile = load_profile_by_channel(0, temp_db_with_plant)
            assert profile.date_last_watered == date.today().isoformat()
            assert profile.needs_watering is False

    def test_date_last_watered_not_updated_when_moisture_stays_below_threshold(
        self, temp_db_with_plant, mock_config
    ):
        """Test that date_last_watered is NOT updated when moisture stays dry (T050)."""
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.database import (
            update_current_moisture,
            set_needs_watering_flag,
            load_profile_by_channel
        )

        # Set up plant as dry (below threshold)
        update_current_moisture("TestPlant", 30.0, temp_db_with_plant)
        set_needs_watering_flag("TestPlant", True, temp_db_with_plant)

        # Verify initial state - no watering recorded
        profile = load_profile_by_channel(0, temp_db_with_plant)
        assert profile.date_last_watered is None

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plant)

            # Plant stays dry - moisture remains below threshold
            monitor.plants[0].current_moisture = 35.0  # Still below 40% threshold
            monitor.plants[0].last_notification_time = Mock()  # Simulate previous notification

            # Trigger threshold check
            monitor.check_thresholds()

            # Verify date_last_watered still None (no watering detected)
            profile = load_profile_by_channel(0, temp_db_with_plant)
            assert profile.date_last_watered is None
            assert profile.needs_watering is True  # Still needs water

    def test_watering_event_only_recorded_when_crossing_throttle_reset_threshold(
        self, temp_db_with_plant, mock_config
    ):
        """Test that watering event requires crossing throttle_reset_threshold (threshold + 5%)."""
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.database import (
            update_current_moisture,
            set_needs_watering_flag,
            load_profile_by_channel
        )

        # Set up plant as dry
        update_current_moisture("TestPlant", 30.0, temp_db_with_plant)
        set_needs_watering_flag("TestPlant", True, temp_db_with_plant)

        with patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', False):
            monitor = MoistureMonitor(mock_config, db_path=temp_db_with_plant)

            # Plant moisture rises slightly above threshold but not above reset threshold
            # Threshold: 40%, Reset threshold: 45%
            monitor.plants[0].current_moisture = 42.0  # Above 40% but below 45%
            monitor.plants[0].last_notification_time = Mock()

            # Trigger threshold check
            monitor.check_thresholds()

            # Verify watering event NOT recorded (didn't cross reset threshold)
            profile = load_profile_by_channel(0, temp_db_with_plant)
            assert profile.date_last_watered is None

            # Now simulate crossing reset threshold
            monitor.plants[0].current_moisture = 46.0  # Above 45% reset threshold

            # Trigger threshold check again
            monitor.check_thresholds()

            # Verify watering event recorded
            profile = load_profile_by_channel(0, temp_db_with_plant)
            assert profile.date_last_watered == date.today().isoformat()
            assert profile.needs_watering is False
