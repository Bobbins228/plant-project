# Deployment Guide: Plant Monitoring System

Complete step-by-step guide for deploying the plant monitoring system to a Raspberry Pi 4B.

## Prerequisites

- Raspberry Pi 4B with Raspberry Pi OS installed
- ADS1115 16-bit ADC module
- 3 capacitive soil moisture sensors
- Internet connection (WiFi or Ethernet)
- SSH access to Raspberry Pi (or keyboard/monitor)

## Hardware Assembly

### 1. Connect ADS1115 to Raspberry Pi

Connect the ADS1115 module to the Raspberry Pi's I2C pins:

| Raspberry Pi Pin | ADS1115 Pin | Description |
|------------------|-------------|-------------|
| Pin 1 (3.3V)     | VDD         | Power supply |
| Pin 3 (GPIO 2 / SDA) | SDA     | I2C data |
| Pin 5 (GPIO 3 / SCL) | SCL     | I2C clock |
| Pin 9 (GND)      | GND         | Ground |

**Important**: Use the Raspberry Pi's 3.3V pin, NOT 5V. The ADS1115 operates at 3.3V logic levels.

### 2. Connect Moisture Sensors to ADS1115

Each capacitive moisture sensor has 3 wires:

| Sensor Wire | Connect To |
|-------------|------------|
| VCC (Red)   | Raspberry Pi 3.3V or external 3.3V power |
| GND (Black) | Raspberry Pi GND or external GND |
| SIG (Yellow/Blue) | ADS1115 channel (A0, A1, or A2) |

**Sensor Mapping**:
- Plant-A → ADS1115 channel A0
- Plant-B → ADS1115 channel A1
- Plant-C → ADS1115 channel A2

**Power Consideration**: If using 3 sensors, consider using an external 3.3V power supply to avoid overloading the Raspberry Pi's 3.3V rail. Each sensor draws ~5-8mA.

### 3. Physical Installation

1. **Insert sensors into soil**: Push sensor probes vertically into soil near plant roots
2. **Keep electronics dry**: Position sensor circuit boards above soil surface
3. **Secure wiring**: Use cable ties or clips to prevent wire strain
4. **Label sensors**: Mark each sensor with plant name (A, B, C)

## Software Installation

### 1. System Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip (usually pre-installed)
sudo apt install -y python3 python3-pip git

# Install system dependencies
sudo apt install -y python3-venv i2c-tools
```

### 2. Enable I2C

```bash
# Enable I2C interface
sudo raspi-config
# Navigate: Interface Options → I2C → Yes → OK → Finish

# Reboot to apply changes
sudo reboot
```

After reboot, verify I2C is enabled:

```bash
# Check I2C kernel modules loaded
lsmod | grep i2c

# Should see output like:
# i2c_bcm2835

# Detect I2C devices (ADS1115 should appear at 0x48)
sudo i2cdetect -y 1

# Should see output like:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# ...
# 40:          -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
```

If `48` does not appear, check wiring and power connections.

### 3. Clone Repository

```bash
# Clone project to home directory
cd ~
git clone https://github.com/yourusername/plant-project.git
cd plant-project

# Checkout the feature branch (or main if merged)
git checkout 001-moisture-monitoring  # Or main
```

### 4. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Verify installation
python3 -c "from ADS1x15 import ADS1115; print('Success! ADS1115 library installed.')"
```

## Configuration

### 1. Create Configuration File

```bash
# Copy example configuration
cp config/monitor.env.example config/monitor.env

# Edit configuration
nano config/monitor.env
```

### 2. Configure ntfy.sh Topic

In `config/monitor.env`, set a unique topic name:

```bash
NTFY_TOPIC=your-unique-plant-topic-12345
```

**Important**: Choose a unique topic name to prevent conflicts with other users. Example: `plants-john-home-2026`.

### 3. Calibrate Sensors

Sensor calibration determines the voltage range for 0% (dry) and 100% (wet) moisture.

#### Dry Calibration

```bash
# Remove sensors from soil (leave in air)
# Run calibration script
python3 -m src.cli.monitor --calibrate-dry

# Output will show:
# === Dry Calibration (Sensors in Air) ===
# Channel 0 (Plant-A): 2.987V
# Channel 1 (Plant-B): 3.012V
# Channel 2 (Plant-C): 2.965V
#
# Average dry voltage: 2.99V
#
# Update config/monitor.env:
# MOISTURE_VOLTAGE_DRY=2.99
```

#### Wet Calibration

```bash
# Submerge sensor probes in distilled water (keep electronics dry!)
# Run calibration script
python3 -m src.cli.monitor --calibrate-wet

# Output will show:
# === Wet Calibration (Sensors in Water) ===
# Channel 0 (Plant-A): 1.587V
# Channel 1 (Plant-B): 1.612V
# Channel 2 (Plant-C): 1.598V
#
# Average wet voltage: 1.60V
#
# Update config/monitor.env:
# MOISTURE_VOLTAGE_WET=1.60
```

#### Update Configuration

Edit `config/monitor.env` with calibration values:

```bash
nano config/monitor.env

# Update these lines:
MOISTURE_VOLTAGE_DRY=2.99
MOISTURE_VOLTAGE_WET=1.60
```

### 4. Test Configuration

```bash
# Run in foreground to test
python3 -u src/cli/monitor.py

# You should see output like:
# ============================================================
# Plant Monitoring Daemon Starting
# ============================================================
# Configuration:
#   Moisture threshold: 40.0%
#   Sampling interval: 30s
#   Throttle duration: 21600s (6.0h)
#   ntfy.sh topic: your-topic
#   Log level: INFO
# Monitoring started - press Ctrl+C to stop
# Read 3 sensors: Plant-A: 55.2% (OK), Plant-B: 38.5% (DRY), Plant-C: 62.1% (OK)

# Press Ctrl+C to stop
```

## Subscribe to Notifications

### Mobile App

1. **Install ntfy app**:
   - Android: [Google Play Store](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - iOS: [App Store](https://apps.apple.com/us/app/ntfy/id1625396347)

2. **Subscribe to topic**:
   - Open ntfy app
   - Tap "+" to add subscription
   - Enter your topic name (same as `NTFY_TOPIC` in config)
   - Tap "Subscribe"

3. **Test notification**:
   ```bash
   # Send test notification
   curl -d "Test message from plant monitor" ntfy.sh/your-topic
   ```

   You should receive a notification on your phone.

## Install as System Service

### 1. Update Service File

Edit `config/plant-monitor.service` and update paths if necessary:

```bash
nano config/plant-monitor.service

# Verify paths match your installation:
# WorkingDirectory=/home/pi/plant-project
# ExecStart=/usr/bin/python3 -u /home/pi/plant-project/src/cli/monitor.py
# EnvironmentFile=-/home/pi/plant-project/config/monitor.env

# If using virtual environment, update ExecStart:
# ExecStart=/home/pi/plant-project/venv/bin/python3 -u /home/pi/plant-project/src/cli/monitor.py
```

### 2. Install Service

```bash
# Copy service file to systemd directory
sudo cp config/plant-monitor.service /etc/systemd/system/

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
     Loaded: loaded (/etc/systemd/system/plant-monitor.service; enabled; vendor preset: enabled)
     Active: active (running) since ...
   Main PID: 1234 (python3)
      Tasks: 1 (limit: 4915)
     Memory: 15.2M
        CPU: 1.234s
     CGroup: /system.slice/plant-monitor.service
             └─1234 /usr/bin/python3 -u /home/pi/plant-project/src/cli/monitor.py
```

### 3. View Logs

```bash
# View live logs
sudo journalctl -u plant-monitor.service -f

# View logs since boot
sudo journalctl -u plant-monitor.service -b

# View logs from last hour
sudo journalctl -u plant-monitor.service --since "1 hour ago"
```

## Maintenance

### Update Software

```bash
cd ~/plant-project

# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart plant-monitor.service
```

### Change Configuration

```bash
# Edit configuration
nano ~/plant-project/config/monitor.env

# Restart service to apply changes
sudo systemctl restart plant-monitor.service
```

### Re-calibrate Sensors

```bash
# Stop service
sudo systemctl stop plant-monitor.service

# Run calibration
python3 -m src.cli.monitor --calibrate-dry
python3 -m src.cli.monitor --calibrate-wet

# Update config/monitor.env with new values

# Restart service
sudo systemctl start plant-monitor.service
```

### Check Service Status

```bash
# Service status
sudo systemctl status plant-monitor.service

# View recent logs (last 50 lines)
sudo journalctl -u plant-monitor.service -n 50

# Check log file
tail -f /var/log/plant-monitor.log
```

## Troubleshooting

### Service Won't Start

1. Check configuration validity:
   ```bash
   python3 -c "from src.lib.config import MonitorConfig; print(MonitorConfig.load())"
   ```

2. Check Python dependencies:
   ```bash
   pip3 list | grep -E '(ADS1x15|requests|dotenv)'
   ```

3. Check I2C permissions:
   ```bash
   groups pi  # Should include 'i2c'
   sudo usermod -a -G i2c pi  # Add pi user to i2c group if missing
   ```

### No Notifications

1. Test ntfy.sh connectivity:
   ```bash
   curl -d "Test" ntfy.sh/your-topic
   ```

2. Check service logs for errors:
   ```bash
   sudo journalctl -u plant-monitor.service -n 100 | grep -i error
   ```

3. Verify internet connection:
   ```bash
   ping -c 3 ntfy.sh
   ```

### Invalid Sensor Readings

1. Check I2C connection:
   ```bash
   sudo i2cdetect -y 1  # Should show 48
   ```

2. Test sensor voltages:
   ```bash
   # Stop service
   sudo systemctl stop plant-monitor.service

   # Run calibration to see current voltages
   python3 -m src.cli.monitor --calibrate-dry
   ```

3. Check for loose wiring or corrosion on sensor probes

### High CPU Usage

Normal CPU usage should be <1%. If high:

1. Check sampling interval (increase if too frequent):
   ```bash
   # In config/monitor.env
   SAMPLING_INTERVAL=60  # Increase to 60 seconds
   ```

2. Check for rapid notification loops (should be throttled)

## Security Considerations

- **ntfy.sh topic**: Use a unique, hard-to-guess topic name (acts as password for public topics)
- **Network**: Consider running on isolated IoT network
- **Updates**: Regularly update system packages and Python dependencies
- **Logs**: Log files may contain sensor data; consider log rotation settings

## Performance Tuning

### Reduce Notification Frequency

```bash
# In config/monitor.env
THROTTLE_DURATION=43200  # 12 hours instead of 6
```

### Adjust Sampling Interval

```bash
# In config/monitor.env
SAMPLING_INTERVAL=120  # Check every 2 minutes instead of 30 seconds
```

### Change Moisture Threshold

```bash
# In config/monitor.env
MOISTURE_THRESHOLD=30.0  # Alert at 30% instead of 40%
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup config file
cp ~/plant-project/config/monitor.env ~/plant-monitor-backup.env

# Backup systemd service file
sudo cp /etc/systemd/system/plant-monitor.service ~/plant-monitor-service-backup
```

### Restore from Backup

```bash
# Restore config
cp ~/plant-monitor-backup.env ~/plant-project/config/monitor.env

# Restore service
sudo cp ~/plant-monitor-service-backup /etc/systemd/system/plant-monitor.service
sudo systemctl daemon-reload
sudo systemctl restart plant-monitor.service
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop plant-monitor.service
sudo systemctl disable plant-monitor.service

# Remove service file
sudo rm /etc/systemd/system/plant-monitor.service
sudo systemctl daemon-reload

# Remove project directory (optional)
rm -rf ~/plant-project
```

## Support

For additional help:
- Review [quickstart.md](specs/001-moisture-monitoring/quickstart.md)
- Check [troubleshooting section](README.md#troubleshooting) in README
- Review service logs: `sudo journalctl -u plant-monitor.service -n 100`
