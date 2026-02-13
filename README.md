# Plant Monitoring System

Automated soil moisture monitoring for Raspberry Pi 4B with push notifications via ntfy.sh.

## Overview

This system monitors up to 3 plants using capacitive soil moisture sensors connected via ADS1115 ADC, and sends mobile push notifications when plants need watering.

**Key Features**:
- 🌱 Monitor 3 plants independently
- 📱 Push notifications via ntfy.sh
- ⏱️ Configurable moisture thresholds
- 🔄 Automatic throttling (no spam)
- 🚀 Runs as systemd service

## Hardware Requirements

- Raspberry Pi 4B (Raspberry Pi OS)
- ADS1115 16-bit ADC module (I2C)
- 3x Capacitive soil moisture sensors
- Internet connection (for notifications)

## Quick Start

### 1. Install Dependencies

```bash
# Enable I2C on Raspberry Pi
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable

# Install Python dependencies
pip3 install -r requirements.txt
```

### 2. Configure

```bash
# Copy example configuration
cp config/monitor.env.example config/monitor.env

# Edit with your settings
nano config/monitor.env
# Set NTFY_TOPIC to a unique name
```

### 3. Calibrate Sensors

```bash
# Dry calibration (sensors in air)
python3 -m src.cli.monitor --calibrate-dry

# Wet calibration (sensors in water)
python3 -m src.cli.monitor --calibrate-wet

# Update config/monitor.env with calibration values
```

### 4. Subscribe to Notifications

- Install ntfy app on your phone ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/us/app/ntfy/id1625396347))
- Subscribe to your topic (same as NTFY_TOPIC in config)

### 5. Run

```bash
# Test run (foreground)
python3 -u src/cli/monitor.py

# Install as systemd service
sudo cp config/plant-monitor.service /etc/systemd/system/
sudo systemctl enable plant-monitor.service
sudo systemctl start plant-monitor.service
```

## Documentation

Full setup guide: [quickstart.md](specs/001-moisture-monitoring/quickstart.md)

Project documentation:
- [Feature Specification](specs/001-moisture-monitoring/spec.md)
- [Implementation Plan](specs/001-moisture-monitoring/plan.md)
- [Data Model](specs/001-moisture-monitoring/data-model.md)
- [API Contracts](specs/001-moisture-monitoring/contracts/ntfy-api.md)

## Project Structure

```
plant-project/
├── src/
│   ├── lib/           # Core monitoring library
│   ├── cli/           # CLI entry point
│   └── models/        # Data models
├── tests/
│   ├── contract/      # External API tests
│   ├── integration/   # Cross-component tests
│   └── unit/          # Component tests
├── config/            # Configuration files
└── specs/             # Design documentation
```

## Configuration Reference

Edit `config/monitor.env` to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOISTURE_THRESHOLD` | `40.0` | Moisture percentage below which to send alerts (0-100%) |
| `MOISTURE_VOLTAGE_DRY` | `3.0` | Calibrated voltage for dry sensor (in air) |
| `MOISTURE_VOLTAGE_WET` | `1.6` | Calibrated voltage for wet sensor (in water) |
| `SAMPLING_INTERVAL` | `60` | Seconds between monitoring cycles |
| `THROTTLE_DURATION` | `21600` | Seconds between repeated notifications (6 hours) |
| `NTFY_TOPIC` | `plant-monitor` | ntfy.sh topic name (use unique value) |
| `NTFY_URL` | `https://ntfy.sh` | ntfy.sh server URL |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG` or `INFO`) |
| `ADS1115_ADDRESS` | `0x48` | I2C address of ADS1115 (hex) |
| `ADS1115_GAIN` | `1` | ADC gain setting (1 = ±4.096V range) |

## Hardware Wiring

Connect ADS1115 to Raspberry Pi via I2C:

```
Raspberry Pi 4B          ADS1115
─────────────────        ───────
Pin 1  (3.3V)     ────→  VDD
Pin 3  (SDA)      ────→  SDA
Pin 5  (SCL)      ────→  SCL
Pin 9  (GND)      ────→  GND

ADS1115 Channels         Moisture Sensors
────────────────         ────────────────
A0                ────→  Plant-A
A1                ────→  Plant-B
A2                ────→  Plant-C
```

**Sensor Connections**: Each capacitive sensor has 3 wires (VCC, GND, SIG). Connect SIG wire to ADS1115 channel, VCC to 3.3V, GND to ground.

## Monitoring & Logs

View service status and logs:

```bash
# Check service status
sudo systemctl status plant-monitor.service

# View live logs
sudo journalctl -u plant-monitor.service -f

# View logs since boot
sudo journalctl -u plant-monitor.service -b

# View logs from specific time
sudo journalctl -u plant-monitor.service --since "1 hour ago"
```

Log files are also written to `/var/log/plant-monitor.log` (rotated at 10MB, 5 backups).

## Troubleshooting

### No notifications received

1. Check ntfy.sh subscription:
   - Open ntfy app on phone
   - Verify topic name matches `NTFY_TOPIC` in config
   - Test with: `curl -d "Test message" ntfy.sh/YOUR_TOPIC`

2. Check service logs:
   ```bash
   sudo journalctl -u plant-monitor.service -n 50
   ```

3. Verify internet connectivity:
   ```bash
   ping -c 3 ntfy.sh
   ```

### Invalid sensor readings

1. Check sensor connections:
   - Verify I2C wiring (SDA, SCL, VDD, GND)
   - Test I2C detection: `sudo i2cdetect -y 1` (should show `48`)

2. Re-calibrate sensors:
   ```bash
   python3 -m src.cli.monitor --calibrate-dry
   python3 -m src.cli.monitor --calibrate-wet
   ```

3. Check voltage range:
   - Expected dry voltage: 2.8-3.2V
   - Expected wet voltage: 1.4-1.8V
   - If outside range, sensor may be damaged

### Service won't start

1. Check Python dependencies:
   ```bash
   pip3 list | grep -E '(adafruit|requests|dotenv)'
   ```

2. Verify I2C enabled:
   ```bash
   lsmod | grep i2c
   sudo raspi-config  # Interface Options → I2C
   ```

3. Check configuration file exists:
   ```bash
   ls -l config/monitor.env
   ```

## Development

This project follows Test-Driven Development (TDD):
- Tests written FIRST before implementation
- All tests must pass before merge
- Run tests: `pytest -v`
- See [tasks.md](specs/001-moisture-monitoring/tasks.md) for implementation roadmap

**Development on Mac/Linux (no hardware)**:
- Tests use mocked sensor interfaces
- Import errors for I2C libraries are handled gracefully
- Full development environment without Raspberry Pi

## License

MIT License - see LICENSE file for details

## Support

For issues and questions, see the [quickstart troubleshooting guide](specs/001-moisture-monitoring/quickstart.md#troubleshooting).
