"""ADS1115 sensor reader and moisture conversion.

Reads analog voltage from capacitive soil moisture sensors via ADS1115 ADC
and converts to moisture percentage using linear calibration formula.
"""

from typing import Optional
import logging

try:
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn
    I2C_AVAILABLE = True
except ImportError:
    # Allow import on systems without I2C hardware (e.g., Mac development)
    I2C_AVAILABLE = False
    board = None
    busio = None
    ADS1115 = None
    AnalogIn = None

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
                "I2C libraries not available. Install adafruit-circuitpython-ads1x15 "
                "and ensure running on Raspberry Pi with I2C enabled."
            )

        self.address = address
        self.gain = gain
        self.voltage_dry = voltage_dry
        self.voltage_wet = voltage_wet

        # Initialize I2C bus and ADS1115
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.ads = ADS1115(i2c, address=address)
            self.ads.gain = gain
            logger.info(f"ADS1115 initialized at address 0x{address:02x} with gain={gain}")
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
            # Map channel number to ADS1115 channel constant
            channel_map = {
                0: ADS1115.P0,
                1: ADS1115.P1,
                2: ADS1115.P2
            }

            # Read voltage
            analog_in = AnalogIn(self.ads, channel_map[channel])
            voltage = analog_in.voltage

            logger.debug(f"Channel {channel}: {voltage:.3f}V (raw: {analog_in.value})")
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
