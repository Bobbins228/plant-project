"""Integration test for single plant watering notification.

Tests User Story 1: Automatic Watering Alerts
Verifies that when a plant's moisture drops below threshold,
a notification is sent via ntfy.sh.

Per constitution: These tests must be written FIRST and FAIL before implementation.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.models.plant import Plant


class TestSinglePlantAlert:
    """Integration tests for single plant notification workflow."""

    def test_plant_below_threshold_sends_notification(self):
        """Test that plant below threshold triggers notification.

        User Story 1, Scenario 1:
        GIVEN Plant-A soil moisture is at 50%
        WHEN moisture drops to 38%
        THEN notification is sent to ntfy.sh stating "Plant-A needs watering (moisture: 38%)"
        """
        # This will fail until MoistureMonitor is implemented
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.config import MonitorConfig

        # Setup
        config = MonitorConfig(
            moisture_threshold=40.0,
            moisture_voltage_dry=3.0,
            moisture_voltage_wet=1.6,
            sampling_interval=30,
            throttle_duration=21600,
            ntfy_topic='test-topic',
            ntfy_url='https://ntfy.sh',
            log_level='INFO',
            ads1115_address=0x48,
            ads1115_gain=1
        )

        monitor = MoistureMonitor(config)

        # Create plant with low moisture
        plant = Plant(id='Plant-A', ads_channel=0, min_moisture_threshold=40.0)
        plant.current_moisture = 38.0  # Below threshold

        # Mock ntfy.sh API
        with patch('src.lib.notifier.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'test'}
            mock_post.return_value = mock_response

            # Check threshold and send notification
            result = monitor.send_notification(plant)

            # Verify notification sent
            assert result['success'] is True
            assert mock_post.called

            # Verify message format
            call_args = mock_post.call_args
            message = call_args[1]['data'].decode('utf-8')
            assert 'Plant-A' in message
            assert 'needs watering' in message
            assert '38%' in message

    def test_plant_already_dry_on_startup_notifies_immediately(self):
        """Test that plant already dry on startup sends immediate notification.

        User Story 1, Scenario 2:
        GIVEN Plant-B soil moisture is at 35% (already low)
        WHEN system starts monitoring
        THEN notification is sent immediately for Plant-B
        """
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.config import MonitorConfig

        config = MonitorConfig(
            moisture_threshold=40.0,
            moisture_voltage_dry=3.0,
            moisture_voltage_wet=1.6,
            sampling_interval=30,
            throttle_duration=21600,
            ntfy_topic='test-topic',
            ntfy_url='https://ntfy.sh',
            log_level='INFO',
            ads1115_address=0x48,
            ads1115_gain=1
        )

        # Plant already dry (35% < 40% threshold)
        plant = Plant(id='Plant-B', ads_channel=1, min_moisture_threshold=40.0)
        plant.current_moisture = 35.0

        # Verify needs_water is True
        assert plant.needs_water is True

        # Mock notification
        with patch('src.lib.notifier.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'id': 'test'}
            mock_post.return_value = mock_response

            monitor = MoistureMonitor(config)
            result = monitor.send_notification(plant)

            # Verify immediate notification
            assert result['success'] is True
            assert mock_post.called

            # Verify Plant-B in message
            message = mock_post.call_args[1]['data'].decode('utf-8')
            assert 'Plant-B' in message
            assert '35%' in message

    def test_all_plants_above_threshold_no_notification(self):
        """Test that plants above threshold don't trigger notifications.

        User Story 1, Scenario 3:
        GIVEN all three plants have adequate moisture (above 40%)
        WHEN system monitors for 24 hours
        THEN no notifications are sent
        """
        from src.lib.moisture_monitor import MoistureMonitor
        from src.lib.config import MonitorConfig

        config = MonitorConfig(
            moisture_threshold=40.0,
            moisture_voltage_dry=3.0,
            moisture_voltage_wet=1.6,
            sampling_interval=30,
            throttle_duration=21600,
            ntfy_topic='test-topic',
            ntfy_url='https://ntfy.sh',
            log_level='INFO',
            ads1115_address=0x48,
            ads1115_gain=1
        )

        # All plants above threshold
        plants = [
            Plant(id='Plant-A', ads_channel=0, min_moisture_threshold=40.0, current_moisture=55.0),
            Plant(id='Plant-B', ads_channel=1, min_moisture_threshold=40.0, current_moisture=48.0),
            Plant(id='Plant-C', ads_channel=2, min_moisture_threshold=40.0, current_moisture=62.0),
        ]

        # Verify none need water
        for plant in plants:
            assert plant.needs_water is False

        # Mock notification (should not be called)
        with patch('src.lib.notifier.requests.post') as mock_post:
            monitor = MoistureMonitor(config)

            # Check each plant
            for plant in plants:
                if plant.needs_water:
                    monitor.send_notification(plant)

            # Verify no notifications sent
            assert mock_post.call_count == 0

    def test_needs_water_property_correctly_identifies_dry_plant(self):
        """Test Plant.needs_water property correctly identifies dry conditions."""
        # Plant below threshold
        plant_dry = Plant(id='Plant-A', ads_channel=0, min_moisture_threshold=40.0)
        plant_dry.current_moisture = 35.0
        assert plant_dry.needs_water is True

        # Plant at threshold (edge case)
        plant_edge = Plant(id='Plant-B', ads_channel=1, min_moisture_threshold=40.0)
        plant_edge.current_moisture = 40.0
        assert plant_edge.needs_water is False  # Exactly at threshold = not dry

        # Plant above threshold
        plant_ok = Plant(id='Plant-C', ads_channel=2, min_moisture_threshold=40.0)
        plant_ok.current_moisture = 50.0
        assert plant_ok.needs_water is False

        # Plant with no reading yet
        plant_no_reading = Plant(id='Plant-A', ads_channel=0)
        assert plant_no_reading.current_moisture is None
        assert plant_no_reading.needs_water is False  # No reading = no alert
