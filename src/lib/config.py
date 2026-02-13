"""Configuration loader for plant monitoring system."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class MonitorConfig:
    """Plant monitoring system configuration.

    Loaded from environment variables or .env file.
    """

    # Moisture thresholds
    moisture_threshold: float
    moisture_voltage_dry: float
    moisture_voltage_wet: float

    # Monitoring behavior
    sampling_interval: int  # seconds
    throttle_duration: int  # seconds

    # Notifications
    ntfy_topic: str
    ntfy_url: str

    # Logging
    log_level: str

    # Hardware
    ads1115_address: int
    ads1115_gain: int

    def validate(self):
        """Validate configuration values are within acceptable ranges.

        Raises:
            ValueError: If any configuration value is invalid.
        """
        # Validate moisture threshold
        if not 0.0 <= self.moisture_threshold <= 100.0:
            raise ValueError(
                f"MOISTURE_THRESHOLD must be 0-100%, got {self.moisture_threshold}%"
            )

        # Validate voltage calibration (dry > wet)
        if self.moisture_voltage_dry <= self.moisture_voltage_wet:
            raise ValueError(
                f"MOISTURE_VOLTAGE_DRY ({self.moisture_voltage_dry}V) must be greater than "
                f"MOISTURE_VOLTAGE_WET ({self.moisture_voltage_wet}V)"
            )

        # Validate voltage ranges (typical for ADS1115 at gain=1)
        if not 0.0 <= self.moisture_voltage_dry <= 5.0:
            raise ValueError(
                f"MOISTURE_VOLTAGE_DRY must be 0-5V, got {self.moisture_voltage_dry}V"
            )
        if not 0.0 <= self.moisture_voltage_wet <= 5.0:
            raise ValueError(
                f"MOISTURE_VOLTAGE_WET must be 0-5V, got {self.moisture_voltage_wet}V"
            )

        # Validate sampling interval (prevent too frequent polling)
        if self.sampling_interval < 10:
            raise ValueError(
                f"SAMPLING_INTERVAL must be at least 10 seconds, got {self.sampling_interval}s"
            )

        # Validate throttle duration (prevent too short throttle)
        if self.throttle_duration < 60:
            raise ValueError(
                f"THROTTLE_DURATION must be at least 60 seconds, got {self.throttle_duration}s"
            )

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_log_levels}, got {self.log_level}"
            )

        # Validate ADS1115 address (standard I2C addresses)
        valid_addresses = [0x48, 0x49, 0x4A, 0x4B]
        if self.ads1115_address not in valid_addresses:
            raise ValueError(
                f"ADS1115_ADDRESS must be one of {[hex(a) for a in valid_addresses]}, "
                f"got {hex(self.ads1115_address)}"
            )

        # Validate ADS1115 gain
        valid_gains = [1, 2, 4, 8, 16]  # ADS1115 programmable gain values
        if self.ads1115_gain not in valid_gains:
            raise ValueError(
                f"ADS1115_GAIN must be one of {valid_gains}, got {self.ads1115_gain}"
            )

        # Validate ntfy topic is not empty
        if not self.ntfy_topic or not self.ntfy_topic.strip():
            raise ValueError("NTFY_TOPIC cannot be empty")

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "MonitorConfig":
        """Load configuration from environment or .env file.

        Args:
            env_file: Path to .env file. If None, searches for config/monitor.env
                     then .env in current directory.

        Returns:
            MonitorConfig instance with loaded values.

        Raises:
            ValueError: If required configuration is missing or invalid.
        """
        # Load from .env file if it exists
        if env_file:
            load_dotenv(env_file)
        else:
            # Try config/monitor.env first, then .env
            config_path = Path("config/monitor.env")
            if config_path.exists():
                load_dotenv(config_path)
            else:
                load_dotenv()  # Tries .env in current directory

        def get_float(key: str, default: float) -> float:
            """Get float value from environment."""
            value = os.getenv(key)
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Invalid {key}: {value}. Must be a number.")

        def get_int(key: str, default: int) -> int:
            """Get integer value from environment."""
            value = os.getenv(key)
            if value is None:
                return default
            try:
                # Handle hex values (e.g., 0x48)
                if value.startswith("0x"):
                    return int(value, 16)
                return int(value)
            except ValueError:
                raise ValueError(f"Invalid {key}: {value}. Must be an integer.")

        def get_str(key: str, default: str) -> str:
            """Get string value from environment."""
            return os.getenv(key, default)

        config = cls(
            moisture_threshold=get_float("MOISTURE_THRESHOLD", 40.0),
            moisture_voltage_dry=get_float("MOISTURE_VOLTAGE_DRY", 1.2),
            moisture_voltage_wet=get_float("MOISTURE_VOLTAGE_WET", 0.5),
            sampling_interval=get_int("SAMPLING_INTERVAL", 30),
            throttle_duration=get_int("THROTTLE_DURATION", 21600),  # 6 hours
            ntfy_topic=get_str("NTFY_TOPIC", "mark-test-watering-monitor"),
            ntfy_url=get_str("NTFY_URL", "https://ntfy.sh"),
            log_level=get_str("LOG_LEVEL", "INFO"),
            ads1115_address=get_int("ADS1115_ADDRESS", 0x48),
            ads1115_gain=get_int("ADS1115_GAIN", 1),
        )

        # Validate configuration values
        config.validate()

        return config
