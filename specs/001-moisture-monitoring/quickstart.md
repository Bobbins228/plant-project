# Quickstart Guide: Plant Moisture Monitoring

**Feature**: 001-moisture-monitoring
**Audience**: Raspberry Pi users setting up plant monitoring system
**Prerequisites**: Raspberry Pi 4B with Raspberry Pi OS, hardware sensors connected

## Overview

This guide walks you through setting up and running the MVP plant moisture monitoring system. By the end, you'll have a system that:
- Monitors 3 plants continuously
- Sends notifications to your phone when plants need watering
- Runs automatically on boot

**Estimated Setup Time**: 30-45 minutes

---

## Hardware Setup

### Required Components

- **Raspberry Pi 4B** with Raspberry Pi OS installed
- **ADS1115** 16-bit ADC module (I2C address 0x48)
- **3x Capacitive Soil Moisture Sensors**
- Jumper wires for connections
- Internet connection (for ntfy.sh notifications)

### Wiring Diagram

```
Raspberry Pi 4B GPIO Pins:
┌────────────────────────────────┐
│ Pin 1  (3.3V)  ───────┐        │
│ Pin 3  (SDA)   ───────┼───┐    │
│ Pin 5  (SCL)   ───────┼───┼──┐ │
│ Pin 9  (GND)   ───────┘   │  │ │
└────────────────────────────┼──┼─┘
                             │  │
                             ▼  ▼
           ADS1115 Module  SDA SCL
           ┌─────────────────────┐
           │ VDD ← 3.3V          │
           │ GND ← GND           │
           │ SCL ← GPIO 5 (SCL)  │
           │ SDA ← GPIO 3 (SDA)  │
           │ ADDR → GND (0x48)   │
           │                     │
           │ A0 ← Sensor 1 (Plant-A)
           │ A1 ← Sensor 2 (Plant-B)
           │ A2 ← Sensor 3 (Plant-C)
           │ A3 ← (unused)       │
           └─────────────────────┘
                 │    │    │
                 ▼    ▼    ▼
            Sensor Sensor Sensor
               1      2      3
         (Plant-A)(Plant-B)(Plant-C)
```

**Connection Steps**:
1. Connect ADS1115 to Raspberry Pi I2C pins:
   - ADS1115 VDD → Pi Pin 1 (3.3V)
   - ADS1115 GND → Pi Pin 9 (GND)
   - ADS1115 SCL → Pi Pin 5 (GPIO 3 / SCL)
   - ADS1115 SDA → Pi Pin 3 (GPIO 2 / SDA)
   - ADS1115 ADDR → GND (sets I2C address to 0x48)

2. Connect moisture sensors to ADS1115:
   - Sensor 1 signal wire → ADS1115 A0 (Plant-A)
   - Sensor 2 signal wire → ADS1115 A1 (Plant-B)
   - Sensor 3 signal wire → ADS1115 A2 (Plant-C)
   - All sensors: VCC → 3.3V, GND → GND

3. Insert sensors into plant soil (probe only, keep electronics dry)

### Enable I2C on Raspberry Pi

```bash
# Enable I2C interface
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable

# Verify I2C is enabled
lsmod | grep i2c
# Should show: i2c_dev, i2c_bcm2835

# Install I2C tools
sudo apt-get update
sudo apt-get install -y i2c-tools python3-smbus

# Detect ADS1115 (should show 0x48)
sudo i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

---

## Software Installation

### Step 1: Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/plant-project.git
cd plant-project
```

### Step 2: Install Python Dependencies

```bash
# Install pip if not already installed
sudo apt-get install -y python3-pip

# Install project dependencies
pip3 install -r requirements.txt
```

**requirements.txt** contents:
```
adafruit-circuitpython-ads1x15==2.2.23
requests==2.31.0
python-dotenv==1.0.0
```

### Step 3: Verify Installation

```bash
# Test ADS1115 connection
python3 -c "
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
print('ADS1115 detected successfully!')
"
```

---

## Configuration

### Step 1: Create Configuration File

```bash
# Copy example configuration
cp config/monitor.env.example config/monitor.env

# Edit configuration
nano config/monitor.env
```

### Step 2: Configure Settings

**config/monitor.env**:
```ini
# Moisture Monitoring Configuration

# Notification Settings
NTFY_TOPIC=your-unique-topic-name-12345
NTFY_URL=https://ntfy.sh

# Moisture Thresholds
MOISTURE_THRESHOLD=40.0  # Alert when below 40%

# Sensor Calibration (default values - calibrate for accuracy)
MOISTURE_VOLTAGE_DRY=3.0  # Voltage in air (0% moisture)
MOISTURE_VOLTAGE_WET=1.6  # Voltage in water (100% moisture)

# Monitoring Behavior
SAMPLING_INTERVAL=30  # Seconds between readings
THROTTLE_DURATION=21600  # 6 hours between notifications (21600 seconds)

# Logging
LOG_LEVEL=INFO  # INFO or DEBUG

# Hardware Settings (usually don't need to change)
ADS1115_ADDRESS=0x48
ADS1115_GAIN=1
```

**Important**: Replace `your-unique-topic-name-12345` with a unique, hard-to-guess name (this is your notification "password")

### Step 3: Subscribe to Notifications on Your Phone

1. **Install ntfy app**:
   - Android: [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - iOS: [App Store](https://apps.apple.com/us/app/ntfy/id1625396347)
   - Web: https://ntfy.sh/app

2. **Subscribe to your topic**:
   - Open ntfy app
   - Tap "+" to add subscription
   - Enter your topic name (same as `NTFY_TOPIC` in config)
   - Tap "Subscribe"

3. **Test notification**:
   ```bash
   curl -d "Test notification - system working!" https://ntfy.sh/your-unique-topic-name-12345
   ```
   You should receive a push notification on your phone!

---

## Sensor Calibration

For accurate moisture readings, calibrate your sensors:

### Dry Calibration (Air)

```bash
# Remove all sensors from soil and wait 5 minutes
# Run calibration script
python3 -m src.cli.monitor --calibrate-dry

# Output example:
# Sensor A0 (Plant-A): 3.05V
# Sensor A1 (Plant-B): 2.98V
# Sensor A2 (Plant-C): 3.12V
# Average dry voltage: 3.05V
#
# Update config/monitor.env:
# MOISTURE_VOLTAGE_DRY=3.05
```

### Wet Calibration (Water)

```bash
# Submerge sensor probes in water (electronics must stay dry!)
# Wait 5 minutes for stabilization
python3 -m src.cli.monitor --calibrate-wet

# Output example:
# Sensor A0 (Plant-A): 1.62V
# Sensor A1 (Plant-B): 1.58V
# Sensor A2 (Plant-C): 1.65V
# Average wet voltage: 1.62V
#
# Update config/monitor.env:
# MOISTURE_VOLTAGE_WET=1.62
```

### Update Configuration

```bash
nano config/monitor.env
# Update MOISTURE_VOLTAGE_DRY and MOISTURE_VOLTAGE_WET with calibrated values
```

---

## Running the Monitor

### Test Run (Foreground)

```bash
# Run in foreground to see live output
python3 -u src/cli/monitor.py

# Expected output:
# 2026-02-13 10:30:15 - plant-monitor - INFO - Plant monitoring daemon starting...
# 2026-02-13 10:30:15 - plant-monitor - INFO - Plant-A: 52% (OK)
# 2026-02-13 10:30:15 - plant-monitor - INFO - Plant-B: 38% (DRY - sending notification)
# 2026-02-13 10:30:16 - plant-monitor - INFO - Notification sent: Plant-B needs watering (moisture: 38%)
# 2026-02-13 10:30:16 - plant-monitor - INFO - Plant-C: 45% (OK)
```

**Press Ctrl+C to stop**

### Debug Mode

```bash
# Enable DEBUG logging for detailed sensor readings
LOG_LEVEL=DEBUG python3 -u src/cli/monitor.py

# Output includes:
# - Raw ADC values
# - Voltage readings
# - Conversion calculations
# - Throttle timer checks
```

---

## Install as System Service

For production use, run as a systemd service that auto-starts on boot:

### Step 1: Create Service File

```bash
sudo nano /etc/systemd/system/plant-monitor.service
```

**Contents**:
```ini
[Unit]
Description=Plant Moisture Monitoring Daemon
Documentation=https://github.com/yourusername/plant-project
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/plant-project

# Unbuffered Python output for immediate logging
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

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable plant-monitor.service

# Start service now
sudo systemctl start plant-monitor.service

# Check status
sudo systemctl status plant-monitor.service
```

Expected output:
```
● plant-monitor.service - Plant Moisture Monitoring Daemon
   Loaded: loaded (/etc/systemd/system/plant-monitor.service; enabled)
   Active: active (running) since Thu 2026-02-13 10:35:22 GMT; 5s ago
 Main PID: 12345 (python3)
   Status: "Monitoring 3 plants..."
   CGroup: /system.slice/plant-monitor.service
           └─12345 /usr/bin/python3 -u /home/pi/plant-project/src/cli/monitor.py
```

### Step 3: View Logs

```bash
# View live logs
sudo journalctl -u plant-monitor.service -f

# View last 100 lines
sudo journalctl -u plant-monitor.service -n 100

# View logs from today
sudo journalctl -u plant-monitor.service --since today
```

### Service Management Commands

```bash
# Stop service
sudo systemctl stop plant-monitor.service

# Restart service
sudo systemctl restart plant-monitor.service

# Disable auto-start on boot
sudo systemctl disable plant-monitor.service

# Re-enable auto-start
sudo systemctl enable plant-monitor.service
```

---

## Usage Examples

### Scenario 1: Normal Operation

All plants have adequate moisture:
```
2026-02-13 10:00:00 - plant-monitor - INFO - Plant-A: 55% (OK)
2026-02-13 10:00:00 - plant-monitor - INFO - Plant-B: 48% (OK)
2026-02-13 10:00:00 - plant-monitor - INFO - Plant-C: 62% (OK)
(Waits 30 seconds)
2026-02-13 10:00:30 - plant-monitor - INFO - Plant-A: 54% (OK)
...
```

**Action**: None required. System monitors silently.

### Scenario 2: Plant Needs Watering

Plant-B moisture drops below 40%:
```
2026-02-13 10:15:00 - plant-monitor - INFO - Plant-B: 38% (DRY - sending notification)
2026-02-13 10:15:01 - plant-monitor - INFO - Notification sent: Plant-B needs watering (moisture: 38%)
```

**Phone Notification**:
```
🔔 Plant Alert
Plant-B needs watering (moisture: 38%)
```

**Action**: Water Plant-B

### Scenario 3: After Watering

User waters Plant-B, moisture rises above 45% (threshold + 5% buffer):
```
2026-02-13 10:30:00 - plant-monitor - INFO - Plant-B: 48% (OK - throttle reset)
```

**Result**: Throttle timer reset. If Plant-B dries out again, immediate notification sent.

### Scenario 4: Throttle Active

Plant-B still dry, but notification sent <6 hours ago:
```
2026-02-13 11:00:00 - plant-monitor - INFO - Plant-B: 37% (DRY - throttled, last notified 45min ago)
```

**Result**: No duplicate notification. Next alert eligible at 4:15 PM (6 hours after first notification).

---

## Troubleshooting

### Sensors Not Detected

**Error**: `OSError: [Errno 121] Remote I/O error`

**Solution**:
```bash
# Check I2C is enabled
sudo raspi-config  # Interface Options → I2C → Enable

# Verify ADS1115 address
sudo i2cdetect -y 1

# Check wiring (especially SDA/SCL connections)
```

### Invalid Moisture Readings

**Symptom**: Log shows "Invalid sensor reading: 120% (voltage: 1.2V)"

**Causes**:
1. Incorrect calibration values
2. Loose sensor connections
3. Sensor malfunction

**Solution**:
```bash
# Re-calibrate sensors
python3 -m src.cli.monitor --calibrate-dry
python3 -m src.cli.monitor --calibrate-wet

# Test sensor directly
python3 -c "
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import ADS1115
import board, busio

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)
ch0 = AnalogIn(ads, ADS1115.P0)
print(f'Channel 0 voltage: {ch0.voltage}V')
"
```

### Notifications Not Received

**Symptom**: Log shows "Notification sent" but phone doesn't receive alert

**Solution**:
1. **Check ntfy app subscription**:
   - Open ntfy app
   - Verify topic name matches config exactly
   - Check subscription is active

2. **Test ntfy.sh directly**:
   ```bash
   curl -d "Test" https://ntfy.sh/your-unique-topic-name-12345
   ```

3. **Check network connectivity**:
   ```bash
   ping -c 3 ntfy.sh
   ```

4. **Review logs for errors**:
   ```bash
   sudo journalctl -u plant-monitor.service | grep ERROR
   ```

### Service Won't Start

**Error**: `Failed to start plant-monitor.service: Unit not found`

**Solution**:
```bash
# Check service file exists
ls -l /etc/systemd/system/plant-monitor.service

# Reload systemd
sudo systemctl daemon-reload

# Check for syntax errors
sudo systemctl status plant-monitor.service
```

---

## Next Steps

- **Adjust thresholds**: Fine-tune `MOISTURE_THRESHOLD` per plant type (succulents: 20%, ferns: 50%)
- **Monitor trends**: Track moisture levels over time to understand plant water consumption
- **Add more sensors**: Future: connect BME688 environmental sensor for temperature/humidity
- **Web UI**: Future: view live data and configure settings via web interface

---

## Support

- **Documentation**: `/docs` directory
- **Configuration**: `/config/monitor.env.example`
- **Logs**: `sudo journalctl -u plant-monitor.service`
- **Issues**: https://github.com/yourusername/plant-project/issues
