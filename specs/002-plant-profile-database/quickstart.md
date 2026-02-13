# Quickstart: Plant Profile Database

**Feature**: 002-plant-profile-database
**Date**: 2026-02-13
**Audience**: Users setting up plant profiles for the first time

## Overview

This guide shows you how to set up plant profiles with custom names and moisture thresholds using the interactive CLI setup script. Once configured, the monitoring system will use each plant's individual threshold instead of a global default.

## Prerequisites

- Raspberry Pi with plant monitoring system installed
- At least one moisture sensor connected to ADS1115 (channels 0, 1, or 2)
- Sensors calibrated using `uv run python3 src/cli/calibrate.py`
- Database directory created (run once):
  ```bash
  mkdir -p data
  chmod 755 data
  ```

## Quick Start

### Step 1: Run the Setup Script

```bash
uv run python3 src/cli/setup_plants.py
```

### Step 2: Follow Interactive Prompts

The script will guide you through creating a plant profile:

```
============================================================
Plant Profile Setup
============================================================

Enter plant name (e.g., Basil, Tomato): Basil

Available sensor channels: 0, 1, 2
Which sensor channel monitors this plant? 0

Enter moisture threshold for Basil (0-100%): 45.0

============================================================
Profile Summary
============================================================
Plant name:       Basil
Sensor channel:   0
Moisture threshold: 45.0%

Save this profile? (y/n): y

✅ Profile saved successfully!

Create another profile? (y/n): y
```

### Step 3: Add More Plants (Optional)

Repeat for each plant you want to monitor:

```
Enter plant name (e.g., Basil, Tomato): Tomato

Available sensor channels: 1, 2
Which sensor channel monitors this plant? 1

Enter moisture threshold for Tomato (0-100%): 35.0

============================================================
Profile Summary
============================================================
Plant name:       Tomato
Sensor channel:   1
Moisture threshold: 35.0%

Save this profile? (y/n): y

✅ Profile saved successfully!

Create another profile? (y/n): n

============================================================
Setup Complete!
============================================================

Created 2 plant profiles:
  - Basil (channel 0, threshold 45.0%)
  - Tomato (channel 1, threshold 35.0%)

Next steps:
1. Start monitoring: uv run python3 src/cli/monitor.py
2. View profiles: sqlite3 data/plants.db "SELECT * FROM plant_profiles;"
```

### Step 4: Start Monitoring

```bash
uv run python3 src/cli/monitor.py
```

You should now see notifications with your custom plant names:

```
2026-02-13 14:30:00 - INFO - Loaded 2 plant profiles from database
2026-02-13 14:30:00 - INFO - Monitoring: Basil (45.0%), Tomato (35.0%)
2026-02-13 14:30:05 - INFO - Basil: 42.0% (OK)
2026-02-13 14:30:05 - INFO - Tomato: 30.0% (DRY - needs water)
2026-02-13 14:30:05 - INFO - Notification sent: Tomato needs watering (30.0%)
```

## Common Tasks

### View All Plant Profiles

```bash
sqlite3 data/plants.db "SELECT plant_name, sensor_channel, acceptable_moisture_level, needs_watering FROM plant_profiles;"
```

Output:
```
Basil|0|45.0|0
Tomato|1|35.0|1
```

### Check Watering History

```bash
sqlite3 data/plants.db "SELECT plant_name, date_last_watered FROM plant_profiles WHERE date_last_watered IS NOT NULL;"
```

Output:
```
Basil|2026-02-13
Tomato|2026-02-12
```

### View Current Moisture Levels

```bash
sqlite3 data/plants.db "SELECT plant_name, current_moisture_level, needs_watering FROM plant_profiles;"
```

Output:
```
Basil|42.5|0
Tomato|30.2|1
Oregano|55.0|0
```

### Update a Plant's Threshold

```bash
sqlite3 data/plants.db "UPDATE plant_profiles SET acceptable_moisture_level = 50.0 WHERE plant_name = 'Basil';"
```

Then restart the monitoring script to pick up the change.

## Validation & Error Handling

### Invalid Plant Name

```
Enter plant name (e.g., Basil, Tomato):

❌ Plant name cannot be empty.

Enter plant name (e.g., Basil, Tomato): This is a very very very long plant name that exceeds the fifty character limit

❌ Plant name too long (max 50 characters).

Enter plant name (e.g., Basil, Tomato): Basil
```

### Duplicate Plant Name

```
Enter plant name (e.g., Basil, Tomato): Basil

❌ Error: Plant name 'Basil' already exists.
   Tip: Choose a different name or modify the existing profile.

Enter plant name (e.g., Basil, Tomato): Sweet Basil
```

### Duplicate Sensor Channel

```
Which sensor channel monitors this plant? 0

❌ Error: Sensor channel 0 is already assigned to 'Basil'.
   Available channels: 1, 2

Which sensor channel monitors this plant? 1
```

### Invalid Moisture Threshold

```
Enter moisture threshold for Basil (0-100%): 150

❌ Moisture threshold must be between 0 and 100%.

Enter moisture threshold for Basil (0-100%): 45.0
```

## Fallback Behavior

If the database is unavailable or corrupted, the monitoring system will automatically fall back to the environment default threshold:

```
2026-02-13 14:30:00 - ERROR - Failed to load database: [Errno 2] No such file or directory: 'data/plants.db'
2026-02-13 14:30:00 - WARN - Using fallback threshold from environment: 40.0%
2026-02-13 14:30:00 - INFO - Monitoring with default threshold for all plants
```

The system will continue monitoring and sending notifications, but all plants will use the same threshold from `config/monitor.env`.

## Database Location

The plant profiles database is stored at:
```
<project-root>/data/plants.db
```

This file is automatically created by the setup script. It's excluded from version control (`.gitignore`) since it contains your specific plant configuration.

## Troubleshooting

### Setup Script Won't Run

**Error**: `ModuleNotFoundError: No module named 'sqlite3'`

**Solution**: SQLite3 is included in Python standard library. If missing, your Python installation may be incomplete. Reinstall Python 3.9+.

### Database File Permissions

**Error**: `PermissionError: [Errno 13] Permission denied: 'data/plants.db'`

**Solution**: Ensure the `data/` directory is writable:
```bash
mkdir -p data
chmod 755 data
```

### Monitoring Script Ignores Database

**Error**: Monitoring script uses default threshold despite database existing

**Solution**: Check the logs for database load errors:
```bash
uv run python3 src/cli/monitor.py 2>&1 | grep -i database
```

If profiles aren't loading, verify the database has profiles:
```bash
sqlite3 data/plants.db "SELECT COUNT(*) FROM plant_profiles;"
```

### Corrupted Database

**Error**: `sqlite3.DatabaseError: database disk image is malformed`

**Solution**: Delete the corrupted database and recreate profiles:
```bash
rm data/plants.db
uv run python3 src/cli/setup_plants.py
```

**Prevention**: Add regular backups to your routine:
```bash
cp data/plants.db data/plants.db.backup-$(date +%Y%m%d)
```

## Next Steps

1. **Customize thresholds**: Each plant type has different water needs. Research optimal moisture levels for your specific plants.
2. **Monitor watering history**: Check `date_last_watered` to track your watering patterns and identify neglected plants.
3. **Adjust notifications**: Modify `config/monitor.env` to change notification throttle duration or sampling interval.

## Advanced Usage

### Bulk Import Profiles

Create a SQL file with multiple INSERT statements:

```sql
-- bulk_import.sql
INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
VALUES
  ('Basil', 0, 45.0, 0),
  ('Tomato', 1, 35.0, 0),
  ('Oregano', 2, 40.0, 0);
```

Import:
```bash
sqlite3 data/plants.db < bulk_import.sql
```

### Export Profiles

```bash
sqlite3 data/plants.db ".dump plant_profiles" > profiles_backup.sql
```

### Reset All Watering Status

Useful after watering all plants:
```bash
sqlite3 data/plants.db "UPDATE plant_profiles SET needs_watering = 0, date_last_watered = DATE('now');"
```

## Reference

- **Setup CLI**: `src/cli/setup_plants.py`
- **Database library**: `src/lib/database.py`
- **Data model**: `src/models/plant_profile.py`
- **Database schema**: [contracts/database.yaml](./contracts/database.yaml)
- **Full specification**: [spec.md](./spec.md)
