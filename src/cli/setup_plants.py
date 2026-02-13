#!/usr/bin/env python3
"""Interactive CLI setup script for creating plant profiles.

Prompts users for plant name, sensor channel, and moisture threshold,
validates inputs, and stores profiles in the database.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.lib.database import (
    initialize_database,
    create_plant_profile,
    load_all_profiles,
    load_profile_by_channel,
    DEFAULT_DB_PATH
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def prompt_plant_name(db_path: str = DEFAULT_DB_PATH) -> str:
    """Prompt for plant name with validation.

    Args:
        db_path: Path to database for duplicate checking

    Returns:
        Valid plant name (1-50 characters, unique)
    """
    while True:
        name = input("Enter plant name (e.g., Basil, Tomato): ").strip()

        # Validate non-empty
        if not name:
            print("❌ Plant name cannot be empty.")
            continue

        # Validate length
        if len(name) > 50:
            print("❌ Plant name too long (max 50 characters).")
            continue

        # Check for duplicates
        try:
            profiles = load_all_profiles(db_path)
            if any(p.plant_name == name for p in profiles):
                print(f"❌ Plant name '{name}' already exists. Choose a different name.")
                continue
        except Exception as e:
            logger.warning(f"Could not check for duplicates: {e}")

        return name


def prompt_sensor_channel(db_path: str = DEFAULT_DB_PATH) -> int:
    """Prompt for sensor channel with validation.

    Args:
        db_path: Path to database for duplicate checking

    Returns:
        Valid sensor channel (0, 1, or 2), not already assigned
    """
    # Get assigned channels
    try:
        profiles = load_all_profiles(db_path)
        assigned_channels = {p.sensor_channel for p in profiles}
        available_channels = set([0, 1, 2]) - assigned_channels

        if available_channels:
            print(f"Available sensor channels: {', '.join(map(str, sorted(available_channels)))}")
        else:
            print("⚠️  All sensor channels (0, 1, 2) are already assigned.")
    except Exception as e:
        logger.warning(f"Could not check assigned channels: {e}")
        assigned_channels = set()

    while True:
        channel_str = input("Which sensor channel monitors this plant? ").strip()

        # Validate numeric
        try:
            channel = int(channel_str)
        except ValueError:
            print("❌ Please enter a number (0, 1, or 2).")
            continue

        # Validate range
        if channel not in (0, 1, 2):
            print("❌ Sensor channel must be 0, 1, or 2.")
            continue

        # Check if already assigned
        if channel in assigned_channels:
            existing_profile = load_profile_by_channel(channel, db_path)
            existing_name = existing_profile.plant_name if existing_profile else "unknown"
            print(f"❌ Sensor channel {channel} is already assigned to '{existing_name}'.")

            remaining = set([0, 1, 2]) - assigned_channels
            if remaining:
                print(f"   Available channels: {', '.join(map(str, sorted(remaining)))}")
            continue

        return channel


def prompt_moisture_threshold() -> float:
    """Prompt for moisture threshold with validation.

    Returns:
        Valid moisture threshold (0.0-100.0%)
    """
    while True:
        threshold_str = input("Enter moisture threshold for this plant (0-100%): ").strip()

        # Validate numeric
        try:
            threshold = float(threshold_str)
        except ValueError:
            print("❌ Please enter a number between 0 and 100.")
            continue

        # Validate range
        if not 0.0 <= threshold <= 100.0:
            print("❌ Moisture threshold must be between 0 and 100%.")
            continue

        return threshold


def main():
    """Main setup wizard loop."""
    print("=" * 60)
    print("Plant Profile Setup")
    print("=" * 60)
    print()

    db_path = DEFAULT_DB_PATH

    # Ensure database is initialized
    try:
        initialize_database(db_path)
        logger.info(f"Database ready at {db_path}")
    except Exception as e:
        print(f"❌ Error: Failed to initialize database: {e}")
        logger.error(f"Database initialization failed: {e}")
        return 1

    created_profiles = []

    while True:
        try:
            # Prompt for profile details
            plant_name = prompt_plant_name(db_path)
            sensor_channel = prompt_sensor_channel(db_path)
            threshold = prompt_moisture_threshold()

            # Show summary and confirm
            print()
            print("=" * 60)
            print("Profile Summary")
            print("=" * 60)
            print(f"Plant name:         {plant_name}")
            print(f"Sensor channel:     {sensor_channel}")
            print(f"Moisture threshold: {threshold}%")
            print()

            confirm = input("Save this profile? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Profile discarded.")
                print()
                continue

            # Create profile
            try:
                create_plant_profile(plant_name, sensor_channel, threshold, db_path)
                print()
                print("✅ Profile saved successfully!")
                created_profiles.append((plant_name, sensor_channel, threshold))
                logger.info(f"Profile created: {plant_name} (channel {sensor_channel}, threshold {threshold}%)")
                print()

            except Exception as e:
                print(f"❌ Error: Failed to save profile: {e}")
                logger.error(f"Profile creation failed: {e}", exc_info=True)
                print()

            # Ask if user wants to create another
            another = input("Create another profile? (y/n): ").strip().lower()
            if another != 'y':
                break

            print()

        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            logger.info("Setup cancelled by user")
            return 130

    # Show final summary
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()

    if created_profiles:
        print(f"Created {len(created_profiles)} plant profile(s):")
        for name, channel, threshold in created_profiles:
            print(f"  - {name} (channel {channel}, threshold {threshold}%)")
        print()
        print("Next steps:")
        print("  1. Start monitoring: uv run python3 src/cli/monitor.py")
        print("  2. View profiles: sqlite3 data/plants.db \"SELECT * FROM plant_profiles;\"")
    else:
        print("No profiles created.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
