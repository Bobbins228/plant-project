"""Sensor reading data model for moisture measurements."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SensorReading:
    """Single sensor measurement from ADS1115 channel.

    Represents a moisture reading with raw ADC value, converted voltage,
    and calculated moisture percentage.

    Attributes:
        plant_id: Which plant this reading belongs to ("Plant-A", "Plant-B", "Plant-C")
        timestamp: When the reading was taken (UTC)
        raw_adc_value: Raw ADC count from ADS1115 (0-32767 for 16-bit resolution)
        voltage: Converted voltage reading (0.0-4.096V range with gain=1)
        moisture_percent: Converted moisture percentage (0-100), None if conversion failed
    """

    plant_id: str
    timestamp: datetime
    raw_adc_value: int
    voltage: float
    moisture_percent: Optional[float]  # None if invalid

    @property
    def is_valid(self) -> bool:
        """True if moisture reading is in valid range.

        Allows ±5% margin for sensor variance to handle calibration differences.
        Readings outside [-5%, 105%] indicate sensor malfunction.
        """
        if self.moisture_percent is None:
            return False
        # Allow ±5% margin for sensor variance
        return -5.0 <= self.moisture_percent <= 105.0
