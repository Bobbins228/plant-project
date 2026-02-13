"""Integration tests for User Story 2: Multi-Plant Independent Monitoring.

Tests that the system correctly monitors 3 plants independently with distinct
notifications and state tracking.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.lib.config import MonitorConfig
from src.lib.moisture_monitor import MoistureMonitor
from src.models.plant import Plant


class TestMultiPlantMonitoring:
    """Test multi-plant independent monitoring (User Story 2)."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MonitorConfig(
            moisture_threshold=40.0,
            moisture_voltage_dry=3.0,
            moisture_voltage_wet=1.6,
            sampling_interval=60,
            throttle_duration=21600,  # 6 hours
            ntfy_url="https://ntfy.sh",
            ntfy_topic="test-plants",
            log_level="INFO",
            ads1115_address=0x48,
            ads1115_gain=1
        )

    @pytest.fixture
    def mock_sensor_readings(self):
        """Mock sensor to return specific moisture values per channel."""
        def side_effect(channel):
            # Plant-A: 25% (dry), Plant-B: 55% (ok), Plant-C: 30% (dry)
            moisture_map = {0: 25.0, 1: 55.0, 2: 30.0}
            return moisture_map.get(channel)
        return side_effect

    @pytest.fixture
    def mock_sensor_all_dry(self):
        """Mock sensor with all plants dry."""
        def side_effect(channel):
            # All plants below 40% threshold
            moisture_map = {0: 20.0, 1: 15.0, 2: 10.0}
            return moisture_map.get(channel)
        return side_effect

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_three_plants_monitored_independently(self, mock_sensor_class, config, mock_sensor_readings):
        """Test that all 3 plants are monitored with independent state.

        Scenario:
        - Plant-A: 25% (dry, needs notification)
        - Plant-B: 55% (ok, no notification)
        - Plant-C: 30% (dry, needs notification)

        Expected:
        - 3 sensor reads (one per plant)
        - 2 notifications sent (Plant-A and Plant-C)
        - Plant-B state updated but no notification
        - Each plant has independent moisture state
        """
        # Setup mock sensor
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(side_effect=mock_sensor_readings)
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Run one monitoring cycle
            monitor.monitor_cycle()

            # Verify sensor reads for all 3 plants
            assert mock_sensor.read_moisture.call_count == 3
            mock_sensor.read_moisture.assert_any_call(0)  # Plant-A
            mock_sensor.read_moisture.assert_any_call(1)  # Plant-B
            mock_sensor.read_moisture.assert_any_call(2)  # Plant-C

            # Verify plant states updated independently
            assert monitor.plants[0].current_moisture == 25.0  # Plant-A
            assert monitor.plants[1].current_moisture == 55.0  # Plant-B
            assert monitor.plants[2].current_moisture == 30.0  # Plant-C

            # Verify needs_water computed correctly per plant
            assert monitor.plants[0].needs_water is True   # Plant-A dry
            assert monitor.plants[1].needs_water is False  # Plant-B ok
            assert monitor.plants[2].needs_water is True   # Plant-C dry

            # Verify exactly 2 notifications sent (Plant-A and Plant-C)
            assert mock_notifier.send_notification.call_count == 2

            # Verify notification messages contain correct plant IDs
            calls = mock_notifier.send_notification.call_args_list
            messages = [call[1]['message'] for call in calls]
            assert any('Plant-A' in msg for msg in messages)
            assert any('Plant-C' in msg for msg in messages)
            assert not any('Plant-B' in msg for msg in messages)

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_all_plants_dry_simultaneous_notifications(self, mock_sensor_class, config, mock_sensor_all_dry):
        """Test that all 3 plants can send notifications simultaneously.

        Scenario: All 3 plants below threshold

        Expected:
        - 3 notifications sent (one per plant)
        - Each notification has correct plant ID
        - No interference between plants
        """
        # Setup mock sensor
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(side_effect=mock_sensor_all_dry)
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Run one monitoring cycle
            monitor.monitor_cycle()

            # Verify all 3 plants read
            assert mock_sensor.read_moisture.call_count == 3

            # Verify all 3 notifications sent
            assert mock_notifier.send_notification.call_count == 3

            # Verify each plant has distinct notification
            calls = mock_notifier.send_notification.call_args_list
            messages = [call[1]['message'] for call in calls]
            assert any('Plant-A' in msg for msg in messages)
            assert any('Plant-B' in msg for msg in messages)
            assert any('Plant-C' in msg for msg in messages)

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_independent_throttle_timers(self, mock_sensor_class, config):
        """Test that each plant has independent throttle state.

        Scenario:
        - Cycle 1: Plant-A dry (notified), Plant-B dry (notified), Plant-C ok
        - Cycle 2 (5 min later): Plant-A still dry, Plant-B still dry, Plant-C now dry

        Expected:
        - Cycle 1: 2 notifications (A, B)
        - Cycle 2: 1 notification (C only, A and B throttled)
        - Each plant tracks its own last_notification_time
        """
        # Setup mock sensor
        mock_sensor = Mock()
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Cycle 1: Plant-A dry, Plant-B dry, Plant-C ok
            mock_sensor.read_moisture = Mock(side_effect=lambda ch: {0: 25.0, 1: 30.0, 2: 50.0}.get(ch))
            monitor.monitor_cycle()

            # Verify 2 notifications sent
            assert mock_notifier.send_notification.call_count == 2

            # Verify throttle timers set for A and B only
            assert monitor.plants[0].last_notification_time is not None  # Plant-A
            assert monitor.plants[1].last_notification_time is not None  # Plant-B
            assert monitor.plants[2].last_notification_time is None      # Plant-C

            # Reset mock
            mock_notifier.send_notification.reset_mock()

            # Cycle 2 (5 min later): Plant-A still dry, Plant-B still dry, Plant-C now dry
            mock_sensor.read_moisture = Mock(side_effect=lambda ch: {0: 25.0, 1: 30.0, 2: 35.0}.get(ch))
            monitor.monitor_cycle()

            # Verify only 1 notification sent (Plant-C, others throttled)
            assert mock_notifier.send_notification.call_count == 1

            # Verify it was for Plant-C
            call_message = mock_notifier.send_notification.call_args[1]['message']
            assert 'Plant-C' in call_message

            # Verify throttle timer now set for C
            assert monitor.plants[2].last_notification_time is not None

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_sensor_failure_does_not_affect_other_plants(self, mock_sensor_class, config):
        """Test that sensor read failure on one plant doesn't stop monitoring others.

        Scenario:
        - Plant-A: sensor read fails (returns None)
        - Plant-B: 30% (dry)
        - Plant-C: 50% (ok)

        Expected:
        - Plant-A state not updated (current_moisture remains None)
        - Plant-B notification sent
        - Plant-C no notification
        - Monitoring continues normally
        """
        # Setup mock sensor with one failure
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(side_effect=lambda ch: {0: None, 1: 30.0, 2: 50.0}.get(ch))
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Run monitoring cycle
            monitor.monitor_cycle()

            # Verify Plant-A state not updated (still None)
            assert monitor.plants[0].current_moisture is None
            assert monitor.plants[0].needs_water is False  # None moisture = not dry

            # Verify Plant-B and Plant-C updated correctly
            assert monitor.plants[1].current_moisture == 30.0
            assert monitor.plants[2].current_moisture == 50.0

            # Verify only Plant-B notification sent
            assert mock_notifier.send_notification.call_count == 1
            call_message = mock_notifier.send_notification.call_args[1]['message']
            assert 'Plant-B' in call_message
