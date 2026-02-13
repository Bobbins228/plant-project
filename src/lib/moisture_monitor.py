"""Core moisture monitoring logic with notification and throttling.

Implements the main monitoring loop that reads sensors, checks thresholds,
sends notifications, and manages throttle timers.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import logging

from src.models.plant import Plant
from src.models.sensor_reading import SensorReading
from src.models.notification_event import NotificationEvent
from src.lib.config import MonitorConfig
from src.lib.notifier import NtfyClient
from src.lib.database import (
    load_all_profiles,
    load_profile_by_channel,
    update_current_moisture,
    set_needs_watering_flag,
    record_watering_event,
    check_unmapped_sensors,
    DEFAULT_DB_PATH
)

try:
    from src.lib.sensor import SensorReader
    SENSOR_AVAILABLE = True
except RuntimeError:
    # I2C not available (development on Mac)
    SENSOR_AVAILABLE = False
    SensorReader = None

try:
    from src.lib.environmental_sensor import EnvironmentalSensorReader
    ENVIRONMENTAL_SENSOR_AVAILABLE = True
except ImportError:
    # Environmental sensor library not available
    ENVIRONMENTAL_SENSOR_AVAILABLE = False
    EnvironmentalSensorReader = None

logger = logging.getLogger(__name__)


class MoistureMonitor:
    """Main moisture monitoring system.

    Coordinates sensor reading, threshold checking, and notification sending
    for multiple plants with independent throttle timers.
    """

    def __init__(self, config: MonitorConfig, db_path: str = DEFAULT_DB_PATH):
        """Initialize moisture monitor.

        Args:
            config: System configuration
            db_path: Path to SQLite database file (optional, defaults to data/plants.db)
        """
        self.config = config
        self.db_path = db_path

        # Log database file location
        logger.info(f"Using database: {db_path}")

        # Initialize plants from database with fallback to hardcoded defaults
        self.plants: List[Plant] = []

        try:
            # Attempt to load plant profiles from database
            profiles = load_all_profiles(db_path)

            if profiles:
                # Convert PlantProfile objects to Plant objects for monitoring
                for profile in profiles:
                    plant = Plant(
                        id=profile.plant_name,
                        ads_channel=profile.sensor_channel,
                        min_moisture_threshold=profile.acceptable_moisture_level
                    )
                    # Restore current state from database
                    if profile.current_moisture_level is not None:
                        plant.current_moisture = profile.current_moisture_level
                    self.plants.append(plant)

                logger.info(f"Loaded {len(profiles)} plant profiles from database")

                # Check for unmapped sensors and log warnings
                check_unmapped_sensors(db_path)
            else:
                # Database exists but no profiles yet - warn user
                logger.warning("No plant profiles found in database. Use setup_plants.py to create profiles.")
                logger.warning("Falling back to hardcoded plant defaults")
                self._init_default_plants()

        except Exception as e:
            # Database unavailable - fall back to hardcoded defaults (FR-005)
            logger.warning(f"Database unavailable ({e}), using hardcoded plant defaults")
            self._init_default_plants()

        # Initialize sensor reader (only on Raspberry Pi)
        if SENSOR_AVAILABLE:
            try:
                self.sensor = SensorReader(
                    address=self.config.ads1115_address,
                    gain=self.config.ads1115_gain,
                    voltage_dry=self.config.moisture_voltage_dry,
                    voltage_wet=self.config.moisture_voltage_wet
                )
                logger.info("Sensor reader initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize sensor reader: {e}")
                self.sensor = None
        else:
            logger.warning("Sensor reader not available (I2C libraries not found)")
            self.sensor = None

        # Initialize environmental sensor (BME688)
        if ENVIRONMENTAL_SENSOR_AVAILABLE:
            try:
                self.environmental_sensor = EnvironmentalSensorReader(
                    i2c_bus=1,     # I2C bus 1 (Raspberry Pi pins 3 & 5)
                    timeout=2.0    # 2 second timeout per spec
                )
                if self.environmental_sensor.is_available():
                    logger.info("Environmental sensor initialized successfully")
                else:
                    logger.warning("Environmental sensor not detected - monitoring will continue without environmental data")
                    self.environmental_sensor = None
            except Exception as e:
                logger.warning(f"Failed to initialize environmental sensor: {e}")
                self.environmental_sensor = None
        else:
            logger.debug("Environmental sensor library not available")
            self.environmental_sensor = None

        # Initialize ntfy.sh client
        self.notifier = NtfyClient(base_url=self.config.ntfy_url, max_retries=3)
        logger.info(f"Notification client initialized (topic: {self.config.ntfy_topic})")

    def _init_default_plants(self):
        """Initialize hardcoded default plants (fallback when database unavailable)."""
        self.plants = [
            Plant(
                id='Plant-A',
                ads_channel=0,
                min_moisture_threshold=self.config.moisture_threshold
            ),
            Plant(
                id='Plant-B',
                ads_channel=1,
                min_moisture_threshold=self.config.moisture_threshold
            ),
            Plant(
                id='Plant-C',
                ads_channel=2,
                min_moisture_threshold=self.config.moisture_threshold
            ),
        ]

    def read_sensors(self) -> List[SensorReading]:
        """Read moisture from all plant sensors.

        Returns:
            List of SensorReading objects (includes invalid readings with moisture_percent=None)
        """
        readings = []
        timestamp = datetime.utcnow()

        for plant in self.plants:
            if self.sensor is None:
                # Sensor not available (development mode)
                logger.debug(f"{plant.id}: Sensor not available (skipping)")
                continue

            try:
                # Read voltage and moisture from sensor (single ADC read)
                voltage, moisture = self.sensor.read_moisture_with_voltage(plant.ads_channel)

                # Create reading
                reading = SensorReading(
                    plant_id=plant.id,
                    timestamp=timestamp,
                    raw_adc_value=0,  # Not exposed by ADS1x15 library
                    voltage=voltage if voltage is not None else 0.0,
                    moisture_percent=moisture
                )

                readings.append(reading)

                # Update plant state if reading is valid
                if reading.is_valid and moisture is not None:
                    plant.current_moisture = moisture
                    logger.debug(f"{plant.id}: {moisture:.1f}% (voltage: {voltage:.3f}V)")

                    # Update current moisture in database (non-blocking, FR-017)
                    update_current_moisture(plant.id, moisture, self.db_path)
                else:
                    voltage_str = f"{voltage:.3f}V" if voltage is not None else "None"
                    moisture_str = f"{moisture:.1f}%" if moisture is not None else "None"
                    logger.error(
                        f"{plant.id}: Invalid reading (voltage: {voltage_str}, "
                        f"moisture: {moisture_str})"
                    )

            except Exception as e:
                logger.error(f"{plant.id}: Sensor read error: {e}", exc_info=True)
                continue

        return readings

    def check_thresholds(self) -> List[Plant]:
        """Check which plants need watering.

        Also handles throttle reset when plants are watered (moisture rises above
        threshold + 5% hysteresis buffer) and records watering events.

        Returns:
            List of plants that need water
        """
        plants_needing_water = []

        for plant in self.plants:
            # Check throttle reset (plant was watered)
            if (plant.current_moisture is not None and
                plant.current_moisture > plant.throttle_reset_threshold and
                plant.last_notification_time is not None):
                logger.info(
                    f"{plant.id}: Watering detected - moisture rose to {plant.current_moisture:.1f}% "
                    f"(above {plant.throttle_reset_threshold:.1f}% reset threshold)"
                )
                plant.last_notification_time = None

                # Record watering event in database (FR-009: detect threshold crossings)
                today = date.today()
                record_watering_event(plant.id, today, self.db_path)
                logger.info(f"{plant.id}: Recorded watering event on {today.isoformat()}")

                # Update needs_watering flag to False (plant no longer needs water)
                set_needs_watering_flag(plant.id, False, self.db_path)

            # Check if plant needs water
            if plant.needs_water:
                plants_needing_water.append(plant)
                logger.debug(f"{plant.id}: Needs water (moisture: {plant.current_moisture:.1f}%)")

                # Update needs_watering flag to True in database
                set_needs_watering_flag(plant.id, True, self.db_path)

        return plants_needing_water

    def send_notification(self, plant: Plant) -> Dict[str, Any]:
        """Send watering notification for a plant (with throttle check).

        Args:
            plant: Plant that needs watering

        Returns:
            Result dict from notifier with 'success' boolean
        """
        # Check throttle
        if plant.last_notification_time is not None:
            time_since_last = datetime.utcnow() - plant.last_notification_time
            throttle_delta = timedelta(seconds=self.config.throttle_duration)

            if time_since_last < throttle_delta:
                # Still throttled
                remaining = throttle_delta - time_since_last
                remaining_mins = int(remaining.total_seconds() / 60)
                logger.debug(
                    f"{plant.id}: DRY - throttled, last notified {remaining_mins}min ago "
                    f"(moisture: {plant.current_moisture:.1f}%)"
                )
                return {'success': False, 'error': 'Throttled'}

        # Generate notification message
        message = NotificationEvent.create_message(
            plant.id,
            plant.current_moisture if plant.current_moisture is not None else 0.0
        )

        # Send notification
        result = self.notifier.send_notification(
            topic=self.config.ntfy_topic,
            message=message,
            title='Plant Alert',
            priority=4,  # High priority
            tags='droplet,warning'
        )

        # Update throttle timer if successful
        if result['success']:
            plant.last_notification_time = datetime.utcnow()
            logger.info(
                f"{plant.id}: Notification sent - {message} "
                f"(next eligible in {self.config.throttle_duration / 3600:.1f}h)"
            )
        else:
            logger.error(
                f"{plant.id}: Notification failed - {result.get('error', 'Unknown error')}"
            )

        return result

    def monitor_cycle(self):
        """Execute one monitoring cycle.

        Reads all sensors, checks thresholds, and sends notifications as needed.
        Called repeatedly by the main loop.
        """
        logger.debug("Starting monitoring cycle")

        # Read all moisture sensors (FIRST - sequential I2C to avoid conflicts)
        readings = self.read_sensors()
        logger.info(
            f"Read {len(readings)} sensors: " +
            ", ".join([
                f"{p.id}: {p.current_moisture:.1f}% ({'DRY' if p.needs_water else 'OK'})"
                for p in self.plants if p.current_moisture is not None
            ])
        )

        # Read environmental sensor (AFTER moisture sensors - sequential I2C)
        if self.environmental_sensor is not None:
            try:
                env_reading = self.environmental_sensor.read()

                if env_reading.is_valid:
                    # Display environmental data with 2 decimal places
                    env_display = env_reading.format_for_display()
                    logger.info(f"Environment: {env_display}")
                else:
                    logger.warning("Environment: UNAVAILABLE (sensor read failed)")

            except Exception as e:
                logger.error(f"Environmental sensor read error: {e}")
                logger.info("Environment: ERROR")
        else:
            # Environmental sensor not initialized - skip silently (already warned at init)
            logger.debug("Environmental sensor not available - skipping environmental read")

        # Check thresholds
        plants_needing_water = self.check_thresholds()

        # Send notifications
        for plant in plants_needing_water:
            self.send_notification(plant)

        logger.debug("Monitoring cycle complete")
