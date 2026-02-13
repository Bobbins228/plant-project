# Quick Reference: Plant Monitoring System

Quick command reference for common operations.

## Service Management

```bash
# Start service
sudo systemctl start plant-monitor.service

# Stop service
sudo systemctl stop plant-monitor.service

# Restart service (after config changes)
sudo systemctl restart plant-monitor.service

# Check status
sudo systemctl status plant-monitor.service

# Enable auto-start on boot
sudo systemctl enable plant-monitor.service

# Disable auto-start
sudo systemctl disable plant-monitor.service
```

## View Logs

```bash
# Live logs (follow mode)
sudo journalctl -u plant-monitor.service -f

# Last 50 lines
sudo journalctl -u plant-monitor.service -n 50

# Logs since boot
sudo journalctl -u plant-monitor.service -b

# Logs from last hour
sudo journalctl -u plant-monitor.service --since "1 hour ago"

# Logs from specific date
sudo journalctl -u plant-monitor.service --since "2026-02-01"

# View log file directly
tail -f /var/log/plant-monitor.log
```

## Configuration

```bash
# Edit configuration
nano ~/plant-project/config/monitor.env

# After editing, restart service
sudo systemctl restart plant-monitor.service

# Verify configuration (without starting service)
python3 -c "from src.lib.config import MonitorConfig; print(MonitorConfig.load())"
```

## Common Configuration Values

| Setting | Default | Description |
|---------|---------|-------------|
| `MOISTURE_THRESHOLD` | `40.0` | Alert when below this % |
| `SAMPLING_INTERVAL` | `30` | Seconds between checks |
| `THROTTLE_DURATION` | `21600` | Seconds between alerts (6 hrs) |
| `LOG_LEVEL` | `INFO` | `DEBUG` or `INFO` |

## Sensor Calibration

```bash
# Stop service before calibrating
sudo systemctl stop plant-monitor.service

# Dry calibration (sensors in air)
python3 -m src.cli.monitor --calibrate-dry

# Wet calibration (sensors in water)
python3 -m src.cli.monitor --calibrate-wet

# Update config with values from calibration output
nano ~/plant-project/config/monitor.env

# Restart service
sudo systemctl start plant-monitor.service
```

## Testing

```bash
# Run in foreground (test mode)
python3 -u ~/plant-project/src/cli/monitor.py

# Test notification manually
curl -d "Test message" ntfy.sh/YOUR_TOPIC

# Check I2C detection
sudo i2cdetect -y 1  # Should show 48

# Run unit tests
cd ~/plant-project
pytest -v

# Run specific test file
pytest tests/integration/test_single_plant_alert.py -v
```

## Troubleshooting

```bash
# Check service errors
sudo journalctl -u plant-monitor.service -n 100 | grep -i error

# Check Python dependencies
pip3 list | grep -E '(ADS1x15|requests|dotenv|pytest)'

# Verify I2C enabled
lsmod | grep i2c

# Test network connectivity
ping -c 3 ntfy.sh

# Check configuration file exists
ls -l ~/plant-project/config/monitor.env

# View current moisture readings (from logs)
sudo journalctl -u plant-monitor.service -n 20 | grep "Read"
```

## Hardware Diagnostics

```bash
# Check I2C devices
sudo i2cdetect -y 1

# Expected output shows 48:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 40:          -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --

# Check I2C kernel modules
lsmod | grep i2c_bcm2835

# Enable I2C if not detected
sudo raspi-config  # Interface Options → I2C → Yes

# Check Raspberry Pi GPIO info
pinout
```

## Update Software

```bash
# Pull latest code
cd ~/plant-project
git pull origin main

# Update dependencies
pip3 install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart plant-monitor.service
```

## Backup & Restore

```bash
# Backup configuration
cp ~/plant-project/config/monitor.env ~/monitor-backup-$(date +%Y%m%d).env

# Restore configuration
cp ~/monitor-backup-20260213.env ~/plant-project/config/monitor.env
sudo systemctl restart plant-monitor.service
```

## Performance Monitoring

```bash
# Check service resource usage
systemctl status plant-monitor.service | grep -E '(Memory|CPU)'

# Check disk space
df -h /var/log

# Check log file size
ls -lh /var/log/plant-monitor.log

# Rotate logs manually (if needed)
sudo journalctl --vacuum-size=100M
```

## Emergency Commands

```bash
# Stop service immediately
sudo systemctl stop plant-monitor.service

# Disable service (won't start on boot)
sudo systemctl disable plant-monitor.service

# Remove service entirely
sudo systemctl stop plant-monitor.service
sudo systemctl disable plant-monitor.service
sudo rm /etc/systemd/system/plant-monitor.service
sudo systemctl daemon-reload

# Clear all logs
sudo journalctl --vacuum-time=1s
```

## Monitoring Dashboard (Manual)

Create a simple monitoring script:

```bash
#!/bin/bash
# monitor-status.sh - Quick status dashboard

echo "=== Plant Monitor Status ==="
echo

echo "Service Status:"
sudo systemctl is-active plant-monitor.service
echo

echo "Last 5 Readings:"
sudo journalctl -u plant-monitor.service -n 100 | grep "Read" | tail -5
echo

echo "Recent Notifications:"
sudo journalctl -u plant-monitor.service -n 100 | grep "Notification sent" | tail -5
echo

echo "Recent Errors:"
sudo journalctl -u plant-monitor.service -n 100 | grep -i error | tail -5
echo

echo "Resource Usage:"
systemctl status plant-monitor.service | grep -E '(Memory|CPU)'
```

Save to `~/monitor-status.sh`, make executable, and run:

```bash
chmod +x ~/monitor-status.sh
./monitor-status.sh
```

## Configuration Presets

### Low Frequency (Battery Saver)
```bash
SAMPLING_INTERVAL=300       # Check every 5 minutes
THROTTLE_DURATION=43200     # Alert every 12 hours
```

### High Sensitivity
```bash
MOISTURE_THRESHOLD=50.0     # Alert at 50% instead of 40%
THROTTLE_DURATION=10800     # Alert every 3 hours
```

### Debug Mode
```bash
LOG_LEVEL=DEBUG             # Verbose logging
SAMPLING_INTERVAL=10        # Check every 10 seconds
```

### Production (Recommended)
```bash
MOISTURE_THRESHOLD=40.0
SAMPLING_INTERVAL=30
THROTTLE_DURATION=21600     # 6 hours
LOG_LEVEL=INFO
```

## Help Resources

- Full documentation: [README.md](README.md)
- Deployment guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Feature specification: [specs/001-moisture-monitoring/spec.md](specs/001-moisture-monitoring/spec.md)
- Troubleshooting: [README.md#troubleshooting](README.md#troubleshooting)
- Quick start: [specs/001-moisture-monitoring/quickstart.md](specs/001-moisture-monitoring/quickstart.md)
