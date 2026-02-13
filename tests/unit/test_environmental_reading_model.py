"""Unit tests for EnvironmentalReading data model.

Tests validation logic, properties, and display formatting for environmental
sensor readings.
"""

import pytest
from datetime import datetime, timezone

from src.models.environmental_reading import EnvironmentalReading


class TestEnvironmentalReadingValidation:
    """Test EnvironmentalReading model validation (T004)."""

    def test_valid_reading_with_all_values(self):
        """Valid reading with all four sensor values."""
        reading = EnvironmentalReading(
            temperature=22.45,
            humidity=55.67,
            pressure=1013.25,
            gas_resistance=12345.67,
            timestamp=datetime(2026, 2, 13, 15, 30, 0, tzinfo=timezone.utc)
        )

        assert reading.temperature == 22.45
        assert reading.humidity == 55.67
        assert reading.pressure == 1013.25
        assert reading.gas_resistance == 12345.67

    def test_valid_reading_with_partial_values(self):
        """Valid reading with some None values (partial sensor failure)."""
        reading = EnvironmentalReading(
            temperature=None,
            humidity=None,
            pressure=1013.25,
            gas_resistance=12345.67,
            timestamp=datetime(2026, 2, 13, 15, 30, 0, tzinfo=timezone.utc)
        )

        assert reading.temperature is None
        assert reading.humidity is None
        assert reading.pressure == 1013.25
        assert reading.gas_resistance == 12345.67

    def test_reading_with_all_none_values(self):
        """Reading with all None values (complete sensor failure)."""
        reading = EnvironmentalReading(
            temperature=None,
            humidity=None,
            pressure=None,
            gas_resistance=None,
            timestamp=datetime(2026, 2, 13, 15, 30, 0, tzinfo=timezone.utc)
        )

        assert reading.temperature is None
        assert reading.humidity is None
        assert reading.pressure is None
        assert reading.gas_resistance is None


class TestEnvironmentalReadingIsValid:
    """Test EnvironmentalReading.is_valid property logic (T005)."""

    def test_is_valid_true_when_all_values_present(self):
        """is_valid returns True when all readings succeeded."""
        reading = EnvironmentalReading(
            temperature=22.45,
            humidity=55.67,
            pressure=1013.25,
            gas_resistance=12345.67,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.is_valid is True

    def test_is_valid_true_when_partial_values_present(self):
        """is_valid returns True when at least one reading succeeded."""
        reading = EnvironmentalReading(
            temperature=22.45,
            humidity=None,
            pressure=None,
            gas_resistance=None,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.is_valid is True

    def test_is_valid_false_when_all_values_none(self):
        """is_valid returns False when all readings failed."""
        reading = EnvironmentalReading(
            temperature=None,
            humidity=None,
            pressure=None,
            gas_resistance=None,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.is_valid is False


class TestEnvironmentalReadingFormatForDisplay:
    """Test EnvironmentalReading.format_for_display() method (T006)."""

    def test_format_all_values_present(self):
        """Formats all values to 2 decimal places when present."""
        reading = EnvironmentalReading(
            temperature=22.456,
            humidity=55.678,
            pressure=1013.254,
            gas_resistance=12345.678,
            timestamp=datetime.now(timezone.utc)
        )

        formatted = reading.format_for_display()

        assert "22.46°C" in formatted  # Rounded to 2 decimals
        assert "55.68%" in formatted
        assert "1013.25 hPa" in formatted
        assert "12345.68 Ω" in formatted

    def test_format_shows_error_for_none_values(self):
        """Shows ERROR for None values."""
        reading = EnvironmentalReading(
            temperature=None,
            humidity=55.67,
            pressure=None,
            gas_resistance=12345.67,
            timestamp=datetime.now(timezone.utc)
        )

        formatted = reading.format_for_display()

        assert "ERROR" in formatted  # For temperature
        assert "55.67%" in formatted
        assert "ERROR" in formatted  # For pressure (appears twice)
        assert "12345.67 Ω" in formatted

    def test_format_adds_warning_for_out_of_range_temperature(self):
        """Adds warning indicator for out-of-range temperature."""
        reading = EnvironmentalReading(
            temperature=55.0,  # Above 50°C
            humidity=50.0,
            pressure=1013.0,
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        formatted = reading.format_for_display()

        assert "⚠️" in formatted
        assert "OUT OF RANGE" in formatted

    def test_format_adds_warning_for_out_of_range_pressure(self):
        """Adds warning indicator for out-of-range pressure."""
        reading = EnvironmentalReading(
            temperature=22.0,
            humidity=50.0,
            pressure=850.0,  # Below 900 hPa
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        formatted = reading.format_for_display()

        assert "⚠️" in formatted
        assert "OUT OF RANGE" in formatted


class TestEnvironmentalReadingHasOutOfRangeValues:
    """Test EnvironmentalReading.has_out_of_range_values() method (T007)."""

    def test_returns_false_for_normal_values(self):
        """Returns False when all values within expected range."""
        reading = EnvironmentalReading(
            temperature=22.0,  # -10 to 50
            humidity=50.0,     # No range check
            pressure=1013.0,   # 900 to 1100
            gas_resistance=10000.0,  # No range check
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is False

    def test_returns_true_for_low_temperature(self):
        """Returns True when temperature below -10°C."""
        reading = EnvironmentalReading(
            temperature=-15.0,
            humidity=50.0,
            pressure=1013.0,
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is True

    def test_returns_true_for_high_temperature(self):
        """Returns True when temperature above 50°C."""
        reading = EnvironmentalReading(
            temperature=55.0,
            humidity=50.0,
            pressure=1013.0,
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is True

    def test_returns_true_for_low_pressure(self):
        """Returns True when pressure below 900 hPa."""
        reading = EnvironmentalReading(
            temperature=22.0,
            humidity=50.0,
            pressure=850.0,
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is True

    def test_returns_true_for_high_pressure(self):
        """Returns True when pressure above 1100 hPa."""
        reading = EnvironmentalReading(
            temperature=22.0,
            humidity=50.0,
            pressure=1150.0,
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is True

    def test_returns_false_when_out_of_range_values_are_none(self):
        """Returns False when out-of-range values are None (not checked)."""
        reading = EnvironmentalReading(
            temperature=None,  # Would be out of range if present
            humidity=50.0,
            pressure=None,
            gas_resistance=10000.0,
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is False

    def test_humidity_and_gas_not_checked_for_range(self):
        """Humidity and gas resistance have no range checking."""
        reading = EnvironmentalReading(
            temperature=22.0,
            humidity=150.0,  # Unrealistic but not checked
            pressure=1013.0,
            gas_resistance=999999.0,  # Very high but not checked
            timestamp=datetime.now(timezone.utc)
        )

        assert reading.has_out_of_range_values() is False
