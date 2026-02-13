"""Integration tests for User Story 3: Notification Throttling.

Tests that the system correctly throttles notifications (max once per 6 hours)
and resets throttle when plants are watered.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.lib.config import MonitorConfig
from src.lib.moisture_monitor import MoistureMonitor


class TestNotificationThrottling:
    """Test notification throttling (User Story 3)."""

    @pytest.fixture
    def config(self):
        """Create test configuration with 6-hour throttle."""
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

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_notification_sent_only_once_within_6_hours(self, mock_sensor_class, config):
        """Test that notification sent max once per 6-hour window.

        Scenario:
        - Cycle 1: Plant-A dry (30%) → notification sent
        - Cycle 2 (1 hour later): Plant-A still dry (25%) → throttled (no notification)
        - Cycle 3 (3 hours later): Plant-A still dry (20%) → throttled (no notification)
        - Cycle 4 (7 hours total): Plant-A still dry (15%) → notification sent (window expired)

        Expected:
        - Only 2 notifications sent (cycle 1 and cycle 4)
        - Cycles 2 and 3 throttled
        """
        # Setup mock sensor - Plant-A always dry
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(return_value=30.0)
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Cycle 1: Plant-A dry → notification sent
            mock_sensor.read_moisture = Mock(return_value=30.0)
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 1
            first_notification_time = monitor.plants[0].last_notification_time
            assert first_notification_time is not None

            # Cycle 2 (1 hour later): Still dry → throttled
            mock_notifier.send_notification.reset_mock()
            mock_sensor.read_moisture = Mock(return_value=25.0)
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=1)
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 0  # Throttled

            # Cycle 3 (4 hours total): Still dry → throttled
            mock_sensor.read_moisture = Mock(return_value=20.0)
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=4)
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 0  # Still throttled

            # Cycle 4 (7 hours total): Still dry → notification sent (window expired)
            mock_sensor.read_moisture = Mock(return_value=15.0)
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=7)
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 1  # Window expired, sent

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_throttle_reset_when_plant_watered(self, mock_sensor_class, config):
        """Test that throttle resets when plant moisture rises above threshold + 5%.

        Scenario:
        - Cycle 1: Plant-A dry (30%) → notification sent, throttle active
        - User waters plant
        - Cycle 2 (30 min later): Plant-A moisture 50% (above 45% reset threshold) → throttle reset
        - Cycle 3: Plant-A dries to 35% → notification sent immediately (throttle was reset)

        Expected:
        - Cycle 1: Notification sent
        - Cycle 2: Throttle timer cleared when moisture > 45%
        - Cycle 3: Notification sent (no throttle)
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

            # Cycle 1: Plant-A dry (30%) → notification sent
            mock_sensor.read_moisture = Mock(return_value=30.0)
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 1
            assert monitor.plants[0].last_notification_time is not None

            # Cycle 2 (30 min later): Plant-A watered, moisture 50%
            mock_notifier.send_notification.reset_mock()
            mock_sensor.read_moisture = Mock(return_value=50.0)
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(minutes=30)
            monitor.monitor_cycle()

            # Verify throttle was reset (moisture > threshold + 5% = 45%)
            assert monitor.plants[0].last_notification_time is None
            assert mock_notifier.send_notification.call_count == 0  # Not dry, no notification

            # Cycle 3: Plant-A dries to 35% → notification sent immediately
            mock_sensor.read_moisture = Mock(return_value=35.0)
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 1  # Not throttled

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_throttle_reset_threshold_with_hysteresis(self, mock_sensor_class, config):
        """Test that throttle reset requires threshold + 5% hysteresis buffer.

        Scenario:
        - Plant threshold: 40%
        - Throttle reset threshold: 45% (40% + 5%)
        - Test moisture values: 43%, 44%, 45%, 46%

        Expected:
        - 43% and 44%: Throttle NOT reset (below 45%)
        - 45% and 46%: Throttle reset (at or above 45%)
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

            # Set initial throttle (simulate prior notification)
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=1)

            # Test 43% → throttle NOT reset
            mock_sensor.read_moisture = Mock(return_value=43.0)
            monitor.monitor_cycle()
            assert monitor.plants[0].last_notification_time is not None

            # Test 44% → throttle NOT reset
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=1)
            mock_sensor.read_moisture = Mock(return_value=44.0)
            monitor.monitor_cycle()
            assert monitor.plants[0].last_notification_time is not None

            # Test 45% (exactly at threshold) → throttle reset
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=1)
            mock_sensor.read_moisture = Mock(return_value=45.0)
            monitor.monitor_cycle()
            assert monitor.plants[0].last_notification_time is None  # Reset!

            # Test 46% → throttle reset
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(hours=1)
            mock_sensor.read_moisture = Mock(return_value=46.0)
            monitor.monitor_cycle()
            assert monitor.plants[0].last_notification_time is None  # Reset!

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_failed_notification_does_not_set_throttle(self, mock_sensor_class, config):
        """Test that throttle timer NOT set if notification fails.

        Scenario:
        - Cycle 1: Plant-A dry, notification fails (ntfy.sh error) → throttle NOT set
        - Cycle 2 (1 min later): Plant-A still dry → notification retried immediately

        Expected:
        - Cycle 1: Notification attempted, failed, no throttle set
        - Cycle 2: Notification retried (not throttled)
        """
        # Setup mock sensor - Plant-A always dry
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(return_value=30.0)
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier with failure then success
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            # First call fails, second succeeds
            mock_notifier.send_notification = Mock(
                side_effect=[
                    {'success': False, 'status_code': 500, 'error': 'Server error'},
                    {'success': True, 'status_code': 200}
                ]
            )
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Cycle 1: Notification fails
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 1
            assert monitor.plants[0].last_notification_time is None  # No throttle on failure

            # Cycle 2 (1 min later): Notification retried
            monitor.monitor_cycle()

            assert mock_notifier.send_notification.call_count == 2  # Retried
            assert monitor.plants[0].last_notification_time is not None  # Throttle set on success

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_throttle_duration_configurable(self, mock_sensor_class):
        """Test that throttle duration respects configuration.

        Scenario:
        - Config with 1-hour throttle (3600 seconds)
        - Plant-A dry, notification sent
        - 30 minutes later: throttled
        - 61 minutes later: notification sent

        Expected:
        - Throttle window matches config value
        """
        # Create config with 1-hour throttle (instead of 6 hours)
        short_config = MonitorConfig(
            moisture_threshold=40.0,
            moisture_voltage_dry=3.0,
            moisture_voltage_wet=1.6,
            sampling_interval=60,
            throttle_duration=3600,  # 1 hour
            ntfy_url="https://ntfy.sh",
            ntfy_topic="test-plants",
            log_level="INFO",
            ads1115_address=0x48,
            ads1115_gain=1
        )

        # Setup mock sensor - always dry
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(return_value=30.0)
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor with short throttle
            monitor = MoistureMonitor(short_config)

            # Cycle 1: Notification sent
            monitor.monitor_cycle()
            assert mock_notifier.send_notification.call_count == 1

            # Cycle 2 (30 min later): Throttled (within 1-hour window)
            mock_notifier.send_notification.reset_mock()
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(minutes=30)
            monitor.monitor_cycle()
            assert mock_notifier.send_notification.call_count == 0  # Throttled

            # Cycle 3 (61 min total): Notification sent (window expired)
            monitor.plants[0].last_notification_time = datetime.utcnow() - timedelta(minutes=61)
            monitor.monitor_cycle()
            assert mock_notifier.send_notification.call_count == 1  # Window expired

    @patch('src.lib.moisture_monitor.SensorReader')
    @patch('src.lib.moisture_monitor.SENSOR_AVAILABLE', True)
    def test_throttle_prevents_notification_spam(self, mock_sensor_class, config):
        """Test that throttle prevents repeated notifications for persistent dry condition.

        Scenario:
        - Plant-A continuously dry for 10 cycles over 5 hours
        - Without throttle: 10 notifications (spam)
        - With 6-hour throttle: 1 notification only

        Expected:
        - Only 1 notification sent across all 10 cycles
        """
        # Setup mock sensor - always dry
        mock_sensor = Mock()
        mock_sensor.read_moisture = Mock(return_value=30.0)
        mock_sensor_class.return_value = mock_sensor

        # Mock notifier
        with patch('src.lib.moisture_monitor.NtfyClient') as mock_notifier_class:
            mock_notifier = Mock()
            mock_notifier.send_notification = Mock(return_value={'success': True, 'status_code': 200})
            mock_notifier_class.return_value = mock_notifier

            # Create monitor
            monitor = MoistureMonitor(config)

            # Run 10 monitoring cycles over 5 hours (30-min intervals)
            total_notifications = 0
            for i in range(10):
                # Simulate time passing (30 min per cycle)
                if i > 0 and monitor.plants[0].last_notification_time is not None:
                    monitor.plants[0].last_notification_time = (
                        datetime.utcnow() - timedelta(minutes=30 * i)
                    )

                monitor.monitor_cycle()
                total_notifications += mock_notifier.send_notification.call_count
                mock_notifier.send_notification.reset_mock()

            # Verify only 1 notification sent (not 10)
            assert total_notifications == 1
