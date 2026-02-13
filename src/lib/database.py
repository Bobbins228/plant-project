"""Database operations library for plant profile management.

Provides SQLite database connection management and CRUD operations
for plant profiles. Implements context manager pattern for safe
connection handling.
"""

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional
from datetime import date

from src.models.plant_profile import PlantProfile

logger = logging.getLogger(__name__)

# Default database location
DEFAULT_DB_PATH = "data/plants.db"


@contextmanager
def get_db_connection(db_path: str = DEFAULT_DB_PATH):
    """Context manager for database connections.

    Args:
        db_path: Path to SQLite database file

    Yields:
        sqlite3.Connection: Database connection with row_factory configured

    Raises:
        sqlite3.Error: If database connection fails

    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM plant_profiles")
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access

        # Set pragmas for better performance and data integrity
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize database schema.

    Creates the plant_profiles table if it doesn't exist, with all
    required constraints and indexes.

    Args:
        db_path: Path to SQLite database file

    Raises:
        sqlite3.Error: If schema creation fails
    """
    # Ensure directory exists
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plant_profiles (
                    -- Identity & Configuration
                    plant_name TEXT PRIMARY KEY,
                    sensor_channel INTEGER NOT NULL UNIQUE,
                    acceptable_moisture_level REAL NOT NULL,

                    -- Current State
                    current_moisture_level REAL,
                    needs_watering INTEGER NOT NULL DEFAULT 0,
                    date_last_watered TEXT,

                    -- Constraints
                    CHECK (sensor_channel IN (0, 1, 2)),
                    CHECK (acceptable_moisture_level >= 0.0 AND acceptable_moisture_level <= 100.0),
                    CHECK (current_moisture_level IS NULL OR (current_moisture_level >= 0.0 AND current_moisture_level <= 100.0))
                )
            """)
            conn.commit()
            logger.info(f"Database initialized at {db_path}")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def create_plant_profile(
    plant_name: str,
    sensor_channel: int,
    acceptable_moisture_level: float,
    db_path: str = DEFAULT_DB_PATH
) -> None:
    """Create a new plant profile.

    Args:
        plant_name: Unique plant identifier
        sensor_channel: ADS1115 channel (0, 1, or 2)
        acceptable_moisture_level: Moisture threshold percentage (0-100)
        db_path: Path to SQLite database file

    Raises:
        sqlite3.IntegrityError: If plant_name or sensor_channel already exists
        sqlite3.Error: For other database errors
    """
    # Validate using PlantProfile model
    profile = PlantProfile(
        plant_name=plant_name,
        sensor_channel=sensor_channel,
        acceptable_moisture_level=acceptable_moisture_level
    )

    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                INSERT INTO plant_profiles (
                    plant_name,
                    sensor_channel,
                    acceptable_moisture_level,
                    needs_watering
                ) VALUES (?, ?, ?, 0)
            """, (plant_name, sensor_channel, acceptable_moisture_level))
            conn.commit()
            logger.info(f"Created plant profile: {plant_name} (channel {sensor_channel}, threshold {acceptable_moisture_level}%)")
    except sqlite3.IntegrityError as e:
        logger.error(f"Failed to create profile '{plant_name}': {e}")
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error creating profile: {e}")
        raise


def load_all_profiles(db_path: str = DEFAULT_DB_PATH) -> List[PlantProfile]:
    """Load all plant profiles from database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        List of PlantProfile objects ordered by sensor_channel

    Raises:
        sqlite3.Error: If database read fails
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    plant_name,
                    sensor_channel,
                    acceptable_moisture_level,
                    current_moisture_level,
                    needs_watering,
                    date_last_watered
                FROM plant_profiles
                ORDER BY sensor_channel
            """)
            rows = cursor.fetchall()

            profiles = [PlantProfile.from_db_row(dict(row)) for row in rows]
            logger.debug(f"Loaded {len(profiles)} plant profiles")
            return profiles

    except sqlite3.Error as e:
        logger.error(f"Failed to load profiles: {e}")
        raise


def load_profile_by_channel(
    sensor_channel: int,
    db_path: str = DEFAULT_DB_PATH
) -> Optional[PlantProfile]:
    """Load plant profile for specific sensor channel.

    Args:
        sensor_channel: ADS1115 channel (0, 1, or 2)
        db_path: Path to SQLite database file

    Returns:
        PlantProfile if exists, None if channel unmapped

    Raises:
        sqlite3.Error: If database read fails
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    plant_name,
                    sensor_channel,
                    acceptable_moisture_level,
                    current_moisture_level,
                    needs_watering,
                    date_last_watered
                FROM plant_profiles
                WHERE sensor_channel = ?
            """, (sensor_channel,))
            row = cursor.fetchone()

            if row:
                profile = PlantProfile.from_db_row(dict(row))
                logger.debug(f"Loaded profile for channel {sensor_channel}: {profile.plant_name}")
                return profile
            else:
                logger.debug(f"No profile found for channel {sensor_channel}")
                return None

    except sqlite3.Error as e:
        logger.error(f"Failed to load profile for channel {sensor_channel}: {e}")
        raise


def update_current_moisture(
    plant_name: str,
    moisture_level: float,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """Update plant's current moisture reading.

    Args:
        plant_name: Plant identifier
        moisture_level: Moisture percentage (0-100)
        db_path: Path to SQLite database file

    Returns:
        True if successful, False on error

    Note:
        Logs errors but does not raise exceptions to allow
        monitoring to continue on database failures (FR-017)
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                UPDATE plant_profiles
                SET current_moisture_level = ?
                WHERE plant_name = ?
            """, (moisture_level, plant_name))
            conn.commit()
            logger.debug(f"Updated moisture for {plant_name}: {moisture_level:.1f}%")
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to update moisture for {plant_name}: {e}")
        return False


def set_needs_watering_flag(
    plant_name: str,
    needs_watering: bool,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """Update needs_watering flag for plant.

    Args:
        plant_name: Plant identifier
        needs_watering: True if plant needs water, False otherwise
        db_path: Path to SQLite database file

    Returns:
        True if successful, False on error

    Note:
        Logs errors but does not raise exceptions to allow
        monitoring to continue on database failures (FR-017)
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                UPDATE plant_profiles
                SET needs_watering = ?
                WHERE plant_name = ?
            """, (1 if needs_watering else 0, plant_name))
            conn.commit()
            logger.debug(f"Updated needs_watering for {plant_name}: {needs_watering}")
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to update needs_watering for {plant_name}: {e}")
        return False


def record_watering_event(
    plant_name: str,
    watered_date: date,
    db_path: str = DEFAULT_DB_PATH
) -> bool:
    """Record that plant was watered.

    Sets needs_watering to False and updates date_last_watered.

    Args:
        plant_name: Plant identifier
        watered_date: Date plant was watered
        db_path: Path to SQLite database file

    Returns:
        True if successful, False on error

    Note:
        Logs errors but does not raise exceptions to allow
        monitoring to continue on database failures (FR-017)
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.execute("""
                UPDATE plant_profiles
                SET needs_watering = 0,
                    date_last_watered = ?
                WHERE plant_name = ?
            """, (watered_date.isoformat(), plant_name))
            conn.commit()
            logger.info(f"Recorded watering event for {plant_name}: {watered_date}")
            return True
    except sqlite3.Error as e:
        logger.error(f"Failed to record watering for {plant_name}: {e}")
        return False


def check_unmapped_sensors(db_path: str = DEFAULT_DB_PATH) -> List[int]:
    """Check for unmapped sensor channels and log warnings.

    Scans all valid sensor channels (0, 1, 2) and logs warnings
    for any channels not assigned to plant profiles.

    Args:
        db_path: Path to SQLite database file

    Returns:
        List of unmapped sensor channel numbers

    Note:
        This function is intended to be called at monitoring startup
        to warn users about sensors that won't be monitored.
    """
    all_channels = [0, 1, 2]
    unmapped_channels = []

    try:
        profiles = load_all_profiles(db_path)
        mapped_channels = {p.sensor_channel for p in profiles}

        for channel in all_channels:
            if channel not in mapped_channels:
                unmapped_channels.append(channel)
                logger.warning(
                    f"Sensor channel {channel} is not assigned to any plant profile. "
                    f"Sensor readings from this channel will be ignored."
                )

        if unmapped_channels:
            logger.info(f"Unmapped sensor channels: {unmapped_channels}")
        else:
            logger.info("All sensor channels (0, 1, 2) are assigned to plant profiles")

    except sqlite3.Error as e:
        logger.error(f"Failed to check unmapped sensors: {e}")

    return unmapped_channels
