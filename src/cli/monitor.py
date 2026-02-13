"""CLI entry point for plant monitoring daemon.

Implements graceful shutdown with signal handlers and configurable logging.
"""

import signal
import sys
import time
import logging
import logging.handlers
from pathlib import Path
from typing import NoReturn

# Add project root to Python path to allow imports when run directly
# This allows running the script as: python3 src/cli/monitor.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.lib.config import MonitorConfig
from src.lib.moisture_monitor import MoistureMonitor


class GracefulKiller:
    """Handle signals for graceful shutdown.

    Implements signal handling pattern from research.md for clean daemon shutdown.
    """

    def __init__(self):
        """Initialize signal handlers."""
        self.shutdown_requested = False
        # Register signal handlers
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, signum, frame):
        """Signal handler that sets shutdown flag.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logging.info(f'Received signal {signum}, requesting graceful shutdown')
        self.shutdown_requested = True

    def should_continue(self) -> bool:
        """Check if daemon should continue running.

        Returns:
            True if should continue, False if shutdown requested
        """
        return not self.shutdown_requested


def configure_logging(log_level: str):
    """Configure structured logging with file rotation.

    Args:
        log_level: Log level string ('INFO' or 'DEBUG')
    """
    # Parse log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Console handler (for foreground testing)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (if /var/log writable, else local file)
    log_file = Path("/var/log/plant-monitor.log")
    if not log_file.parent.exists() or not log_file.parent.is_dir():
        # Fall back to local log file
        log_file = Path("plant-monitor.log")

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # Can't write to log file, console only
        logging.warning(f"Could not create log file {log_file}: {e}")

    logging.info(f"Logging configured at {log_level} level")


def calibrate_dry():
    """Calibration utility: read all sensors in air and suggest voltage_dry value."""
    print("=== Dry Calibration (Sensors in Air) ===")
    print("Ensure all sensors are removed from soil and in free air.")
    print("Waiting 5 seconds for stabilization...")
    time.sleep(5)

    try:
        from src.lib.sensor import SensorReader

        # Use default calibration for reading
        sensor = SensorReader(voltage_dry=3.0, voltage_wet=1.6)

        voltages = []
        for channel in range(3):
            voltage = sensor.read_channel(channel)
            if voltage is not None:
                print(f"Channel {channel} (Plant-{'ABC'[channel]}): {voltage:.3f}V")
                voltages.append(voltage)
            else:
                print(f"Channel {channel}: Read failed")

        if voltages:
            avg_voltage = sum(voltages) / len(voltages)
            print(f"\nAverage dry voltage: {avg_voltage:.3f}V")
            print(f"\nUpdate config/monitor.env:")
            print(f"MOISTURE_VOLTAGE_DRY={avg_voltage:.2f}")
        else:
            print("\nNo valid readings obtained. Check sensor connections.")

    except RuntimeError as e:
        print(f"Error: {e}")
        print("Calibration requires Raspberry Pi with I2C hardware.")


def calibrate_wet():
    """Calibration utility: read all sensors in water and suggest voltage_wet value."""
    print("=== Wet Calibration (Sensors in Water) ===")
    print("Submerge sensor probes in distilled water (keep electronics dry!).")
    print("Waiting 5 seconds for stabilization...")
    time.sleep(5)

    try:
        from src.lib.sensor import SensorReader

        # Use default calibration for reading
        sensor = SensorReader(voltage_dry=3.0, voltage_wet=1.6)

        voltages = []
        for channel in range(3):
            voltage = sensor.read_channel(channel)
            if voltage is not None:
                print(f"Channel {channel} (Plant-{'ABC'[channel]}): {voltage:.3f}V")
                voltages.append(voltage)
            else:
                print(f"Channel {channel}: Read failed")

        if voltages:
            avg_voltage = sum(voltages) / len(voltages)
            print(f"\nAverage wet voltage: {avg_voltage:.3f}V")
            print(f"\nUpdate config/monitor.env:")
            print(f"MOISTURE_VOLTAGE_WET={avg_voltage:.2f}")
        else:
            print("\nNo valid readings obtained. Check sensor connections.")

    except RuntimeError as e:
        print(f"Error: {e}")
        print("Calibration requires Raspberry Pi with I2C hardware.")


def main() -> NoReturn:
    """Main daemon loop.

    Loads configuration, initializes monitor, and runs continuous monitoring
    loop with graceful shutdown handling.
    """
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--calibrate-dry':
            calibrate_dry()
            sys.exit(0)
        elif sys.argv[1] == '--calibrate-wet':
            calibrate_wet()
            sys.exit(0)
        elif sys.argv[1] in ('--help', '-h'):
            print("Plant Monitoring System")
            print("\nUsage:")
            print("  python3 -m src.cli.monitor              Run monitoring daemon")
            print("  python3 -m src.cli.monitor --calibrate-dry   Calibrate dry voltage")
            print("  python3 -m src.cli.monitor --calibrate-wet   Calibrate wet voltage")
            print("\nConfiguration: config/monitor.env")
            sys.exit(0)

    # Load configuration
    try:
        config = MonitorConfig.load()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Ensure config/monitor.env exists or set environment variables.")
        sys.exit(1)

    # Configure logging
    configure_logging(config.log_level)

    logging.info("=" * 60)
    logging.info("Plant Monitoring Daemon Starting")
    logging.info("=" * 60)
    logging.info(f"Configuration:")
    logging.info(f"  Moisture threshold: {config.moisture_threshold}%")
    logging.info(f"  Sampling interval: {config.sampling_interval}s")
    logging.info(f"  Throttle duration: {config.throttle_duration}s ({config.throttle_duration / 3600:.1f}h)")
    logging.info(f"  ntfy.sh topic: {config.ntfy_topic}")
    logging.info(f"  Log level: {config.log_level}")

    # Initialize monitor
    try:
        monitor = MoistureMonitor(config)
    except Exception as e:
        logging.critical(f"Failed to initialize monitor: {e}", exc_info=True)
        sys.exit(1)

    # Initialize graceful shutdown handler
    killer = GracefulKiller()

    logging.info("Monitoring started - press Ctrl+C to stop")

    try:
        # Main monitoring loop
        while killer.should_continue():
            try:
                monitor.monitor_cycle()
            except Exception as e:
                logging.error(f"Error during monitoring cycle: {e}", exc_info=True)
                # Continue running even if monitoring fails

            # Sleep with interruptible check for shutdown
            for _ in range(config.sampling_interval):
                if not killer.should_continue():
                    break
                time.sleep(1)

        logging.info("Shutdown requested, cleaning up...")
        logging.info("Plant monitoring daemon stopped gracefully")
        sys.exit(0)

    except Exception as e:
        logging.critical(f"Fatal error in main loop: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
