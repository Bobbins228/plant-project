"""ADS1115 sensor reader and moisture conversion.

Reads analog voltage from capacitive soil moisture sensors via ADS1115 ADC
and converts to moisture percentage using linear calibration formula.
"""

from typing import Optional
import logging

try:
    from ADS1x15 import ADS1115
    I2C_AVAILABLE = True
except ImportError:
    # Allow import on systems without I2C hardware (e.g., Mac development)
    I2C_AVAILABLE = False
    ADS1115 = None

logger = logging.getLogger(__name__)

# I2C bus number on Raspberry Pi (bus 1 = GPIO pins 3 & 5)
I2C_BUS = 1

# Gain to voltage range mapping (for raw ADC to voltage conversion)
GAIN_VOLTAGE_RANGE = {
    1: 4.096,   # ±4.096V (PGA_4_096V)
    2: 2.048,   # ±2.048V (PGA_2_048V)
    4: 1.024,   # ±1.024V (PGA_1_024V)
    8: 0.512,   # ±0.512V (PGA_0_512V)
    16: 0.256,  # ±0.256V (PGA_0_256V)
}

# Gain to ADS1x15 PGA constant mapping
GAIN_PGA_MAP = {
    1: 'PGA_4_096V',
    2: 'PGA_2_048V',
    4: 'PGA_1_024V',
    8: 'PGA_0_512V',
    16: 'PGA_0_256V',
}

logger = logging.getLogger(__name__)


class SensorReader:
    """ADS1115 sensor interface for reading soil moisture.

    Reads analog voltage from capacitive sensors connected to ADS1115 channels
    and converts to moisture percentage using configurable calibration values.
    """

    def __init__(
        self,
        address: int = 0x48,
        gain: int = 1,
        voltage_dry: float = 3.0,
        voltage_wet: float = 1.6
    ):
        """Initialize sensor reader.

        Args:
            address: I2C address of ADS1115 (default: 0x48)
            gain: ADS1115 gain setting (1 = ±4.096V range)
            voltage_dry: Calibrated voltage in air (0% moisture)
            voltage_wet: Calibrated voltage in water (100% moisture)

        Raises:
            RuntimeError: If I2C hardware/libraries not available
        """
        if not I2C_AVAILABLE:
            raise RuntimeError(
                "I2C libraries not available. Install ADS1x15-ADC "
                "and ensure running on Raspberry Pi with I2C enabled."
            )

        if gain not in GAIN_VOLTAGE_RANGE:
            raise ValueError(f"Invalid gain: {gain}. Must be one of {list(GAIN_VOLTAGE_RANGE.keys())}")

        self.address = address
        self.gain = gain
        self.voltage_dry = voltage_dry
        self.voltage_wet = voltage_wet
        self.voltage_range = GAIN_VOLTAGE_RANGE[gain]

        # Initialize ADS1115 on I2C bus
        try:
            self.ads = ADS1115(I2C_BUS, address)

            # Set gain (voltage range)
            pga_constant = getattr(self.ads, GAIN_PGA_MAP[gain])
            self.ads.setGain(pga_constant)

            # Set to single-shot mode (not continuous)
            self.ads.setMode(self.ads.MODE_SINGLE)

            logger.info(
                f"ADS1115 initialized at address 0x{address:02x} with gain={gain} "
                f"(±{self.voltage_range}V range)"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ADS1115: {e}")
            raise

    def read_channel(self, channel: int) -> Optional[float]:
        """Read voltage from ADS1115 channel.

        Args:
            channel: Channel number (0, 1, or 2)

        Returns:
            Voltage reading (0.0-4.096V), or None if read failed

        Raises:
            ValueError: If channel not in range 0-2
        """
        if channel not in (0, 1, 2):
            raise ValueError(f"Invalid channel: {channel}. Must be 0, 1, or 2")

        try:
            # Read raw ADC value from channel (single-ended)
            raw_adc = self.ads.readADCSingleEnded(channel)

            # Convert raw ADC value to voltage
            # ADS1115 returns raw values 0-32767 for single-ended positive inputs
            # Voltage = (raw / 32768) * voltage_range
            voltage = (raw_adc / 32768.0) * self.voltage_range

            logger.debug(f"Channel {channel}: {voltage:.3f}V (raw: {raw_adc})")
            return voltage

        except Exception as e:
            logger.error(f"Failed to read channel {channel}: {e}")
            return None

    def voltage_to_moisture(self, voltage: float) -> Optional[float]:
        """Convert voltage to moisture percentage using linear calibration.

        Uses formula from research.md:
        moisture_percent = ((voltage_dry - voltage) / (voltage_dry - voltage_wet)) * 100.0

        Args:
            voltage: Voltage reading from sensor (V)

        Returns:
            Moisture percentage (0-100), or None if outside valid range

        Note:
            - Returns None if outside [-5%, 105%] margin (sensor failure)
            - Clamps valid readings to [0%, 100%] for reporting
        """
        # Calculate moisture percentage (inverse: higher voltage = drier)
        raw_percent = ((self.voltage_dry - voltage) /
                       (self.voltage_dry - self.voltage_wet)) * 100.0

        # Validate with ±5% margin for sensor variance
        if raw_percent < -5.0 or raw_percent > 105.0:
            logger.error(
                f"Invalid sensor reading: {raw_percent:.1f}% (voltage: {voltage:.3f}V, "
                f"range: {self.voltage_wet}V-{self.voltage_dry}V)"
            )
            return None

        # Clamp to valid 0-100 range for reporting
        moisture_percent = max(0.0, min(100.0, raw_percent))

        return moisture_percent

    def read_moisture(self, channel: int) -> Optional[float]:
        """Read voltage from channel and convert to moisture percentage.

        Convenience method that combines read_channel and voltage_to_moisture.

        Args:
            channel: ADS1115 channel number (0, 1, or 2)

        Returns:
            Moisture percentage (0-100), or None if read/conversion failed
        """
        voltage = self.read_channel(channel)
        if voltage is None:
            return None

        return self.voltage_to_moisture(voltage)

    def read_moisture_with_voltage(self, channel: int) -> tuple[Optional[float], Optional[float]]:
        """Read channel once and return both voltage and moisture percentage.

        More efficient than calling read_channel() and read_moisture() separately
        as it only performs one ADC read.

        Args:
            channel: ADS1115 channel number (0, 1, or 2)

        Returns:
            Tuple of (voltage, moisture_percent). Either value can be None if read/conversion failed.
        """
        voltage = self.read_channel(channel)
        if voltage is None:
            return (None, None)

        moisture = self.voltage_to_moisture(voltage)
        return (voltage, moisture)
