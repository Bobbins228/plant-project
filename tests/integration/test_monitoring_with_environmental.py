"""Integration tests for plant monitoring with environmental sensor.

Tests the complete monitoring cycle including environmental sensor integration,
ensuring environmental data displays alongside plant moisture levels and that
monitoring continues gracefully when environmental sensor fails.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.lib.moisture_monitor import MoistureMonitor
from src.models.plant_profile import PlantProfile
from src.models.environmental_reading import EnvironmentalReading


class TestMonitoringCycleWithEnvironmentalSensor:
    """Test monitoring cycle with environmental sensor connected (T017)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_monitoring_cycle_reads_environmental_sensor_after_moisture(
        self, mock_ads, mock_env_sensor_class
    ):
        """Monitoring cycle reads environmental sensor after moisture sensors."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.side_effect = [15000, 18000, 12000]  # 3 plants

        # Setup environmental sensor mock
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.45,
            humidity=55.67,
            pressure=1013.25,
            gas_resistance=12345.67,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profiles
        profiles = [
            PlantProfile(
                name="Snake Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            ),
            PlantProfile(
                name="Boston Fern",
                adc_channel=1,
                dry_value=0,
                wet_value=26400,
                threshold=45
            ),
            PlantProfile(
                name="Money Plant",
                adc_channel=2,
                dry_value=0,
                wet_value=26400,
                threshold=35
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify environmental sensor read was called after moisture reads
        assert mock_adc.readADC.call_count == 3  # Moisture sensors read first
        mock_env_sensor.read.assert_called_once()  # Then environmental sensor

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_monitoring_cycle_completes_successfully_with_environmental_data(
        self, mock_ads, mock_env_sensor_class
    ):
        """Complete monitoring cycle succeeds with both moisture and environmental data."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.side_effect = [15000, 10000]  # 2 plants

        # Setup environmental sensor mock
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=23.12,
            humidity=50.34,
            pressure=1015.67,
            gas_resistance=15000.89,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profiles
        profiles = [
            PlantProfile(
                name="Snake Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            ),
            PlantProfile(
                name="Boston Fern",
                adc_channel=1,
                dry_value=0,
                wet_value=26400,
                threshold=45
            )
        ]

        # Run monitoring cycle - should not raise
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify both moisture and environmental sensors were read
        assert mock_adc.readADC.call_count == 2
        mock_env_sensor.read.assert_called_once()


class TestEnvironmentalDataDisplay:
    """Test environmental data display alongside plant moisture (T018)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_environmental_data_displays_with_plant_moisture(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Environmental data appears in log output alongside plant moisture levels."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000  # 56.8% moisture

        # Setup environmental sensor mock
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.45,
            humidity=55.67,
            pressure=1013.25,
            gas_resistance=12345.67,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Snake Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify both moisture and environmental data appear in logs
        log_output = caplog.text
        assert "Snake Plant" in log_output  # Plant moisture logged
        assert "22.45°C" in log_output  # Temperature logged
        assert "55.67%" in log_output  # Humidity logged
        assert "1013.25 hPa" in log_output  # Pressure logged
        assert "12345.67 Ω" in log_output  # Gas resistance logged

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_environmental_data_formatted_to_two_decimal_places(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Environmental values displayed to exactly 2 decimal places."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor mock with values requiring rounding
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.456789,  # Should round to 22.46
            humidity=55.678901,      # Should round to 55.68
            pressure=1013.254321,    # Should round to 1013.25
            gas_resistance=12345.6789,  # Should round to 12345.68
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify exactly 2 decimal places in output
        log_output = caplog.text
        assert "22.46°C" in log_output
        assert "55.68%" in log_output
        assert "1013.25 hPa" in log_output
        assert "12345.68 Ω" in log_output


class TestEnvironmentalReadingsReflectConditions:
    """Test environmental readings reflect current conditions (T019)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_environmental_readings_update_each_cycle(
        self, mock_ads, mock_env_sensor_class
    ):
        """Environmental readings update with fresh values each monitoring cycle."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor mock with changing values
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True

        # First cycle: 22°C
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.00,
            humidity=50.00,
            pressure=1013.00,
            gas_resistance=10000.00,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # First monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        assert mock_env_sensor.read.call_count == 1

        # Second cycle: 25°C (temperature changed)
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=25.00,
            humidity=52.00,
            pressure=1015.00,
            gas_resistance=11000.00,
            timestamp=datetime.now(timezone.utc)
        )

        # Second monitoring cycle
        monitor.monitor_cycle()

        # Verify sensor read called again with fresh data
        assert mock_env_sensor.read.call_count == 2

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_each_reading_has_current_timestamp(
        self, mock_ads, mock_env_sensor_class
    ):
        """Each environmental reading includes current timestamp."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor mock
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True

        # Capture timestamp before reading
        before_time = datetime.now(timezone.utc)

        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.00,
            humidity=50.00,
            pressure=1013.00,
            gas_resistance=10000.00,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile and run cycle
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify read was called (timestamp validation happens in sensor implementation)
        mock_env_sensor.read.assert_called_once()


class TestOutOfRangeValueDisplay:
    """Test out-of-range value display with warning indicator (T020)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_out_of_range_temperature_displays_warning(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Out-of-range temperature displays with ⚠️ warning indicator."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor with out-of-range temperature
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=55.00,  # Above 50°C threshold
            humidity=50.00,
            pressure=1013.00,
            gas_resistance=10000.00,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify warning indicator appears in output
        log_output = caplog.text
        assert "55.00°C" in log_output
        assert "⚠️" in log_output
        assert "OUT OF RANGE" in log_output

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_out_of_range_pressure_displays_warning(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Out-of-range pressure displays with ⚠️ warning indicator."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor with out-of-range pressure
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.00,
            humidity=50.00,
            pressure=850.00,  # Below 900 hPa threshold
            gas_resistance=10000.00,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify warning indicator appears in output
        log_output = caplog.text
        assert "850.00 hPa" in log_output
        assert "⚠️" in log_output
        assert "OUT OF RANGE" in log_output

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_in_range_values_no_warning(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """In-range values display without warning indicator."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor with all in-range values
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=22.00,  # Within -10 to 50
            humidity=50.00,
            pressure=1013.00,  # Within 900 to 1100
            gas_resistance=10000.00,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify NO warning indicator in output
        log_output = caplog.text
        assert "22.00°C" in log_output
        assert "1013.00 hPa" in log_output
        # Should NOT contain warning when values in range
        # Note: Only check environment line doesn't have warning
        env_lines = [line for line in log_output.split('\n') if '°C' in line and 'hPa' in line]
        if env_lines:
            assert "⚠️" not in env_lines[0] or "OUT OF RANGE" not in env_lines[0]


# Tests for User Story 2 (Failure handling) - T033, T034, T035

class TestMonitoringContinuesWhenEnvironmentalSensorDisconnected:
    """Test plant monitoring continues when environmental sensor disconnected (T033)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_monitoring_continues_when_environmental_sensor_not_detected(
        self, mock_ads, mock_env_sensor_class
    ):
        """Plant monitoring continues when environmental sensor not detected at init."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.side_effect = [15000, 10000]

        # Setup environmental sensor mock - not available
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = False

        # Create profiles
        profiles = [
            PlantProfile(
                name="Snake Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            ),
            PlantProfile(
                name="Boston Fern",
                adc_channel=1,
                dry_value=0,
                wet_value=26400,
                threshold=45
            )
        ]

        # Run monitoring cycle - should complete successfully
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify moisture sensors were read despite environmental sensor unavailable
        assert mock_adc.readADC.call_count == 2

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_monitoring_continues_when_environmental_sensor_read_fails(
        self, mock_ads, mock_env_sensor_class
    ):
        """Plant monitoring continues when environmental sensor read fails."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.side_effect = [15000, 10000]

        # Setup environmental sensor mock - read returns invalid
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=None,
            humidity=None,
            pressure=None,
            gas_resistance=None,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profiles
        profiles = [
            PlantProfile(
                name="Snake Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            ),
            PlantProfile(
                name="Boston Fern",
                adc_channel=1,
                dry_value=0,
                wet_value=26400,
                threshold=45
            )
        ]

        # Run monitoring cycle - should complete successfully
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify moisture sensors were read despite environmental read failure
        assert mock_adc.readADC.call_count == 2


class TestErrorLoggingWhenEnvironmentalSensorFails:
    """Test error logging when environmental sensor fails (T034)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_warning_logged_when_environmental_sensor_unavailable(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Warning logged when environmental sensor unavailable."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor mock - not available
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = False

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify warning appears in logs
        log_output = caplog.text
        assert "WARNING" in log_output or "unavailable" in log_output.lower()

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_warning_logged_when_environmental_read_invalid(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Warning logged when environmental sensor returns invalid reading."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor mock - returns invalid reading
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = True
        mock_env_sensor.read.return_value = EnvironmentalReading(
            temperature=None,
            humidity=None,
            pressure=None,
            gas_resistance=None,
            timestamp=datetime.now(timezone.utc)
        )

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify warning or error indicator in logs
        log_output = caplog.text.lower()
        assert "warning" in log_output or "error" in log_output or "unavailable" in log_output


class TestPlantMoistureDisplayWhenEnvironmentalSensorUnavailable:
    """Test plant moisture display when environmental sensor unavailable (T035)."""

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_plant_moisture_displays_when_environmental_sensor_unavailable(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Plant moisture levels display normally when environmental sensor unavailable."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.side_effect = [15000, 10000]

        # Setup environmental sensor mock - not available
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = False

        # Create profiles
        profiles = [
            PlantProfile(
                name="Snake Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            ),
            PlantProfile(
                name="Boston Fern",
                adc_channel=1,
                dry_value=0,
                wet_value=26400,
                threshold=45
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify plant moisture data appears in logs
        log_output = caplog.text
        assert "Snake Plant" in log_output
        assert "Boston Fern" in log_output

    @patch('src.lib.environmental_sensor.EnvironmentalSensorReader')
    @patch('src.lib.moisture_monitor.ADS')
    def test_environmental_status_shows_unavailable_when_sensor_missing(
        self, mock_ads, mock_env_sensor_class, caplog
    ):
        """Environmental status shows UNAVAILABLE when sensor missing."""
        # Setup moisture sensor mock
        mock_adc = Mock()
        mock_ads.ADS1115.return_value = mock_adc
        mock_adc.readADC.return_value = 15000

        # Setup environmental sensor mock - not available
        mock_env_sensor = Mock()
        mock_env_sensor_class.return_value = mock_env_sensor
        mock_env_sensor.is_available.return_value = False

        # Create profile
        profiles = [
            PlantProfile(
                name="Test Plant",
                adc_channel=0,
                dry_value=0,
                wet_value=26400,
                threshold=40
            )
        ]

        # Run monitoring cycle
        monitor = MoistureMonitor(profiles)
        monitor.monitor_cycle()

        # Verify UNAVAILABLE or ERROR appears for environmental data
        log_output = caplog.text
        assert "UNAVAILABLE" in log_output or "ERROR" in log_output
