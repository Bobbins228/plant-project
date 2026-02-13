"""Core moisture monitoring logic with notification and throttling.

Implements the main monitoring loop that reads sensors, checks thresholds,
sends notifications, and manages throttle timers.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from src.models.plant import Plant
from src.models.sensor_reading import SensorReading
from src.models.notification_event import NotificationEvent
from src.lib.config import MonitorConfig
from src.lib.notifier import NtfyClient

try:
    from src.lib.sensor import SensorReader
    SENSOR_AVAILABLE = True
except RuntimeError:
    # I2C not available (development on Mac)
    SENSOR_AVAILABLE = False
    SensorReader = None

logger = logging.getLogger(__name__)


class MoistureMonitor:
    """Main moisture monitoring system.

    Coordinates sensor reading, threshold checking, and notification sending
    for multiple plants with independent throttle timers.
    """

    def __init__(self, config: MonitorConfig):
        """Initialize moisture monitor.

        Args:
            config: System configuration
        """
        self.config = config

        # Initialize plants (hardcoded for MVP, future: load from database)
        self.plants: List[Plant] = [
            Plant(
                id='Plant-A',
                ads_channel=0,
                min_moisture_threshold=config.moisture_threshold
            ),
            Plant(
                id='Plant-B',
                ads_channel=1,
                min_moisture_threshold=config.moisture_threshold
            ),
            Plant(
                id='Plant-C',
                ads_channel=2,
                min_moisture_threshold=config.moisture_threshold
            ),
        ]

        # Initialize sensor reader (only on Raspberry Pi)
        if SENSOR_AVAILABLE:
            try:
                self.sensor = SensorReader(
                    address=config.ads1115_address,
                    gain=config.ads1115_gain,
                    voltage_dry=config.moisture_voltage_dry,
                    voltage_wet=config.moisture_voltage_wet
                )
                logger.info("Sensor reader initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize sensor reader: {e}")
                self.sensor = None
        else:
            logger.warning("Sensor reader not available (I2C libraries not found)")
            self.sensor = None

        # Initialize ntfy.sh client
        self.notifier = NtfyClient(base_url=config.ntfy_url, max_retries=3)
        logger.info(f"Notification client initialized (topic: {config.ntfy_topic})")

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
        threshold + 5% hysteresis buffer).

        Returns:
            List of plants that need water
        """
        plants_needing_water = []

        for plant in self.plants:
            # Check throttle reset (plant was watered)
            if (plant.current_moisture is not None and
                plant.current_moisture > plant.throttle_reset_threshold and
                plant.last_notification_time is not None):
                logger.info(f"{plant.id}: OK - throttle reset (moisture: {plant.current_moisture:.1f}%)")
                plant.last_notification_time = None

            # Check if plant needs water
            if plant.needs_water:
                plants_needing_water.append(plant)
                logger.debug(f"{plant.id}: Needs water (moisture: {plant.current_moisture:.1f}%)")

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

        # Read all sensors
        readings = self.read_sensors()
        logger.info(
            f"Read {len(readings)} sensors: " +
            ", ".join([
                f"{p.id}: {p.current_moisture:.1f}% ({'DRY' if p.needs_water else 'OK'})"
                for p in self.plants if p.current_moisture is not None
            ])
        )

        # Check thresholds
        plants_needing_water = self.check_thresholds()

        # Send notifications
        for plant in plants_needing_water:
            self.send_notification(plant)

        logger.debug("Monitoring cycle complete")
