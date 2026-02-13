"""Plant data model for moisture monitoring."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Plant:
    """In-memory plant configuration and state.

    Represents a monitored plant with its configuration (channel, threshold)
    and runtime state (current moisture, last notification time).

    Attributes:
        id: Plant identifier ("Plant-A", "Plant-B", "Plant-C")
        ads_channel: ADS1115 ADC channel number (0, 1, or 2)
        min_moisture_threshold: Minimum acceptable moisture percentage (default 40.0)
        current_moisture: Most recent moisture reading (0-100%), None if invalid/no reading
        last_notification_time: Timestamp of last watering notification, None if never notified
    """

    id: str  # "Plant-A", "Plant-B", "Plant-C"
    ads_channel: int  # 0, 1, 2
    min_moisture_threshold: float = 40.0  # percentage
    current_moisture: Optional[float] = None  # percentage or None
    last_notification_time: Optional[datetime] = None

    def __post_init__(self):
        """Validate plant configuration after initialization."""
        if self.id not in ("Plant-A", "Plant-B", "Plant-C"):
            raise ValueError(f"Invalid plant ID: {self.id}. Must be Plant-A, Plant-B, or Plant-C")

        if self.ads_channel not in (0, 1, 2):
            raise ValueError(f"Invalid ADS channel: {self.ads_channel}. Must be 0, 1, or 2")

        if not 0.0 <= self.min_moisture_threshold <= 100.0:
            raise ValueError(f"Invalid threshold: {self.min_moisture_threshold}. Must be 0-100%")

    @property
    def needs_water(self) -> bool:
        """True if current moisture is below threshold.

        Returns False if current_moisture is None (no valid reading yet).
        """
        if self.current_moisture is None:
            return False
        return self.current_moisture < self.min_moisture_threshold

    @property
    def throttle_reset_threshold(self) -> float:
        """Moisture level that resets throttle timer (threshold + 5%).

        Hysteresis buffer prevents notification flapping when moisture
        fluctuates around the threshold.
        """
        return self.min_moisture_threshold + 5.0
