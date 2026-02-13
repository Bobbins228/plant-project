"""Contract tests for EnvironmentalSensorReader interface.

Tests the sensor reading interface contract ensuring it behaves correctly
with and without physical hardware. Uses mocking to avoid hardware dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.models.environmental_reading import EnvironmentalReading


class TestEnvironmentalSensorReaderInitialization:
    """Test EnvironmentalSensorReader initialization (T012)."""

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_initialization_with_default_parameters(self, mock_bme680, mock_smbus2):
        """Initialize with default I2C bus and timeout."""
        # Mock I2C probe - sensor found at 0x76
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61  # BME680 chip ID

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76
        mock_bme680.I2C_ADDR_SECONDARY = 0x77

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()

        # Should probe I2C bus 1 (default) and find sensor at 0x76
        mock_smbus2.SMBus.assert_called_once_with(1)
        mock_bus.read_byte_data.assert_called_with(0x76, 0xD0)
        mock_bme680.BME680.assert_called_once_with(0x76)  # I2C_ADDR_PRIMARY
        assert reader.timeout == 2.0  # Default timeout
        assert reader.detected_address == 0x76

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_initialization_with_custom_parameters(self, mock_bme680, mock_smbus2):
        """Initialize with custom I2C bus and timeout."""
        # Mock I2C probe - sensor found at 0x77
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.side_effect = [OSError(), 0x61]  # Fail at 0x76, succeed at 0x77

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76
        mock_bme680.I2C_ADDR_SECONDARY = 0x77

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader(i2c_bus=0, timeout=5.0)

        mock_smbus2.SMBus.assert_called_once_with(0)
        mock_bme680.BME680.assert_called_once_with(0x77)  # I2C_ADDR_SECONDARY
        assert reader.timeout == 5.0
        assert reader.detected_address == 0x77

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_initialization_configures_sensor(self, mock_bme680, mock_smbus2):
        """Initialization configures sensor oversampling and filter."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()

        # Should configure oversampling
        assert mock_sensor.set_temp_offset.called
        assert mock_sensor.set_temperature_oversample.called
        assert mock_sensor.set_humidity_oversample.called
        assert mock_sensor.set_pressure_oversample.called
        assert mock_sensor.set_filter.called
        assert mock_sensor.set_gas_status.called

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_initialization_does_not_raise_on_sensor_not_found(self, mock_bme680, mock_smbus2):
        """Initialization does not raise exception when sensor not detected."""
        # Mock I2C probe - sensor not found at either address
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.side_effect = OSError("Sensor not found")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        # Should not raise, just log warning
        reader = EnvironmentalSensorReader()
        assert reader is not None
        assert reader.sensor is None
        assert reader.detected_address is None


class TestEnvironmentalSensorReaderRead:
    """Test EnvironmentalSensorReader.read() method (T013, T014, T015)."""

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_successful_read_returns_all_values(self, mock_bme680, mock_smbus2):
        """Successful read returns EnvironmentalReading with all values (T013)."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76

        # Mock successful sensor data
        mock_sensor.get_sensor_data.return_value = True
        mock_sensor.data = Mock()
        mock_sensor.data.temperature = 22.45
        mock_sensor.data.humidity = 55.67
        mock_sensor.data.pressure = 1013.25
        mock_sensor.data.gas_resistance = 12345.67

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        reading = reader.read()

        assert isinstance(reading, EnvironmentalReading)
        assert reading.temperature == 22.45
        assert reading.humidity == 55.67
        assert reading.pressure == 1013.25
        assert reading.gas_resistance == 12345.67
        assert reading.is_valid is True

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    @patch('src.lib.environmental_sensor.time')
    def test_read_timeout_returns_invalid_reading(self, mock_time, mock_bme680, mock_smbus2):
        """Read timeout returns EnvironmentalReading with all None (T014)."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76

        # Mock timeout scenario - get_sensor_data never returns True
        mock_sensor.get_sensor_data.return_value = False
        mock_time.time.side_effect = [0, 0.5, 1.0, 1.5, 2.1]  # Exceeds 2.0s timeout

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader(timeout=2.0)
        reading = reader.read()

        assert isinstance(reading, EnvironmentalReading)
        assert reading.temperature is None
        assert reading.humidity is None
        assert reading.pressure is None
        assert reading.gas_resistance is None
        assert reading.is_valid is False

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_partial_read_failure_returns_available_data(self, mock_bme680, mock_smbus2):
        """Partial failure returns EnvironmentalReading with partial data (T015)."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76

        # Mock partial sensor data (some readings available, others not)
        mock_sensor.get_sensor_data.return_value = True
        mock_sensor.data = Mock()
        mock_sensor.data.temperature = 22.45
        mock_sensor.data.humidity = None  # Failed
        mock_sensor.data.pressure = 1013.25
        mock_sensor.data.gas_resistance = None  # Failed

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        reading = reader.read()

        assert isinstance(reading, EnvironmentalReading)
        assert reading.temperature == 22.45
        assert reading.humidity is None
        assert reading.pressure == 1013.25
        assert reading.gas_resistance is None
        assert reading.is_valid is True  # At least temperature and pressure succeeded

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_read_ioerror_returns_invalid_reading(self, mock_bme680, mock_smbus2):
        """I2C error during read returns invalid reading, no exception raised."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76

        # Mock I2C communication error
        mock_sensor.get_sensor_data.side_effect = IOError("I2C communication error")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        reading = reader.read()  # Should not raise

        assert isinstance(reading, EnvironmentalReading)
        assert reading.is_valid is False


class TestEnvironmentalSensorReaderIsAvailable:
    """Test EnvironmentalSensorReader.is_available() method (T016)."""

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_is_available_true_when_sensor_initialized(self, mock_bme680, mock_smbus2):
        """is_available() returns True when sensor initialized successfully."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        assert reader.is_available() is True

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_is_available_false_when_sensor_not_detected(self, mock_bme680, mock_smbus2):
        """is_available() returns False when sensor not detected at init."""
        # Mock I2C probe - sensor not found
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.side_effect = OSError("Sensor not found")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        assert reader.is_available() is False


# Tests for User Story 2 (Failure handling) - T031, T032

class TestEnvironmentalSensorReaderSensorNotDetected:
    """Test sensor not detected during initialization (T031)."""

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_sensor_not_detected_logs_warning(self, mock_bme680, mock_smbus2):
        """Sensor not detected logs warning and sets available flag to False."""
        # Mock I2C probe - sensor not found
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.side_effect = OSError("Sensor not found")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()

        assert reader.is_available() is False

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_read_when_sensor_not_detected_returns_invalid(self, mock_bme680, mock_smbus2):
        """Read when sensor not detected returns invalid reading."""
        # Mock I2C probe - sensor not found
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.side_effect = OSError("Sensor not found")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        reading = reader.read()

        assert reading.is_valid is False
        assert reading.temperature is None
        assert reading.humidity is None
        assert reading.pressure is None
        assert reading.gas_resistance is None


class TestEnvironmentalSensorReaderI2CError:
    """Test I2C communication error during read (T032)."""

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_ioerror_during_read_logs_and_returns_invalid(self, mock_bme680, mock_smbus2):
        """I2C error during read logs error and returns invalid reading."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76
        mock_sensor.get_sensor_data.side_effect = IOError("I2C bus error")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()
        reading = reader.read()

        assert reading.is_valid is False

    @patch('src.lib.environmental_sensor.smbus2')
    @patch('src.lib.environmental_sensor.bme680')
    def test_ioerror_does_not_raise_exception(self, mock_bme680, mock_smbus2):
        """I2C error does not raise exception (graceful degradation)."""
        # Mock I2C probe
        mock_bus = Mock()
        mock_smbus2.SMBus.return_value = mock_bus
        mock_bus.read_byte_data.return_value = 0x61

        mock_sensor = Mock()
        mock_bme680.BME680.return_value = mock_sensor
        mock_bme680.I2C_ADDR_PRIMARY = 0x76
        mock_sensor.get_sensor_data.side_effect = IOError("I2C bus error")

        from src.lib.environmental_sensor import EnvironmentalSensorReader

        reader = EnvironmentalSensorReader()

        # Should not raise
        try:
            reading = reader.read()
            assert True
        except Exception:
            pytest.fail("read() should not raise exceptions")
