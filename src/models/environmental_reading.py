"""Environmental sensor reading data model.

Represents a snapshot of environmental conditions (temperature, humidity,
atmospheric pressure, gas resistance) at a specific point in time.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EnvironmentalReading:
    """Snapshot of environmental conditions from BME688 sensor.

    Attributes:
        temperature: Temperature in degrees Celsius, None if read failed
        humidity: Relative humidity as percentage (0-100), None if read failed
        pressure: Atmospheric pressure in hectopascals (hPa), None if read failed
        gas_resistance: Gas resistance in ohms (Ω), None if read failed
        timestamp: When the reading was captured (UTC timezone)
    """

    temperature: Optional[float]      # °C
    humidity: Optional[float]          # %
    pressure: Optional[float]          # hPa
    gas_resistance: Optional[float]    # Ω
    timestamp: datetime

    @property
    def is_valid(self) -> bool:
        """True if at least one reading succeeded.

        Returns:
            True if any sensor value is not None, False if all are None
        """
        return any([
            self.temperature is not None,
            self.humidity is not None,
            self.pressure is not None,
            self.gas_resistance is not None
        ])

    def format_for_display(self) -> str:
        """Format environmental data for console output.

        Returns formatted string with all values to 2 decimal places.
        Shows "ERROR" for None values and "⚠️ OUT OF RANGE" suffix for
        values outside expected indoor ranges.

        Returns:
            Formatted string like "Temp: 22.45°C, Humidity: 55.67%, Pressure: 1013.25 hPa, Gas: 12345.67 Ω"
        """
        # Format each value or show ERROR
        temp_str = f"{self.temperature:.2f}°C" if self.temperature is not None else "ERROR"
        humidity_str = f"{self.humidity:.2f}%" if self.humidity is not None else "ERROR"
        pressure_str = f"{self.pressure:.2f} hPa" if self.pressure is not None else "ERROR"
        gas_str = f"{self.gas_resistance:.2f} Ω" if self.gas_resistance is not None else "ERROR"

        # Build base formatted string
        formatted = f"Temp: {temp_str}, Humidity: {humidity_str}, Pressure: {pressure_str}, Gas: {gas_str}"

        # Add warning if any values out of range
        if self.has_out_of_range_values():
            formatted += " ⚠️ OUT OF RANGE"

        return formatted

    def has_out_of_range_values(self) -> bool:
        """Check if any reading is outside expected indoor range.

        Checks:
        - Temperature: -10°C to 50°C
        - Pressure: 900 hPa to 1100 hPa
        - Humidity and gas resistance: no range checking

        Returns:
            True if temperature or pressure outside expected range, False otherwise
        """
        # Check temperature range (-10°C to 50°C)
        if self.temperature is not None:
            if self.temperature < -10.0 or self.temperature > 50.0:
                return True

        # Check pressure range (900 hPa to 1100 hPa)
        if self.pressure is not None:
            if self.pressure < 900.0 or self.pressure > 1100.0:
                return True

        return False
