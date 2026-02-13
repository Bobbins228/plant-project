# Research Findings: Moisture Monitoring and Notifications

**Feature**: 001-moisture-monitoring
**Date**: 2026-02-13
**Purpose**: Resolve technical unknowns for MVP implementation

## Research Questions Addressed

1. Which Python library for ADS1115 I2C communication?
2. How to calibrate capacitive sensors (voltage to percentage)?
3. How to use ntfy.sh HTTP API?
4. Best practices for Python daemon on Raspberry Pi?

---

## Decision 1: ADS1115 Python Library

###Decision: Use `adafruit-circuitpython-ads1x15`

**Rationale**:
- **Actively maintained** (last updated January 2026, weekly releases)
- **Official Adafruit library** with best documentation and community support
- **Cleanest API** with high-level `AnalogIn` abstraction
- **Raspberry Pi 4B compatible** (all Pi models supported)
- **Best for long-term** maintenance (part of CircuitPython ecosystem)

**Alternatives Considered**:
- **Adafruit_ADS1x15**: Deprecated/archived; not maintained since 2020
- **chandrawi/ADS1x15-ADC**: Smaller community, useful if continuous mode needed (not required for MVP)
- **Direct smbus2**: Too low-level; requires manual register manipulation

**Installation**:
```bash
pip3 install adafruit-circuitpython-ads1x15
```

**Code Example**:
```python
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create ADS1115 object (default address 0x48)
ads = ADS1115(i2c)

# Read from channel 0 (Plant-A)
channel0 = AnalogIn(ads, ADS1115.P0)
voltage = channel0.voltage  # Returns voltage (e.g., 2.85V)
raw_value = channel0.value  # Returns raw ADC count (0-32767)
```

**Gain Configuration**:
```python
import adafruit_ads1x15.ads1x15 as ADS
ads.gain = 1  # ±4.096V range (recommended for 0-3.3V sensors)
```

---

## Decision 2: Sensor Calibration Strategy

### Decision: Two-point linear calibration with shared formula

**Rationale**:
- **Adequate accuracy** for plant watering notifications (±5-10%)
- **Simple configuration** (two values: voltage_dry, voltage_wet)
- **Matches spec requirement** for shared calibration across all 3 sensors
- **Easy to recalibrate** (user-friendly procedure)

**Calibration Procedure**:

1. **Dry Calibration**:
   - Remove sensors from soil, leave in free air for 5 minutes
   - Record average voltage (typical: 2.85-3.15V)
   - Store as `MOISTURE_VOLTAGE_DRY` config value

2. **Wet Calibration**:
   - Immerse probe in distilled water (keep electronics dry!)
   - Wait 5 minutes for stabilization
   - Record average voltage (typical: 1.54-1.9V)
   - Store as `MOISTURE_VOLTAGE_WET` config value

**Conversion Formula (Linear)**:
```python
def voltage_to_moisture_percent(voltage, voltage_dry, voltage_wet):
    """Convert voltage to moisture percentage (0-100%)"""
    # Inverse relationship: higher voltage = drier soil
    percent = ((voltage_dry - voltage) / (voltage_dry - voltage_wet)) * 100.0

    # Clamp to valid range
    return max(0.0, min(100.0, percent))
```

**Example Configuration**:
```ini
# config/monitor.env
MOISTURE_VOLTAGE_DRY=3.0   # Typical value in air
MOISTURE_VOLTAGE_WET=1.6   # Typical value in water
MOISTURE_VALIDATION_MARGIN=5.0  # Allow ±5% for sensor variance
```

**Validation Logic**:
```python
# Accept readings in range [-5%, 105%] to handle sensor variance
# Reject readings clearly outside valid range (<-5% or >105%)
# Clamp reported values to [0%, 100%] for user display
```

**Alternatives Considered**:
- **Per-sensor calibration**: More accurate but violates spec requirement (shared calibration)
- **Polynomial calibration**: Higher accuracy (±2-5%) but unnecessary complexity for MVP
- **Auto-calibration**: Interesting for future enhancement but unreliable for MVP

**Recalibration Schedule**:
- Initial: Full calibration (dry + wet)
- Every 3 months: Validation test
- Every 6 months: Full recalibration
- After sensor replacement: Always recalibrate

---

## Decision 3: ntfy.sh HTTP API Implementation

### Decision: Use Python `requests` library with retry logic

**API Endpoint**:
```
POST https://ntfy.sh/{topic}
```

**Authentication**: None required for public topics (topic name acts as password)

**Message Format (Plain Text + Headers)**:
```python
import requests

response = requests.post(
    f"https://ntfy.sh/{topic}",
    data=message.encode('utf-8'),
    headers={
        'Title': 'Plant Alert',
        'Priority': '4',  # 1=min, 3=default, 5=urgent
        'Tags': 'droplet,warning'
    },
    timeout=10
)
```

**HTTP Status Codes**:
- **200 OK**: Success
- **400 Bad Request**: Invalid format (don't retry)
- **401 Unauthorized**: Auth failed (don't retry)
- **429 Too Many Requests**: Rate limited (retry with backoff)
- **500/503 Server Error**: Transient failure (retry)

**Rate Limits**:
- Burst: 60 requests
- Sustained: 1 request per 5 seconds
- No `Retry-After` header provided

**Retry Strategy**:
```python
def send_with_retry(url, data, max_retries=3):
    """Send notification with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                return {'success': True}
            elif response.status_code in [400, 401, 404]:
                # Permanent errors - don't retry
                return {'success': False, 'error': 'Permanent error'}
            elif response.status_code == 429:
                # Rate limited - wait longer
                wait = min(5 * (2 ** attempt), 60)  # 5s, 10s, 20s, max 60s
                time.sleep(wait)
            elif response.status_code >= 500:
                # Server error - exponential backoff
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)

        except (requests.Timeout, requests.ConnectionError):
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue

    return {'success': False, 'error': 'Max retries exceeded'}
```

**Priority Levels**:
- 1 = min (low priority)
- 3 = default (normal)
- 4 = high (our use case: plant needs watering)
- 5 = max/urgent (breaks through DND - reserve for critical failures)

**Notification Format** (from spec clarification):
```
Title: "Plant Alert"
Message: "Plant-A needs watering (moisture: 35%)"
Priority: 4 (high)
```

---

## Decision 4: Python Daemon Architecture

### Decision: Simple while loop with systemd (no python-daemon library)

**Rationale**:
- **Modern best practice** (2026): systemd handles daemon complexity
- **Simpler code**: No forking, PID files, or double-fork complexity
- **Better logging**: Direct integration with journald
- **Easier debugging**: Run script in foreground during development
- **More maintainable**: Standard Python, no special libraries

**Main Loop Structure**:
```python
#!/usr/bin/env python3
import signal
import sys
import time
import logging

class GracefulKiller:
    """Handle SIGTERM/SIGINT for graceful shutdown"""
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self.request_shutdown)
        signal.signal(signal.SIGTERM, self.request_shutdown)

    def request_shutdown(self, signum, frame):
        self.shutdown_requested = True

    def should_continue(self):
        return not self.shutdown_requested

def main():
    SLEEP_INTERVAL = 30  # seconds (configurable)

    killer = GracefulKiller()
    logger.info("Plant monitoring daemon starting...")

    while killer.should_continue():
        try:
            # Read sensors, check thresholds, send notifications
            monitor_plants()
        except Exception as e:
            logger.error(f"Monitoring error: {e}", exc_info=True)
            # Continue running even if cycle fails

        # Interruptible sleep (check shutdown every second)
        for _ in range(SLEEP_INTERVAL):
            if not killer.should_continue():
                break
            time.sleep(1)

    logger.info("Shutdown requested, cleaning up...")
    sys.exit(0)

if __name__ == '__main__':
    main()
```

**Systemd Service File** (`/etc/systemd/system/plant-monitor.service`):
```ini
[Unit]
Description=Plant Monitoring Daemon
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/plant-project

# Unbuffered output for immediate logging
ExecStart=/usr/bin/python3 -u /home/pi/plant-project/src/cli/monitor.py

# Auto-restart on failure
Restart=on-failure
RestartSec=5s

# Graceful shutdown
KillSignal=SIGTERM
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=plant-monitor

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Deployment Commands**:
```bash
sudo cp plant-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable plant-monitor.service
sudo systemctl start plant-monitor.service
sudo journalctl -u plant-monitor.service -f  # View logs
```

**Logging Configuration**:
```python
import logging
import logging.handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.handlers.SysLogHandler(address='/dev/log'),
        logging.handlers.RotatingFileHandler(
            '/var/log/plant-monitor.log',
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
    ]
)
```

**Key Features**:
- **Graceful shutdown**: Handle SIGTERM for clean exit (30 second timeout)
- **Interruptible sleep**: Check shutdown flag every second for responsive exit
- **Auto-restart**: systemd restarts on crash (indefinite retries)
- **Log rotation**: Prevent disk space issues (10MB max, 5 backups)
- **Security**: Run as `pi` user (not root), enable NoNewPrivileges

**Alternatives Considered**:
- **python-daemon library**: Obsolete with systemd; adds unnecessary complexity
- **supervisor**: Extra dependency; systemd is built-in and more powerful
- **cron jobs**: Not suitable for continuous monitoring (30-second intervals)

---

## Implementation Priorities

1. **Phase 0 Complete**: All research questions resolved
2. **Ready for Phase 1**: Data model and contracts design
3. **No blocking unknowns**: All NEEDS CLARIFICATION items addressed

## Next Steps

1. Create data-model.md (Plant, SensorReading, NotificationEvent entities)
2. Create contracts/ntfy-api.md (ntfy.sh HTTP API contract)
3. Create quickstart.md (usage guide and configuration examples)
4. Update agent context with Python 3.9+, adafruit-circuitpython-ads1x15, systemd
