#!/usr/bin/env python3
"""Automatic calibration utility for capacitive soil moisture sensors.

Usage:
    python3 src/cli/calibrate.py dry   # When sensors are in dry air
    python3 src/cli/calibrate.py wet   # When sensors are in water/wet soil

Reads actual voltage values and updates config/monitor.env automatically.
"""

import sys
import time
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.lib.sensor import SensorReader


def read_average_voltage(reader: SensorReader, channel: int, num_samples: int = 10) -> float:
    """Read average voltage from a sensor channel.

    Args:
        reader: Initialized SensorReader instance
        channel: ADC channel number (0, 1, or 2)
        num_samples: Number of samples to average

    Returns:
        Average voltage reading
    """
    voltages = []
    for i in range(num_samples):
        voltage = reader.read_channel(channel)
        if voltage is not None:
            voltages.append(voltage)
            print(f"  Channel {channel} reading {i+1}/{num_samples}: {voltage:.3f}V")
        else:
            print(f"  Channel {channel} reading {i+1}/{num_samples}: FAILED")

        if i < num_samples - 1:
            time.sleep(0.3)

    if not voltages:
        raise RuntimeError(f"Failed to read channel {channel}")

    avg = sum(voltages) / len(voltages)
    print(f"  Channel {channel} average: {avg:.3f}V\n")
    return avg


def update_env_file(key: str, value: float):
    """Update or add a key=value pair in config/monitor.env.

    Args:
        key: Environment variable name (e.g., "MOISTURE_VOLTAGE_DRY")
        value: Voltage value to set
    """
    config_dir = Path(__file__).parent.parent.parent / "config"
    config_dir.mkdir(exist_ok=True)
    env_file = config_dir / "monitor.env"

    # Read existing lines
    existing_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing_lines = [
                line for line in f.readlines()
                if not line.startswith(f"{key}=")
            ]

    # Write updated config
    with open(env_file, 'w') as f:
        f.writelines(existing_lines)
        if existing_lines and not existing_lines[-1].endswith('\n'):
            f.write('\n')
        f.write(f"{key}={value:.3f}\n")

    print(f"✅ Updated {env_file}")
    print(f"   {key}={value:.3f}\n")


def calibrate_dry():
    """Calibrate dry (air) voltage for all sensors."""
    print("=" * 60)
    print("DRY CALIBRATION")
    print("=" * 60)
    print("Ensure all sensors are in DRY AIR before continuing.")
    print("Reading sensors in 3 seconds...\n")
    time.sleep(3)

    # Initialize reader with dummy calibration values
    reader = SensorReader(
        address=0x48,
        gain=1,
        voltage_dry=3.0,
        voltage_wet=1.6
    )

    print("Reading all sensor channels...\n")

    # Read all three channels
    voltages = []
    for channel in range(3):
        try:
            voltage = read_average_voltage(reader, channel, num_samples=10)
            voltages.append(voltage)
        except RuntimeError as e:
            print(f"⚠️  Warning: {e}")

    if not voltages:
        print("❌ No successful readings. Check sensor connections.")
        return 1

    # Use the average of all connected sensors
    avg_voltage = sum(voltages) / len(voltages)

    print("=" * 60)
    print(f"DRY voltage (average of {len(voltages)} sensors): {avg_voltage:.3f}V")
    print("=" * 60)

    # Update env file
    update_env_file("MOISTURE_VOLTAGE_DRY", avg_voltage)

    print("Next step: Run this script with 'wet' when sensors are in water:")
    print("  uv run python3 src/cli/calibrate.py wet\n")

    return 0


def calibrate_wet():
    """Calibrate wet (water) voltage for all sensors."""
    print("=" * 60)
    print("WET CALIBRATION")
    print("=" * 60)
    print("Ensure all sensors are in WATER or VERY WET SOIL before continuing.")
    print("Reading sensors in 3 seconds...\n")
    time.sleep(3)

    # Initialize reader with dummy calibration values
    reader = SensorReader(
        address=0x48,
        gain=1,
        voltage_dry=3.0,
        voltage_wet=1.6
    )

    print("Reading all sensor channels...\n")

    # Read all three channels
    voltages = []
    for channel in range(3):
        try:
            voltage = read_average_voltage(reader, channel, num_samples=10)
            voltages.append(voltage)
        except RuntimeError as e:
            print(f"⚠️  Warning: {e}")

    if not voltages:
        print("❌ No successful readings. Check sensor connections.")
        return 1

    # Use the average of all connected sensors
    avg_voltage = sum(voltages) / len(voltages)

    print("=" * 60)
    print(f"WET voltage (average of {len(voltages)} sensors): {avg_voltage:.3f}V")
    print("=" * 60)

    # Update env file
    update_env_file("MOISTURE_VOLTAGE_WET", avg_voltage)

    print("Calibration complete! You can now run the monitor:")
    print("  uv run python3 src/cli/monitor.py\n")

    # Show final calibration summary
    config_dir = Path(__file__).parent.parent.parent / "config"
    env_file = config_dir / "monitor.env"

    if env_file.exists():
        print("=" * 60)
        print("Current calibration values in config/monitor.env:")
        print("=" * 60)
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith("MOISTURE_VOLTAGE_"):
                    print(f"  {line.rstrip()}")
        print()

    return 0


def main():
    """Run calibration based on command line argument."""
    if len(sys.argv) != 2 or sys.argv[1] not in ('dry', 'wet'):
        print("Usage:")
        print("  python3 src/cli/calibrate.py dry   # Calibrate dry (air) voltage")
        print("  python3 src/cli/calibrate.py wet   # Calibrate wet (water) voltage")
        print()
        print("Workflow:")
        print("  1. Place all sensors in dry air")
        print("  2. Run: uv run python3 src/cli/calibrate.py dry")
        print("  3. Place all sensors in water or very wet soil")
        print("  4. Run: uv run python3 src/cli/calibrate.py wet")
        print("  5. Start monitoring: uv run python3 src/cli/monitor.py")
        return 1

    mode = sys.argv[1]

    try:
        if mode == 'dry':
            return calibrate_dry()
        else:
            return calibrate_wet()
    except KeyboardInterrupt:
        print("\n\nCalibration cancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
