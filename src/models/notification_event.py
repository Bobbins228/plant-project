"""Notification event data model for watering alerts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NotificationEvent:
    """Watering notification sent to ntfy.sh.

    Represents an alert message sent when a plant needs watering.

    Attributes:
        plant_id: Which plant needs watering ("Plant-A", "Plant-B", "Plant-C")
        timestamp: When notification was sent (UTC)
        moisture_percent: Current moisture level that triggered alert
        message: Notification message body (e.g., "Plant-A needs watering (moisture: 35%)")
        success: True if ntfy.sh API returned 200 OK, False if failed
        error_message: Error details if success=False, None otherwise
    """

    plant_id: str
    timestamp: datetime
    moisture_percent: float
    message: str
    success: bool
    error_message: Optional[str] = None

    @classmethod
    def create_message(cls, plant_id: str, moisture_percent: float) -> str:
        """Generate notification message text.

        Args:
            plant_id: Plant identifier (e.g., "Plant-A")
            moisture_percent: Current moisture level (0-100%)

        Returns:
            Formatted message: "{plant_id} needs watering (moisture: {percent}%)"
        """
        return f"{plant_id} needs watering (moisture: {moisture_percent:.0f}%)"
