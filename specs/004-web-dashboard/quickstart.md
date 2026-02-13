# Quickstart: Local Web Dashboard for Plant Monitoring

**Feature**: 004-web-dashboard
**Date**: 2026-02-13
**Audience**: Users setting up the web dashboard to monitor plants via browser

## Overview

This guide shows you how to set up and use the local web dashboard to monitor your plants, view environmental data graphs, and manage plant profiles through a browser interface.

## Prerequisites

- Plant monitoring system installed and working (features 001-003)
- Raspberry Pi with Python 3.9+ and monitoring system running
- Local network access to Raspberry Pi
- Browser on desktop, tablet, or mobile device

## Installation

### 1. Install Dashboard Dependencies

```bash
# Install Flask, Gunicorn, and Pillow for image handling
uv pip install flask gunicorn pillow

# Or using pip
pip install flask gunicorn pillow
```

### 2. Verify Installation

```bash
python3 -c "import flask, gunicorn, PIL; print('Dashboard dependencies installed successfully')"
```

### 3. Run Database Migration

The dashboard requires schema updates to add image support and environmental data storage:

```bash
# Run migration script (creates environmental_readings table and adds image_path column)
uv run python3 src/cli/migrate_dashboard.py

# Or using python directly
python3 src/cli/migrate_dashboard.py
```

Expected output:
```
Database migration complete:
✓ Added image_path column to plant_profiles
✓ Created environmental_readings table
✓ Created images directory: data/images/
```

## Quick Start

### Step 1: Start the Dashboard Server

```bash
# Development mode (with auto-reload)
uv run python3 src/cli/dashboard.py

# Production mode (with Gunicorn)
uv run gunicorn -w 2 -b 0.0.0.0:5000 src.lib.web_server:app
```

Expected output:
```
* Running on http://0.0.0.0:5000
* Serving Flask app 'web_server'
* Press CTRL+C to quit
```

### Step 2: Access the Dashboard

Open your browser and navigate to:

**From the Raspberry Pi itself**:
- `http://localhost:5000`

**From another device on your local network**:
- `http://192.168.1.100:5000` (replace with your Pi's IP address)
- Find Pi IP: `hostname -I` or check your router

### Step 3: View Live Plant Status

The main dashboard displays:
- **Plant cards**: Name, current moisture %, sensor channel, threshold
- **Status indicators**: Green (OK), Red (Needs watering), Gray (No data)
- **Environmental panel**: Temperature, humidity, pressure, gas resistance
- **Last updated**: Timestamp of last monitoring cycle

The dashboard automatically refreshes every 5 seconds to show new readings.

### Step 4: View Environmental History Graph

Click "Environmental History" to see:
- Time-series graph of last 60 minutes
- All 4 metrics (temperature, humidity, pressure, gas) on same timeline
- Hover/tap data points to see exact values and timestamps

If less than 1 hour of data collected, graph shows available data.

## Common Operations

### Add a New Plant

1. Click **"Add Plant"** button on dashboard
2. Fill in the form:
   - **Plant Name**: Unique name (e.g., "Money Plant")
   - **Sensor Channel**: 0-3 (must not be in use by another plant)
   - **Moisture Threshold**: % below which plant needs watering (e.g., 35)
3. Click **"Save"**
4. New plant appears on dashboard with "No data" until next monitoring cycle

**Validation**:
- Name must be unique
- Channel 0-3 must not be assigned to another plant
- Threshold must be 0-100%

### Edit Plant Profile

1. Click **"Edit"** on a plant card
2. Update name, channel, or threshold
3. Click **"Save"**
4. Changes take effect on next monitoring cycle

### Upload Plant Image

1. Click **"Edit"** on a plant card
2. Click **"Upload Image"** and select photo from your device
3. Preview appears before saving
4. Click **"Save"** to confirm
5. Image appears on plant card immediately

**Accepted formats**: JPEG, PNG, GIF, WebP
**Maximum size**: 10 MB

### Remove Plant Image

1. Click **"Edit"** on a plant card
2. Click **"Remove Image"**
3. Plant card shows default placeholder

### Delete Plant

1. Click **"Edit"** on a plant card
2. Click **"Delete Plant"**
3. Confirm deletion when prompted
4. Plant and associated image are permanently removed

**Note**: Cannot delete the last plant - at least one plant is required.

## Scenarios

### Scenario 1: Check Plant Status from Mobile

**Use case**: Check if plants need watering while away from computer

1. Open browser on mobile phone
2. Navigate to `http://192.168.1.100:5000` (your Pi's IP)
3. View plant cards - red cards need watering
4. Tap plant to see detailed moisture percentage

**Mobile-friendly**: Dashboard is responsive, no horizontal scrolling needed.

### Scenario 2: Identify Environmental Trends

**Use case**: Understand why plant moisture drops faster on some days

1. Open dashboard on desktop/tablet
2. Click **"Environmental History"**
3. Observe temperature and humidity spikes
4. Correlate high temperature/low humidity with faster moisture loss

**Example observations**:
- Temperature spike 18-20°C → 28°C correlates with moisture drop 45% → 30%
- Humidity drop 60% → 30% when heater turns on explains faster drying

### Scenario 3: Add Plant with Custom Photo

**Use case**: New plant added to monitoring system with personalized image

1. Take photo of plant with your phone
2. Open dashboard in browser
3. Click **"Add Plant"**, fill in "Philodendron", channel 3, threshold 40%
4. Click **"Upload Image"**, select photo
5. Click **"Save"**
6. Dashboard shows plant card with custom image

### Scenario 4: Dashboard When Monitoring System Stopped

**Use case**: Dashboard accessed while monitoring daemon is not running

**Expected behavior**:
- Dashboard still loads and displays last known plant statuses
- Environmental graph shows historical data up to when monitoring stopped
- "Last updated" timestamp shows when monitoring last ran
- Warning message: "Monitoring system appears stopped (no updates in X minutes)"

**Resolution**: Start monitoring daemon with `sudo systemctl start plant-monitor`

### Scenario 5: Environmental Sensor Disconnected

**Use case**: BME688 sensor unplugged while dashboard is open

**Expected behavior**:
- Plant moisture data continues updating normally
- Environmental panel shows "Sensor Unavailable"
- Environmental graph displays last readings before disconnection
- No error prevents dashboard from functioning

**Resolution**: Reconnect environmental sensor, verify with `i2cdetect -y 1`

## Troubleshooting

### Dashboard Won't Start

**Symptom**: `ModuleNotFoundError: No module named 'flask'`

**Solution**:
```bash
# Install dependencies
uv pip install flask gunicorn pillow

# Verify installation
python3 -c "import flask; print('Flask installed')"
```

---

**Symptom**: `Address already in use: 0.0.0.0:5000`

**Solution**:
```bash
# Check what's using port 5000
sudo lsof -i :5000

# Kill existing process or use different port
uv run python3 src/cli/dashboard.py --port 5001
```

### Dashboard Not Accessible from Other Devices

**Symptom**: Browser on phone/tablet can't reach `http://192.168.1.100:5000`

**Solution**:
1. Verify Raspberry Pi IP: `hostname -I`
2. Ensure dashboard bound to `0.0.0.0`, not `127.0.0.1`
3. Check firewall: `sudo ufw allow 5000` (if using ufw)
4. Verify devices on same network (not guest Wi-Fi)

### Plant Changes Not Appearing

**Symptom**: Created new plant but doesn't show on dashboard

**Solution**:
1. Check monitoring system is running: `systemctl status plant-monitor`
2. Wait for next monitoring cycle (1-2 minutes)
3. Check logs: `journalctl -u plant-monitor -f`
4. Verify database updated: `sqlite3 data/plants.db "SELECT * FROM plant_profiles;"`

### Image Upload Fails

**Symptom**: Error message "Invalid file format" or "File too large"

**Solution**:
1. **File format**: Convert to JPEG/PNG/GIF/WebP
2. **File size**: Resize image to <10 MB using photo editor
3. **Permissions**: Ensure `data/images/` directory writable: `chmod 755 data/images/`

---

**Symptom**: Image uploaded but not displaying on card

**Solution**:
1. Check file exists: `ls -lh data/images/`
2. Verify database reference: `sqlite3 data/plants.db "SELECT id, plant_name, image_path FROM plant_profiles;"`
3. Check image path correct: Should be `plant_{id}.jpg`, not full path
4. Hard refresh browser: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)

### Environmental Graph Empty

**Symptom**: Environmental history graph shows "No data available"

**Solution**:
1. Verify environmental sensor connected: `i2cdetect -y 1` (should show 0x76 or 0x77)
2. Check monitoring system persisting data: `sqlite3 data/plants.db "SELECT COUNT(*) FROM environmental_readings;"`
3. Wait for data collection (monitoring system writes every 1-2 minutes)
4. Verify environmental monitoring enabled (feature 003-bme688-environmental)

### Dashboard Updates Slowly

**Symptom**: New readings take >10 seconds to appear on dashboard

**Expected behavior**: 5-second polling means updates appear within 5-10 seconds

**If slower**:
1. Check network latency between device and Pi
2. Reduce polling interval (modify `app.js` polling frequency)
3. Check Raspberry Pi load: `top` (high CPU usage may delay responses)

## Production Deployment (Continuous Background Service)

### Create systemd Service

Create `/etc/systemd/system/plant-dashboard.service`:

```ini
[Unit]
Description=Plant Monitoring Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/plant-project
Environment="PATH=/home/pi/plant-project/.venv/bin"
ExecStart=/home/pi/plant-project/.venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 src.lib.web_server:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable plant-dashboard

# Start service now
sudo systemctl start plant-dashboard

# Check status
sudo systemctl status plant-dashboard
```

### View Logs

```bash
# View recent logs
journalctl -u plant-dashboard -n 50

# Follow logs in real-time
journalctl -u plant-dashboard -f
```

## Advanced Usage

### Access Dashboard URL by Hostname

If your Pi has hostname `raspberrypi.local`:

```bash
# From any device on local network
http://raspberrypi.local:5000
```

**Setup mDNS** (if not working):
```bash
sudo apt-get install avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

### Set Up Reverse Proxy with Nginx

For cleaner URLs without `:5000` port:

1. Install Nginx: `sudo apt-get install nginx`
2. Configure `/etc/nginx/sites-available/plant-dashboard`:

```nginx
server {
    listen 80;
    server_name raspberrypi.local;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /images/ {
        alias /home/pi/plant-project/data/images/;
    }
}
```

3. Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/plant-dashboard /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

Now access at `http://raspberrypi.local` (no port needed).

## Next Steps

1. **Customize dashboard**: Edit `src/static/style.css` for custom colors/layout
2. **Add more plants**: Use dashboard to configure all your monitored plants
3. **Monitor trends**: Observe environmental patterns over time to optimize watering
4. **Share access**: Give family members the dashboard URL for plant status

## Reference

- **Dashboard API**: [contracts/api.yaml](./contracts/api.yaml)
- **Database Schema**: [contracts/database.sql](./contracts/database.sql)
- **Data Model**: [data-model.md](./data-model.md)
- **Full Specification**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
