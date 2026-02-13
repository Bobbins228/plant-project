"""Plant profile data model.

Represents a monitored plant with its configuration and current state.
Attributes match database schema for easy ORM-free mapping.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class PlantProfile:
    """Plant profile with configuration and current state.

    Attributes match database schema for easy ORM-free mapping.
    """

    # Identity & Configuration
    plant_name: str
    sensor_channel: int
    acceptable_moisture_level: float

    # Current State
    current_moisture_level: Optional[float] = None
    needs_watering: bool = False
    date_last_watered: Optional[date] = None
    image_path: Optional[str] = None  # Path to plant image (feature 004)

    def __post_init__(self):
        """Validate attributes after initialization."""
        # Validate sensor channel
        if self.sensor_channel not in (0, 1, 2, 3):
            raise ValueError(f"sensor_channel must be 0-3, got {self.sensor_channel}")

        # Validate acceptable moisture level
        if not 0.0 <= self.acceptable_moisture_level <= 100.0:
            raise ValueError(
                f"acceptable_moisture_level must be 0-100%, got {self.acceptable_moisture_level}"
            )

        # Validate current moisture level if present
        if self.current_moisture_level is not None:
            if not 0.0 <= self.current_moisture_level <= 100.0:
                raise ValueError(
                    f"current_moisture_level must be 0-100% or None, got {self.current_moisture_level}"
                )

        # Validate plant name
        if not self.plant_name or len(self.plant_name) > 50:
            raise ValueError(f"plant_name must be 1-50 characters, got '{self.plant_name}'")

    @classmethod
    def from_db_row(cls, row: dict) -> "PlantProfile":
        """Create PlantProfile from database row (sqlite3.Row as dict).

        Args:
            row: Database row as dict with keys matching column names

        Returns:
            PlantProfile instance

        Raises:
            ValueError: If row data fails validation
        """
        return cls(
            plant_name=row["plant_name"],
            sensor_channel=row["sensor_channel"],
            acceptable_moisture_level=row["acceptable_moisture_level"],
            current_moisture_level=row["current_moisture_level"],
            needs_watering=bool(row["needs_watering"]),
            date_last_watered=date.fromisoformat(row["date_last_watered"])
                if row["date_last_watered"] else None,
            image_path=row.get("image_path")  # Optional field (feature 004)
        )
