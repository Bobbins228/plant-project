"""Environmental sensor reader for BME688 sensor.

Reads temperature, humidity, atmospheric pressure, and gas resistance from
BME688 environmental sensor over I2C bus. Provides timeout handling and
graceful degradation when sensor unavailable.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import bme680
    import smbus2
    BME680_AVAILABLE = True
except ImportError:
    bme680 = None
    smbus2 = None
    BME680_AVAILABLE = False

from src.models.environmental_reading import EnvironmentalReading


logger = logging.getLogger(__name__)


class EnvironmentalSensorReader:
    """Read environmental data from BME688 sensor.

    Initializes BME688 sensor with appropriate configuration for indoor
    environmental monitoring. Handles sensor initialization failures and
    read timeouts gracefully without raising exceptions.

    Attributes:
        sensor: BME680 sensor instance, None if sensor not detected
        timeout: Maximum seconds to wait for sensor data (default 2.0)
    """

    def __init__(self, i2c_bus: int = 1, timeout: float = 2.0):
        """Initialize environmental sensor reader.

        Args:
            i2c_bus: I2C bus number (1 for Raspberry Pi pins 3 & 5)
            timeout: Maximum seconds to wait for sensor read
        """
        self.timeout = timeout
        self.sensor: Optional[bme680.BME680] = None
        self.detected_address: Optional[int] = None

        # Check if bme680 and smbus2 libraries available
        if not BME680_AVAILABLE:
            logger.warning(
                "bme680 or smbus2 library not installed - environmental sensor unavailable"
            )
            return

        # Probe I2C bus to detect BME688 at 0x76 or 0x77
        bus = None
        try:
            bus = smbus2.SMBus(i2c_bus)

            # Try both possible addresses (0x76 = SDO low, 0x77 = SDO high)
            for address in (0x76, 0x77):
                try:
                    # Try to read chip ID register (0xD0) to verify sensor present
                    bus.read_byte_data(address, 0xD0)
                    self.detected_address = address
                    logger.debug(f"BME688 detected at I2C address 0x{address:02x}")
                    break
                except OSError:
                    continue

            if bus is not None:
                bus.close()
                bus = None

            if self.detected_address is None:
                logger.warning(
                    "Environmental sensor not detected at I2C address 0x76 or 0x77 "
                    "(check wiring and I2C enabled)"
                )
                return

            # Initialize BME680 sensor using library constants
            if self.detected_address == 0x76:
                self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
            else:
                self.sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

            # Set temperature offset
            self.sensor.set_temp_offset(0)

            # Configure sensor for indoor environmental monitoring
            # Temperature oversampling (OS_8X = accurate, slower)
            self.sensor.set_temperature_oversample(bme680.OS_8X)

            # Humidity oversampling (OS_2X = balanced)
            self.sensor.set_humidity_oversample(bme680.OS_2X)

            # Pressure oversampling (OS_4X = accurate)
            self.sensor.set_pressure_oversample(bme680.OS_4X)

            # IIR filter coefficient (SIZE_3 = moderate smoothing)
            self.sensor.set_filter(bme680.FILTER_SIZE_3)

            # Configure gas sensor
            # Enable gas measurements
            self.sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

            # Gas heater: 320°C for 150ms (indoor air quality profile)
            self.sensor.set_gas_heater_temperature(320)
            self.sensor.set_gas_heater_duration(150)
            self.sensor.select_gas_heater_profile(0)

            logger.info(
                f"Environmental sensor initialized successfully at I2C address 0x{self.detected_address:02x}"
            )

        except IOError as e:
            logger.warning(
                f"I2C communication error during environmental sensor initialization: {e}"
            )
            if bus is not None:
                try:
                    bus.close()
                except Exception:
                    pass
            self.sensor = None
        except Exception as e:
            logger.error(
                f"Unexpected error initializing environmental sensor: {e}"
            )
            if bus is not None:
                try:
                    bus.close()
                except Exception:
                    pass
            self.sensor = None

    def is_available(self) -> bool:
        """Check if environmental sensor is available.

        Returns:
            True if sensor initialized successfully, False otherwise
        """
        return self.sensor is not None

    def read(self) -> EnvironmentalReading:
        """Read current environmental conditions from sensor.

        Attempts to read sensor data within timeout period. Returns invalid
        reading (all None) if sensor unavailable, timeout occurs, or I/O error.

        Returns:
            EnvironmentalReading with current sensor values, or all None if failed
        """
        # If sensor not available, return invalid reading
        if not self.is_available():
            logger.debug("Environmental sensor not available - returning invalid reading")
            return EnvironmentalReading(
                temperature=None,
                humidity=None,
                pressure=None,
                gas_resistance=None,
                timestamp=datetime.now(timezone.utc)
            )

        try:
            # Wait for sensor data with timeout
            start_time = time.time()

            while not self.sensor.get_sensor_data():
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    logger.warning(
                        f"Environmental sensor read timeout after {self.timeout:.1f} seconds"
                    )
                    return EnvironmentalReading(
                        temperature=None,
                        humidity=None,
                        pressure=None,
                        gas_resistance=None,
                        timestamp=datetime.now(timezone.utc)
                    )
                time.sleep(0.01)  # Brief sleep to avoid busy-waiting

            # Extract sensor data
            data = self.sensor.data

            # Create reading with current timestamp
            reading = EnvironmentalReading(
                temperature=data.temperature,
                humidity=data.humidity,
                pressure=data.pressure,
                gas_resistance=data.gas_resistance,
                timestamp=datetime.now(timezone.utc)
            )

            logger.debug(
                f"Environmental sensor read successful: "
                f"temp={reading.temperature:.2f}°C, "
                f"humidity={reading.humidity:.2f}%, "
                f"pressure={reading.pressure:.2f} hPa, "
                f"gas={reading.gas_resistance:.2f} Ω"
            )

            return reading

        except IOError as e:
            logger.error(f"I2C communication error reading environmental sensor: {e}")
            return EnvironmentalReading(
                temperature=None,
                humidity=None,
                pressure=None,
                gas_resistance=None,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Unexpected error reading environmental sensor: {e}")
            return EnvironmentalReading(
                temperature=None,
                humidity=None,
                pressure=None,
                gas_resistance=None,
                timestamp=datetime.now(timezone.utc)
            )
